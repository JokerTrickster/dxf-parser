#!/usr/bin/env python3
"""
DXF 주차면 + 건물 외곽선 추출기
주차면 블록과 PLAN 레이어의 LINE/LWPOLYLINE/ARC를 추출
"""

import ezdxf
from ezdxf.math import Matrix44, Vec3
import math
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
import argparse
import os


# 주차면 레이어 매핑
PARKING_LAYER_MAPPING = {
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

LAYER_COLORS = {
    'p-parking-basic': 7,
    'p-parking-large': 3,
    'p-parking-small': 4,
    'p-parking-disable': 1,
    'p-parking-large-electric': 5,
    'p-parking-large-women': 6,
    'building-outline': 8,  # 회색
}


# 제외할 블록 키워드 (계단, 비상구 등)
EXCLUDED_BLOCK_KEYWORDS = [
    '계단', 'STAIR', 'FSD', '비상구'
]


class ParkingWithBuildingExtractor:
    """주차면 + 건물 외곽선 추출기"""

    def __init__(self, input_file: str):
        self.input_file = input_file
        self.doc = ezdxf.readfile(input_file)
        self.parking_data = []
        self.building_entities = []
        self.block_geometries = {}
        self.excluded_blocks_count = 0

    def get_layer_for_block(self, block_name: str) -> Optional[str]:
        """블록명에 해당하는 레이어명 반환"""
        for keyword, layer in PARKING_LAYER_MAPPING.items():
            if keyword in block_name:
                return layer
        return None

    def get_parking_type(self, block_name: str) -> Optional[str]:
        """블록명에서 타입 추출"""
        for keyword in sorted(PARKING_LAYER_MAPPING.keys(), key=len, reverse=True):
            if keyword.upper() in block_name.upper():
                return keyword
        return None

    def extract_block_geometry(self, block_name: str) -> Optional[List[Tuple[float, float]]]:
        """블록에서 가장 큰 LWPOLYLINE 추출"""
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
                    # 면적 계산
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
            self.block_geometries[block_name] = largest_polyline
            return largest_polyline

        return None

    def transform_point(self, point, insert_point, rotation, scale_x=1.0, scale_y=1.0):
        """점에 INSERT 변환 적용"""
        x, y = point[0], point[1]
        x *= scale_x
        y *= scale_y

        rad = math.radians(rotation)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)

        new_x = x * cos_r - y * sin_r
        new_y = x * sin_r + y * cos_r

        new_x += insert_point.x
        new_y += insert_point.y

        return (new_x, new_y)

    def transform_vertices(self, vertices, insert_point, rotation, scale_x=1.0, scale_y=1.0):
        """여러 점에 변환 적용"""
        return [self.transform_point(v, insert_point, rotation, scale_x, scale_y) for v in vertices]

    def extract_parking_from_block(self, block, parent_transform: Matrix44 = None, depth: int = 0):
        """블록에서 주차면 추출 (재귀)"""
        if depth > 10:
            return

        for entity in block:
            if entity.dxftype() == "INSERT":
                block_name = entity.dxf.name
                layer = self.get_layer_for_block(block_name)

                if layer:
                    insert_point = entity.dxf.insert
                    rotation = getattr(entity.dxf, 'rotation', 0)
                    scale_x = getattr(entity.dxf, 'xscale', 1.0)
                    scale_y = getattr(entity.dxf, 'yscale', 1.0)

                    geometry = self.extract_block_geometry(block_name)

                    if geometry:
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

    def extract_building_lines_from_block(self, block, depth: int = 0):
        """PLAN 레이어의 LINE/LWPOLYLINE/ARC 추출"""
        if depth > 10:
            return

        for entity in block:
            # 블록 이름 필터링 (계단 등 제외)
            if entity.dxftype() == 'INSERT':
                block_name = entity.dxf.name
                is_excluded = False
                for keyword in EXCLUDED_BLOCK_KEYWORDS:
                    if keyword in block_name:
                        is_excluded = True
                        self.excluded_blocks_count += 1
                        # print(f"  [제외] {block_name} ({keyword})")
                        break
                
                if is_excluded:
                    continue

                if block_name in self.doc.blocks:
                    nested_block = self.doc.blocks[block_name]
                    self.extract_building_lines_from_block(nested_block, depth + 1)
                continue

            layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else None

            # PLAN 레이어의 도형 요소만 추출
            if layer == 'PLAN':
                etype = entity.dxftype()

                if etype == 'LINE':
                    start = entity.dxf.start
                    end = entity.dxf.end
                    self.building_entities.append({
                        'type': 'LINE',
                        'start': (start.x, start.y),
                        'end': (end.x, end.y)
                    })

                elif etype == 'LWPOLYLINE':
                    vertices = list(entity.get_points())
                    closed = entity.closed
                    self.building_entities.append({
                        'type': 'LWPOLYLINE',
                        'vertices': vertices,
                        'closed': closed
                    })

                elif etype == 'ARC':
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    start_angle = entity.dxf.start_angle
                    end_angle = entity.dxf.end_angle
                    self.building_entities.append({
                        'type': 'ARC',
                        'center': (center.x, center.y),
                        'radius': radius,
                        'start_angle': start_angle,
                        'end_angle': end_angle
                    })

            # INSERT는 위에서 처리했으므로 제거
            # if entity.dxftype() == 'INSERT':
            #     block_name = entity.dxf.name
            #     if block_name in self.doc.blocks:
            #         nested_block = self.doc.blocks[block_name]
            #         self.extract_building_lines_from_block(nested_block, depth + 1)

    def extract_all(self, floor: str = 'B1'):
        """주차면 + 건물 외곽선 추출"""
        print(f"추출 시작: {floor}층...")

        # 주요 평면도 블록
        floor_blocks = {
            'B1': ['지하1층평면도'],
            'B2': ['지하2층평면도']
        }

        blocks_to_process = floor_blocks.get(floor.upper(), ['지하1층평면도'])

        for block_name in blocks_to_process:
            if block_name in self.doc.blocks:
                print(f"  [{block_name}] 분석 중...")
                block = self.doc.blocks[block_name]

                # 주차면 추출
                self.extract_parking_from_block(block)

                # 건물 외곽선 추출
                self.extract_building_lines_from_block(block)

        print(f"주차면: {len(self.parking_data)}개")
        print(f"건물 외곽선: {len(self.building_entities)}개 (LINE/LWPOLYLINE/ARC)")
        print(f"제외된 블록 (계단 등): {self.excluded_blocks_count}개")

        # 통계
        stats = defaultdict(int)
        for p in self.parking_data:
            stats[p['layer']] += 1

        print("\n주차면 레이어별:")
        for layer, count in sorted(stats.items()):
            print(f"  {layer}: {count}개")

    def filter_building_by_parking_area(self):
        """주차면 영역 내의 건물 외곽선만 필터링"""
        if not self.parking_data:
            return

        # 주차면 바운딩 박스 계산 (여유 추가)
        all_x = []
        all_y = []
        for parking in self.parking_data:
            for v in parking['vertices']:
                all_x.append(v[0])
                all_y.append(v[1])

        margin = 10000  # 1만mm (10m) 여유
        bbox_min_x = min(all_x) - margin
        bbox_max_x = max(all_x) + margin
        bbox_min_y = min(all_y) - margin
        bbox_max_y = max(all_y) + margin

        print(f"\n주차면 영역: X({bbox_min_x:.0f} ~ {bbox_max_x:.0f}), Y({bbox_min_y:.0f} ~ {bbox_max_y:.0f})")

        # 건물 외곽선 필터링
        filtered = []
        for entity in self.building_entities:
            in_range = False

            if entity['type'] == 'LINE':
                x1, y1 = entity['start']
                x2, y2 = entity['end']
                # 선의 양 끝점 중 하나라도 범위 내에 있으면 포함
                if (bbox_min_x <= x1 <= bbox_max_x and bbox_min_y <= y1 <= bbox_max_y) or \
                   (bbox_min_x <= x2 <= bbox_max_x and bbox_min_y <= y2 <= bbox_max_y):
                    in_range = True

            elif entity['type'] == 'LWPOLYLINE':
                # 점 중 하나라도 범위 내에 있으면 포함
                for v in entity['vertices']:
                    if bbox_min_x <= v[0] <= bbox_max_x and bbox_min_y <= v[1] <= bbox_max_y:
                        in_range = True
                        break

            elif entity['type'] == 'ARC':
                x, y = entity['center']
                # 중심점이 범위 내에 있으면 포함
                if bbox_min_x <= x <= bbox_max_x and bbox_min_y <= y <= bbox_max_y:
                    in_range = True

            if in_range:
                filtered.append(entity)

        original_count = len(self.building_entities)
        self.building_entities = filtered
        print(f"건물 외곽선 필터링: {original_count}개 → {len(filtered)}개")

    def normalize_coordinates(self):
        """좌표 정규화 (주차면 기준)"""
        if not self.parking_data:
            return (0, 0)

        # 주차면 좌표에서 최소값 찾기
        all_x = []
        all_y = []
        for parking in self.parking_data:
            for v in parking['vertices']:
                all_x.append(v[0])
                all_y.append(v[1])

        min_x = min(all_x)
        min_y = min(all_y)

        print(f"\n좌표 정규화: 오프셋 ({min_x:.2f}, {min_y:.2f})")

        # 주차면 정규화
        for parking in self.parking_data:
            parking['vertices'] = [(v[0] - min_x, v[1] - min_y) for v in parking['vertices']]
            parking['insert_point'] = (
                parking['insert_point'][0] - min_x,
                parking['insert_point'][1] - min_y
            )

        # 건물 외곽선 정규화
        for entity in self.building_entities:
            if entity['type'] == 'LINE':
                entity['start'] = (entity['start'][0] - min_x, entity['start'][1] - min_y)
                entity['end'] = (entity['end'][0] - min_x, entity['end'][1] - min_y)
            elif entity['type'] == 'LWPOLYLINE':
                entity['vertices'] = [(v[0] - min_x, v[1] - min_y) for v in entity['vertices']]
            elif entity['type'] == 'ARC':
                entity['center'] = (entity['center'][0] - min_x, entity['center'][1] - min_y)

        return (min_x, min_y)

    def create_output_dxf(self, output_file: str):
        """새 DXF 파일 생성"""
        print(f"\n새 DXF 파일 생성: {output_file}")

        # 주차면 영역 기준 건물 외곽선 필터링
        self.filter_building_by_parking_area()

        # 좌표 정규화
        self.normalize_coordinates()

        # 새 DXF 문서
        new_doc = ezdxf.new('R2010')
        msp = new_doc.modelspace()

        # 레이어 생성
        for layer_name, color in LAYER_COLORS.items():
            new_doc.layers.add(layer_name, color=color)

        # 주차면 그리기
        for parking in self.parking_data:
            layer = parking['layer']
            vertices = parking['vertices']

            if vertices and len(vertices) >= 3:
                points = [(v[0], v[1]) for v in vertices]
                msp.add_lwpolyline(points, close=True, dxfattribs={'layer': layer})

        # 건물 외곽선 그리기
        for entity in self.building_entities:
            if entity['type'] == 'LINE':
                msp.add_line(
                    entity['start'],
                    entity['end'],
                    dxfattribs={'layer': 'building-outline'}
                )
            elif entity['type'] == 'LWPOLYLINE':
                msp.add_lwpolyline(
                    entity['vertices'],
                    close=entity['closed'],
                    dxfattribs={'layer': 'building-outline'}
                )
            elif entity['type'] == 'ARC':
                msp.add_arc(
                    entity['center'],
                    entity['radius'],
                    entity['start_angle'],
                    entity['end_angle'],
                    dxfattribs={'layer': 'building-outline'}
                )

        # 저장
        new_doc.saveas(output_file)
        print(f"저장 완료: {output_file}")
        print(f"  주차면: {len(self.parking_data)}개")
        print(f"  건물 외곽선: {len(self.building_entities)}개")


def main():
    parser = argparse.ArgumentParser(description='DXF 주차면 + 건물 외곽선 추출기')
    parser.add_argument('input', help='입력 DXF 파일')
    parser.add_argument('-o', '--output', help='출력 DXF 파일', default=None)
    parser.add_argument('--floor', default='B1', help='층 선택 (B1 또는 B2)')

    args = parser.parse_args()

    # 출력 파일명
    if not args.output:
        base_name = os.path.splitext(args.input)[0]
        args.output = f"{base_name}_{args.floor}_converted.dxf"

    # 추출 및 변환
    extractor = ParkingWithBuildingExtractor(args.input)
    extractor.extract_all(floor=args.floor)
    extractor.create_output_dxf(args.output)

    print("\n작업 완료!")


if __name__ == '__main__':
    main()
