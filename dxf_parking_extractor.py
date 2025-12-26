#!/usr/bin/env python3
"""
DXF 주차장 도면 레이어 자동 생성 도구

원본 DXF 파일에서 주차면을 추출하고,
참고용 파일(banpo) 형식의 레이어 구조로 변환하여 새 DXF 생성
"""

import ezdxf
from ezdxf.math import Matrix44, Vec3
import math
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
import os


# 레이어 매핑 설정
LAYER_MAPPING = {
    # 원본 블록명 키워드 -> 새 레이어명
    'PARK_일반': 'p-parking-basic',
    'PARK_확장': 'p-parking-large',
    'PARK_경차': 'p-parking-small',
    'PARK_장애인': 'p-parking-disable',
    'Park-환경친화': 'p-parking-large-electric',
    'PARK-EC': 'p-parking-large-electric',
    '가족배려주차(확장형)': 'p-parking-large-women',
    '가족배려주차(일반형)': 'p-parking-large-women',
    '교통약자우선': 'p-parking-large-women',
}

# 레이어 색상 설정 (AutoCAD 색상 인덱스)
LAYER_COLORS = {
    'p-parking-basic': 7,       # 흰색
    'p-parking-large': 3,       # 초록
    'p-parking-small': 4,       # 시안
    'p-parking-disable': 1,     # 빨강
    'p-parking-large-electric': 5,  # 파랑
    'p-parking-large-women': 6,     # 마젠타
}

# 주차면 타입별 기본 크기 (mm)
PARKING_SIZES = {
    'PARK_일반': (2500, 5000),
    'PARK_확장': (2600, 5200),
    'PARK_경차': (2000, 3600),
    'PARK_장애인': (5000, 3300),
    'Park-환경친화': (2500, 5000),
    'PARK-EC': (5000, 2500),
    '가족배려주차(확장형)': (5200, 2600),
    '가족배려주차(일반형)': (5000, 2500),
    '교통약자우선': (5000, 3300),
}


class DXFParkingExtractor:
    """DXF 주차면 추출 및 레이어 변환 클래스"""

    def __init__(self, input_file: str, reference_file: str = None):
        self.input_file = input_file
        self.reference_file = reference_file
        self.doc = ezdxf.readfile(input_file)
        self.parking_data = []
        self.block_geometries = {}

    def get_layer_for_block(self, block_name: str) -> Optional[str]:
        """블록명에 해당하는 레이어명 반환"""
        for keyword, layer in LAYER_MAPPING.items():
            if keyword in block_name:
                return layer
        return None

    def get_parking_type(self, block_name: str) -> Optional[str]:
        """블록명에서 주차면 타입 추출"""
        for keyword in LAYER_MAPPING.keys():
            if keyword in block_name:
                return keyword
        return None

    def extract_block_geometry(self, block_name: str) -> Optional[List[Tuple[float, float]]]:
        """블록에서 메인 외곽선(가장 큰 LWPOLYLINE) 추출"""
        if block_name in self.block_geometries:
            return self.block_geometries[block_name]

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
                        largest_polyline = [(v[0], v[1]) for v in vertices]

        self.block_geometries[block_name] = largest_polyline
        return largest_polyline

    def transform_vertices(self, vertices: List[Tuple[float, float]],
                          insert_point: Vec3, rotation: float,
                          scale_x: float = 1.0, scale_y: float = 1.0) -> List[Tuple[float, float]]:
        """좌표 변환 (이동, 회전, 스케일)"""
        transformed = []
        rad = math.radians(rotation)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)

        for x, y in vertices:
            # 스케일 적용
            x *= scale_x
            y *= scale_y
            # 회전 적용
            new_x = x * cos_r - y * sin_r
            new_y = x * sin_r + y * cos_r
            # 이동 적용
            new_x += insert_point.x
            new_y += insert_point.y
            transformed.append((new_x, new_y))

        return transformed

    def extract_parking_from_block(self, block, parent_transform: Matrix44 = None, depth: int = 0):
        """블록에서 주차면 INSERT 재귀적 추출"""
        if depth > 10:  # 무한 재귀 방지
            return

        for entity in block:
            if entity.dxftype() == "INSERT":
                block_name = entity.dxf.name
                layer = self.get_layer_for_block(block_name)

                if layer:
                    # 주차면 블록 발견
                    insert_point = entity.dxf.insert
                    rotation = getattr(entity.dxf, 'rotation', 0)
                    scale_x = getattr(entity.dxf, 'xscale', 1.0)
                    scale_y = getattr(entity.dxf, 'yscale', 1.0)

                    # 블록 외곽선 추출
                    geometry = self.extract_block_geometry(block_name)

                    if geometry:
                        # 좌표 변환
                        transformed = self.transform_vertices(
                            geometry, insert_point, rotation, scale_x, scale_y
                        )

                        parking_type = self.get_parking_type(block_name)

                        self.parking_data.append({
                            'layer': layer,
                            'type': parking_type,
                            'block_name': block_name,
                            'vertices': transformed,
                            'insert_point': (insert_point.x, insert_point.y),
                            'rotation': rotation,
                        })

                # 중첩 블록 탐색
                if block_name in self.doc.blocks:
                    nested_block = self.doc.blocks[block_name]
                    self.extract_parking_from_block(nested_block, depth=depth + 1)

    def extract_all_parking(self):
        """모든 주차면 추출"""
        print("주차면 추출 시작...")

        # 주요 평면도 블록 탐색
        main_blocks = ['지하1층평면도', '지하2층평면도']

        for block_name in main_blocks:
            if block_name in self.doc.blocks:
                print(f"  [{block_name}] 분석 중...")
                block = self.doc.blocks[block_name]
                self.extract_parking_from_block(block)

        # 모델스페이스도 확인
        msp = self.doc.modelspace()
        for entity in msp:
            if entity.dxftype() == "INSERT":
                block_name = entity.dxf.name
                if block_name in self.doc.blocks:
                    self.extract_parking_from_block(self.doc.blocks[block_name])

        print(f"총 {len(self.parking_data)}개 주차면 추출 완료")

        # 통계 출력
        stats = defaultdict(int)
        for p in self.parking_data:
            stats[p['layer']] += 1

        print("\n레이어별 주차면 수:")
        for layer, count in sorted(stats.items()):
            print(f"  {layer}: {count}개")

    def calculate_center(self, vertices: List[Tuple[float, float]]) -> Tuple[float, float]:
        """다각형 중심점 계산"""
        x_sum = sum(v[0] for v in vertices)
        y_sum = sum(v[1] for v in vertices)
        n = len(vertices)
        return (x_sum / n, y_sum / n)

    def normalize_coordinates(self):
        """좌표를 원점 기준으로 정규화"""
        if not self.parking_data:
            return

        # 모든 좌표에서 최소값 찾기
        all_x = []
        all_y = []
        for parking in self.parking_data:
            for v in parking['vertices']:
                all_x.append(v[0])
                all_y.append(v[1])

        min_x = min(all_x)
        min_y = min(all_y)

        print(f"\n좌표 정규화: 오프셋 ({min_x:.2f}, {min_y:.2f})")

        # 모든 좌표에서 최소값 빼기
        for parking in self.parking_data:
            parking['vertices'] = [(v[0] - min_x, v[1] - min_y) for v in parking['vertices']]
            parking['insert_point'] = (
                parking['insert_point'][0] - min_x,
                parking['insert_point'][1] - min_y
            )

    def separate_floors(self) -> Dict[str, List]:
        """층별로 주차면 분리 (X 좌표 기준)"""
        if not self.parking_data:
            return {}

        # X 좌표 기준으로 클러스터링
        x_values = [self.calculate_center(p['vertices'])[0] for p in self.parking_data]
        x_min, x_max = min(x_values), max(x_values)
        x_mid = (x_min + x_max) / 2

        floors = {'B1': [], 'B2': []}

        for parking in self.parking_data:
            center_x = self.calculate_center(parking['vertices'])[0]
            if center_x > x_mid:
                floors['B1'].append(parking)
            else:
                floors['B2'].append(parking)

        print(f"\n층별 분리: B1={len(floors['B1'])}개, B2={len(floors['B2'])}개")
        return floors

    def create_output_dxf(self, output_file: str, include_ids: bool = True,
                         normalize: bool = False, floor_filter: str = None):
        """새 DXF 파일 생성"""
        print(f"\n새 DXF 파일 생성: {output_file}")

        # 좌표 정규화
        if normalize:
            self.normalize_coordinates()

        # 층별 필터링
        data_to_export = self.parking_data
        if floor_filter:
            floors = self.separate_floors()
            if floor_filter.upper() in floors:
                data_to_export = floors[floor_filter.upper()]
                print(f"층 필터 적용: {floor_filter.upper()} ({len(data_to_export)}개)")

        # 새 DXF 문서 생성
        new_doc = ezdxf.new('R2010')
        msp = new_doc.modelspace()

        # 레이어 생성
        for layer_name, color in LAYER_COLORS.items():
            new_doc.layers.add(layer_name, color=color)

        # 주차면 ID용 레이어
        if include_ids:
            new_doc.layers.add('p-parking-id', color=7)

        # 주차면 그리기
        parking_id = 1
        for parking in data_to_export:
            layer = parking['layer']
            vertices = parking['vertices']

            if vertices and len(vertices) >= 3:
                # 닫힌 폴리라인으로 주차면 그리기
                points = [(v[0], v[1]) for v in vertices]
                msp.add_lwpolyline(points, close=True, dxfattribs={'layer': layer})

                # 주차면 ID 텍스트 추가
                if include_ids:
                    center = self.calculate_center(vertices)
                    msp.add_mtext(
                        str(parking_id),
                        dxfattribs={
                            'layer': 'p-parking-id',
                            'insert': center,
                            'char_height': 300,  # 텍스트 크기
                            'attachment_point': 5,  # 중앙 정렬
                        }
                    )
                parking_id += 1

        # 저장
        new_doc.saveas(output_file)
        print(f"저장 완료: {output_file}")
        print(f"총 {parking_id - 1}개 주차면 생성됨")

    def export_to_csv(self, csv_file: str):
        """주차면 정보 CSV 내보내기"""
        import csv

        print(f"\nCSV 내보내기: {csv_file}")

        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'id', 'layer', 'type', 'center_x', 'center_y',
                'rotation', 'vertex_count', 'vertices'
            ])

            for idx, parking in enumerate(self.parking_data, 1):
                vertices = parking['vertices']
                center = self.calculate_center(vertices) if vertices else (0, 0)
                vertices_str = ';'.join([f"{v[0]:.2f},{v[1]:.2f}" for v in vertices])

                writer.writerow([
                    idx,
                    parking['layer'],
                    parking['type'],
                    f"{center[0]:.2f}",
                    f"{center[1]:.2f}",
                    parking['rotation'],
                    len(vertices),
                    vertices_str
                ])

        print(f"CSV 저장 완료: {len(self.parking_data)}개 항목")


def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='DXF 주차장 도면 레이어 자동 생성')
    parser.add_argument('input', help='입력 DXF 파일')
    parser.add_argument('-o', '--output', help='출력 DXF 파일', default=None)
    parser.add_argument('-c', '--csv', help='CSV 내보내기 파일', default=None)
    parser.add_argument('--no-ids', action='store_true', help='주차면 ID 텍스트 제외')
    parser.add_argument('--normalize', action='store_true', help='좌표를 원점 기준으로 정규화')
    parser.add_argument('--floor', choices=['B1', 'B2', 'b1', 'b2'], help='특정 층만 추출')
    parser.add_argument('--split-floors', action='store_true', help='층별로 파일 분리 저장')

    args = parser.parse_args()

    # 기본 출력 파일명 생성
    base = os.path.splitext(args.input)[0]
    if args.output is None:
        args.output = f"{base}_converted.dxf"

    if args.csv is None:
        args.csv = f"{base}_parking.csv"

    # 추출 및 변환 실행
    extractor = DXFParkingExtractor(args.input)
    extractor.extract_all_parking()

    if args.split_floors:
        # 층별로 분리 저장
        floors = extractor.separate_floors()
        for floor_name, floor_data in floors.items():
            if floor_data:
                floor_output = f"{base}_{floor_name}_converted.dxf"
                floor_csv = f"{base}_{floor_name}_parking.csv"

                # 임시로 데이터 교체
                original_data = extractor.parking_data
                extractor.parking_data = floor_data

                extractor.create_output_dxf(
                    floor_output,
                    include_ids=not args.no_ids,
                    normalize=args.normalize
                )

                extractor.parking_data = original_data
    else:
        extractor.create_output_dxf(
            args.output,
            include_ids=not args.no_ids,
            normalize=args.normalize,
            floor_filter=args.floor
        )

    print("\n작업 완료!")


if __name__ == '__main__':
    main()
