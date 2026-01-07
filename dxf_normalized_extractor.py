#!/usr/bin/env python3
"""
DXF 정규화 추출기 - 블록 내부 좌표까지 정규화
모든 엔티티의 실제 월드 좌표를 계산하여 정규화
"""

import ezdxf
from ezdxf.math import Vec3
import math
from collections import defaultdict
import argparse
import os


# 추출할 블록 키워드
EXTRACT_KEYWORDS = [
    'PARK_일반', 'PARK_확장', 'PARK_경차', 'PARK_장애인',
    'Park-환경친화', 'PARK-EC',
    '가족배려주차', '교통약자우선',
    '계단', 'STAIR', 'STA', 'core',
    'FSD', '출입구', '비상구',
]

LAYER_MAPPING = {
    'PARK_일반': 'p-parking-basic',
    'PARK_확장': 'p-parking-large',
    'PARK_경차': 'p-parking-small',
    'PARK_장애인': 'p-parking-disable',
    'Park-환경친화': 'p-parking-large-electric',
    'PARK-EC': 'p-parking-large-electric',
    '가족배려주차(확장형)': 'p-parking-large-women',
    '가족배려주차(일반형)': 'p-parking-large-women',
    '교통약자우선': 'p-parking-large-women',
    '계단': 's-circulation-stairs',
    'STAIR': 's-circulation-stairs',
    'STA': 's-circulation-stairs',
    'core': 's-circulation-stairs',
    'FSD': 's-circulation-exit',
    '출입구': 's-circulation-entrance',
    '비상구': 's-circulation-exit',
}

LAYER_COLORS = {
    'p-parking-basic': 7,
    'p-parking-large': 3,
    'p-parking-small': 4,
    'p-parking-disable': 1,
    'p-parking-large-electric': 5,
    'p-parking-large-women': 6,
    's-circulation-stairs': 2,
    's-circulation-exit': 1,
    's-circulation-entrance': 3,
}


class NormalizedDXFExtractor:
    """블록 내부 좌표까지 정규화하는 추출기"""

    def __init__(self, input_file):
        self.input_file = input_file
        self.doc = ezdxf.readfile(input_file)
        self.extracted_geometries = []
        self.stats = defaultdict(int)

    def should_extract(self, block_name):
        """블록명에 추출 키워드가 포함되어 있는지 확인"""
        block_upper = block_name.upper()
        for keyword in EXTRACT_KEYWORDS:
            if keyword.upper() in block_upper:
                return True
        return False

    def get_output_layer(self, block_name):
        """블록명으로 출력 레이어 결정"""
        for keyword in sorted(LAYER_MAPPING.keys(), key=len, reverse=True):
            if keyword.upper() in block_name.upper():
                return LAYER_MAPPING[keyword]
        return 'other'

    def transform_point(self, point, insert_point, rotation, scale_x=1.0, scale_y=1.0):
        """점을 INSERT 변환 적용"""
        x, y = point[0], point[1]

        # 스케일 적용
        x *= scale_x
        y *= scale_y

        # 회전 적용
        rad = math.radians(rotation)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)

        new_x = x * cos_r - y * sin_r
        new_y = x * sin_r + y * cos_r

        # 이동 적용
        new_x += insert_point.x
        new_y += insert_point.y

        return (new_x, new_y)

    def extract_lwpolyline_from_block(self, block_name, insert_point, rotation, scale_x, scale_y):
        """블록에서 가장 큰 LWPOLYLINE 추출 및 변환"""
        if block_name not in self.doc.blocks:
            return None

        block = self.doc.blocks[block_name]
        largest_polyline = None
        largest_area = 0

        for entity in block:
            if entity.dxftype() == "LWPOLYLINE" and entity.closed:
                vertices = list(entity.get_points())
                if len(vertices) >= 3:
                    # 면적 계산 (신발끈 공식)
                    area = 0
                    n = len(vertices)
                    for i in range(n):
                        j = (i + 1) % n
                        area += vertices[i][0] * vertices[j][1]
                        area -= vertices[j][0] * vertices[i][1]
                    area = abs(area) / 2

                    if area > largest_area:
                        largest_area = area
                        largest_polyline = vertices

        if largest_polyline:
            # 좌표 변환 적용
            transformed = [
                self.transform_point(v, insert_point, rotation, scale_x, scale_y)
                for v in largest_polyline
            ]
            return transformed

        return None

    def extract_blocks_recursive(self, block, depth=0, max_depth=10):
        """재귀적으로 블록 탐색 및 geometry 추출"""
        if depth > max_depth:
            return

        for entity in block:
            if entity.dxftype() == 'INSERT':
                block_name = entity.dxf.name

                # 추출 대상인지 확인
                if self.should_extract(block_name):
                    output_layer = self.get_output_layer(block_name)

                    insert_point = entity.dxf.insert
                    rotation = getattr(entity.dxf, 'rotation', 0)
                    scale_x = getattr(entity.dxf, 'xscale', 1.0)
                    scale_y = getattr(entity.dxf, 'yscale', 1.0)

                    # 블록에서 geometry 추출 및 변환
                    vertices = self.extract_lwpolyline_from_block(
                        block_name, insert_point, rotation, scale_x, scale_y
                    )

                    if vertices:
                        self.extracted_geometries.append({
                            'vertices': vertices,
                            'layer': output_layer,
                            'block_name': block_name
                        })

                        self.stats[output_layer] += 1

                # 중첩 블록 탐색
                if block_name in self.doc.blocks:
                    nested_block = self.doc.blocks[block_name]
                    self.extract_blocks_recursive(nested_block, depth + 1, max_depth)

    def extract_all(self):
        """모델스페이스에서 INSERT된 블록만 추출"""
        print("블록 추출 시작 (모델스페이스에 INSERT된 블록만)...")

        # 모델스페이스에서 시작
        msp = self.doc.modelspace()
        for entity in msp:
            if entity.dxftype() == 'INSERT':
                block_name = entity.dxf.name
                if block_name in self.doc.blocks:
                    print(f"  [{block_name}] 분석 중...")
                    self.extract_blocks_recursive(self.doc.blocks[block_name])

        print(f"\n총 {len(self.extracted_geometries)}개 geometry 추출 완료")

        # 통계 출력
        print("\n레이어별 geometry 수:")
        for layer, count in sorted(self.stats.items()):
            print(f"  {layer}: {count}개")

    def calculate_normalization_offset(self):
        """모든 실제 좌표에서 최소값 계산"""
        if not self.extracted_geometries:
            return (0, 0)

        min_x = float('inf')
        min_y = float('inf')

        for geom in self.extracted_geometries:
            for v in geom['vertices']:
                min_x = min(min_x, v[0])
                min_y = min(min_y, v[1])

        return (min_x, min_y)

    def create_output_dxf(self, output_file, normalize=True):
        """새 DXF 파일 생성"""
        print(f"\n새 DXF 파일 생성: {output_file}")

        # 좌표 정규화 오프셋 계산
        offset_x, offset_y = (0, 0)
        if normalize:
            offset_x, offset_y = self.calculate_normalization_offset()
            print(f"좌표 정규화: 오프셋 ({offset_x:.2f}, {offset_y:.2f})")

        # 새 DXF 문서
        new_doc = ezdxf.new('R2010')
        new_msp = new_doc.modelspace()

        # 레이어 생성
        for layer_name, color in LAYER_COLORS.items():
            new_doc.layers.add(layer_name, color=color)

        # Geometry를 LWPOLYLINE으로 추가
        for geom in self.extracted_geometries:
            layer = geom['layer']
            vertices = geom['vertices']

            # 정규화된 좌표
            normalized_vertices = [
                (v[0] - offset_x, v[1] - offset_y)
                for v in vertices
            ]

            # LWPOLYLINE 추가
            new_msp.add_lwpolyline(
                normalized_vertices,
                close=True,
                dxfattribs={'layer': layer}
            )

        # 저장
        new_doc.saveas(output_file)
        print(f"저장 완료: {output_file}")
        print(f"총 {len(self.extracted_geometries)}개 geometry 생성됨")


def main():
    parser = argparse.ArgumentParser(description='DXF 정규화 추출기 (블록 내부 좌표까지 정규화)')
    parser.add_argument('input', help='입력 DXF 파일')
    parser.add_argument('-o', '--output', help='출력 DXF 파일', default=None)
    parser.add_argument('--max-depth', type=int, default=10, help='최대 블록 탐색 깊이')
    parser.add_argument('--normalize', action='store_true', help='좌표를 원점 기준으로 정규화')

    args = parser.parse_args()

    # 출력 파일명
    if not args.output:
        base_name = os.path.splitext(args.input)[0]
        args.output = f"{base_name}_normalized.dxf"

    # 추출 및 변환
    extractor = NormalizedDXFExtractor(args.input)
    extractor.extract_all()
    extractor.create_output_dxf(args.output, normalize=args.normalize)

    print("\n작업 완료!")


if __name__ == '__main__':
    main()
