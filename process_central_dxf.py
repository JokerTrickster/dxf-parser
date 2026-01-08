#!/usr/bin/env python3
"""
Central.dxf 재가공 스크립트
1단계: 주차면만 추출하여 깨끗한 레이어 구조의 DXF 파일 생성
2단계: 가공된 DXF를 CSV로 변환
"""

import ezdxf
from ezdxf.math import Matrix44, Vec3
from collections import defaultdict
import argparse
import os
import csv
import json


# 주차면 레이어 정의 (표준화)
PARKING_LAYERS = {
    'p-parking-basic': {'color': 7, 'name': '일반주차'},
    'p-parking-large': {'color': 3, 'name': '확장주차'},
    'p-parking-small': {'color': 4, 'name': '경차주차'},
    'p-parking-disable': {'color': 1, 'name': '장애인주차'},
    'p-parking-electric': {'color': 5, 'name': '전기차주차'},
    'p-parking-women': {'color': 6, 'name': '여성주차'},
    'p-parking-delivery': {'color': 2, 'name': '택배주차'},
}

# 동선 레이어 정의
CIRCULATION_LAYERS = {
    's-circulation-stairs': {'color': 2, 'name': '계단'},
    's-circulation-exit': {'color': 1, 'name': '비상구'},
    's-circulation-entrance': {'color': 3, 'name': '출입구'},
    's-circulation-ramp': {'color': 4, 'name': '램프'},
}

# 블록명 → 레이어 매핑
BLOCK_TO_LAYER = {
    'p-일반': 'p-parking-basic',
    'p-경차': 'p-parking-small',
    '경형': 'p-parking-small',
    '확장형주차': 'p-parking-large',
    '확장': 'p-parking-large',
    '장애인전용주차': 'p-parking-disable',
    '장애인': 'p-parking-disable',
    '전기차 완속': 'p-parking-electric',
    '전기차 급속': 'p-parking-electric',
    '전기차': 'p-parking-electric',
    '택배주차': 'p-parking-delivery',
    '여성': 'p-parking-women',
    '계단': 's-circulation-stairs',
    'STAIR': 's-circulation-stairs',
    'STA': 's-circulation-stairs',
    'core': 's-circulation-stairs',
    '램프': 's-circulation-ramp',
    '출입': 's-circulation-entrance',
    'FSD': 's-circulation-exit',
    '비상구': 's-circulation-exit',
}


class CentralDXFProcessor:
    """Central.dxf 재가공 처리기"""

    def __init__(self, input_file, layer_mapping=None):
        self.input_file = input_file
        self.doc = ezdxf.readfile(input_file)
        self.parking_geometries = []
        self.stats = defaultdict(int)
        # 사용자 정의 layer_mapping이 있으면 사용, 없으면 기본값 사용
        self.block_to_layer = layer_mapping if layer_mapping else BLOCK_TO_LAYER

    def get_layer_from_block(self, block_name):
        """블록명으로 레이어 결정"""
        # 정확한 블록명 매칭 우선 (사용자 정의 매핑)
        if block_name in self.block_to_layer:
            return self.block_to_layer[block_name]

        # 부분 문자열 매칭 (기본 매핑)
        for keyword in sorted(self.block_to_layer.keys(), key=len, reverse=True):
            if keyword in block_name:
                return self.block_to_layer[keyword]
        return None

    def should_extract(self, block_name):
        """주차/동선 블록인지 확인"""
        return self.get_layer_from_block(block_name) is not None

    def transform_vertices(self, vertices, matrix, mm_to_m=True):
        """변환 매트릭스 적용 및 mm→m 변환"""
        transformed = []
        for v in vertices:
            vec = Vec3(v[0], v[1], 0)
            transformed_vec = matrix.transform(vec)

            if mm_to_m:
                x = transformed_vec.x / 1000.0
                y = transformed_vec.y / 1000.0
            else:
                x = transformed_vec.x
                y = transformed_vec.y

            transformed.append((x, y))
        return transformed

    def extract_from_block(self, block_name, accumulated_matrix):
        """블록에서 LWPOLYLINE 추출"""
        if block_name not in self.doc.blocks:
            return []

        block = self.doc.blocks[block_name]
        results = []

        for entity in block:
            if entity.dxftype() == 'LWPOLYLINE' and entity.closed:
                vertices = list(entity.get_points())
                if len(vertices) >= 3:
                    # 블록 내부 좌표를 가져옴
                    coords = [(v[0], v[1]) for v in vertices]
                    # 누적된 변환 매트릭스 적용
                    world_coords = self.transform_vertices(coords, accumulated_matrix)

                    # 비정상적인 좌표 필터링 (주차면은 -1000m ~ 2000m 범위에 있어야 함)
                    valid_coords = True
                    for x, y in world_coords:
                        if x < -1000 or x > 2000 or y < -1000 or y > 2000:
                            valid_coords = False
                            break

                    if not valid_coords:
                        continue

                    # 면적 계산 (너무 작은 폴리곤 필터링)
                    area = self.calculate_area(world_coords)
                    if area >= 2.0:  # 최소 2m² 이상만 (주차면은 보통 10-15m²)
                        results.append(world_coords)

        return results

    def calculate_area(self, vertices):
        """폴리곤 면적 계산 (신발끈 공식)"""
        n = len(vertices)
        if n < 3:
            return 0

        area = 0
        for i in range(n):
            j = (i + 1) % n
            area += vertices[i][0] * vertices[j][1]
            area -= vertices[j][0] * vertices[i][1]
        return abs(area) / 2

    def process_insert(self, insert, parent_matrix, depth=0):
        """INSERT 재귀 처리"""
        if depth > 20:
            return

        block_name = insert.dxf.name
        insert_matrix = insert.matrix44()
        # 매트릭스 곱셈 순서 수정: 자식 @ 부모
        accumulated_matrix = insert_matrix @ parent_matrix

        # 주차면 블록인 경우 추출
        if self.should_extract(block_name):
            layer = self.get_layer_from_block(block_name)
            polylines = self.extract_from_block(block_name, accumulated_matrix)

            for vertices in polylines:
                self.parking_geometries.append({
                    'vertices': vertices,
                    'layer': layer,
                    'block_name': block_name
                })
                self.stats[layer] += 1

        # 중첩 블록 처리 - should_extract와 관계없이 항상 재귀 처리
        # 이렇게 해야 240426_지하 같은 컨테이너 블록 내부의 주차면도 찾음
        if block_name in self.doc.blocks:
            for entity in self.doc.blocks[block_name]:
                if entity.dxftype() == 'INSERT':
                    self.process_insert(entity, accumulated_matrix, depth + 1)

    def collect_disabled_markers(self):
        """장애인 마크 위치 수집"""
        disabled_positions = []

        msp = self.doc.modelspace()
        for entity in msp:
            if entity.dxftype() == 'INSERT' and entity.dxf.name == 'A$C3CD3280F':
                main_matrix = entity.matrix44()
                main_block = self.doc.blocks[entity.dxf.name]

                for sub_entity in main_block:
                    if sub_entity.dxftype() == 'INSERT' and '장애인' in sub_entity.dxf.name:
                        # 장애인 마크의 월드 좌표 계산
                        sub_matrix = sub_entity.matrix44()
                        accumulated = sub_matrix @ main_matrix

                        # 원점을 변환하여 위치 추출
                        origin = Vec3(0, 0, 0)
                        transformed = accumulated.transform(origin)

                        # mm → m 변환
                        x = transformed.x / 1000.0
                        y = transformed.y / 1000.0

                        # 유효 범위 체크
                        if -1000 <= x <= 2000 and -1000 <= y <= 2000:
                            disabled_positions.append((x, y))

                break

        return disabled_positions

    def reclassify_disabled_parking(self, disabled_positions, tolerance=5.0):
        """장애인 마크 근처 주차면을 장애인 주차로 재분류"""
        if not disabled_positions:
            return 0

        reclassified_count = 0

        for geom in self.parking_geometries:
            # 이미 장애인 주차가 아닌 경우만 체크
            if geom['layer'] != 'p-parking-disable':
                # 폴리곤 중심점 계산
                vertices = geom['vertices']
                center_x = sum(v[0] for v in vertices) / len(vertices)
                center_y = sum(v[1] for v in vertices) / len(vertices)

                # 가장 가까운 장애인 마크와의 거리 계산
                for marker_x, marker_y in disabled_positions:
                    distance = ((center_x - marker_x)**2 + (center_y - marker_y)**2)**0.5

                    if distance < tolerance:  # 5m 이내
                        # 기존 레이어 통계 감소
                        self.stats[geom['layer']] -= 1
                        if self.stats[geom['layer']] == 0:
                            del self.stats[geom['layer']]

                        # 장애인 주차로 재분류
                        geom['layer'] = 'p-parking-disable'
                        self.stats['p-parking-disable'] = self.stats.get('p-parking-disable', 0) + 1
                        reclassified_count += 1
                        break  # 하나의 마크만 매칭

        return reclassified_count

    def extract_all(self, tolerance=7.0):
        """1단계: 주차면 추출"""
        print("=" * 70)
        print("STEP 1: Central.dxf에서 주차면 추출")
        print("=" * 70)

        msp = self.doc.modelspace()
        identity_matrix = Matrix44()

        for entity in msp:
            if entity.dxftype() == 'INSERT':
                self.process_insert(entity, identity_matrix)

        print(f"\n✅ 총 {len(self.parking_geometries)}개 주차면/동선 추출 완료")

        # 장애인 주차 재분류
        print(f"\n장애인 주차 재분류 중 (tolerance={tolerance}m)...")
        disabled_positions = self.collect_disabled_markers()
        print(f"  장애인 마크 발견: {len(disabled_positions)}개")

        if disabled_positions:
            reclassified = self.reclassify_disabled_parking(disabled_positions, tolerance=tolerance)
            print(f"  재분류 완료: {reclassified}개 주차면 → 장애인 주차")

        if self.stats:
            print("\n레이어별 통계:")
            for layer, count in sorted(self.stats.items()):
                layer_info = PARKING_LAYERS.get(layer) or CIRCULATION_LAYERS.get(layer)
                layer_name = layer_info['name'] if layer_info else layer
                print(f"  {layer_name} ({layer}): {count}개")

    def create_clean_dxf(self, output_file, normalize=True):
        """2단계: 깨끗한 DXF 파일 생성"""
        print("\n" + "=" * 70)
        print(f"STEP 2: 깨끗한 DXF 파일 생성: {output_file}")
        print("=" * 70)

        if not self.parking_geometries:
            print("⚠️  추출된 geometry가 없습니다.")
            return

        # 좌표 정규화 - 비정상적인 좌표 필터링
        offset_x, offset_y = (0, 0)
        if normalize:
            # 합리적인 범위의 좌표만 사용 (-1000m ~ 2000m)
            valid_coords = []
            for geom in self.parking_geometries:
                for v in geom['vertices']:
                    if -1000 <= v[0] <= 2000 and -1000 <= v[1] <= 2000:
                        valid_coords.append(v)

            if valid_coords:
                min_x = min(v[0] for v in valid_coords)
                min_y = min(v[1] for v in valid_coords)
                offset_x, offset_y = min_x, min_y
                print(f"좌표 정규화 오프셋: ({offset_x:.2f}m, {offset_y:.2f}m)")
            else:
                print("⚠️  유효한 좌표를 찾을 수 없습니다.")

        # 새 DXF 문서 생성
        new_doc = ezdxf.new('R2010')
        new_msp = new_doc.modelspace()

        # 레이어 생성
        all_layers = {**PARKING_LAYERS, **CIRCULATION_LAYERS}
        for layer_name, layer_info in all_layers.items():
            new_doc.layers.add(
                layer_name,
                color=layer_info['color'],
                linetype='CONTINUOUS'
            )

        # Geometry 추가
        for geom in self.parking_geometries:
            layer = geom['layer']
            vertices = geom['vertices']

            normalized_vertices = [
                (v[0] - offset_x, v[1] - offset_y)
                for v in vertices
            ]

            new_msp.add_lwpolyline(
                normalized_vertices,
                close=True,
                dxfattribs={'layer': layer}
            )

        new_doc.saveas(output_file)
        print(f"✅ 저장 완료!")
        print(f"   - 파일: {output_file}")
        print(f"   - Geometry: {len(self.parking_geometries)}개")
        print(f"   - 레이어: {len(self.stats)}개")

    def convert_to_csv(self, dxf_file, csv_file):
        """3단계: 가공된 DXF를 CSV로 변환 (Vertex-per-row 형식)"""
        print("\n" + "=" * 70)
        print(f"STEP 3: DXF → CSV 변환: {csv_file}")
        print("=" * 70)

        doc = ezdxf.readfile(dxf_file)
        msp = doc.modelspace()

        # 레이어별 색상 매핑
        layer_colors = {}
        all_layers = {**PARKING_LAYERS, **CIRCULATION_LAYERS}
        for layer_name, layer_info in all_layers.items():
            # AutoCAD 색상을 RGB hex로 변환
            aci_color = layer_info['color']
            layer_colors[layer_name] = self.aci_to_hex(aci_color)

        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # osong과 동일한 헤더 형식
            writer.writerow(['X', 'Y', 'Z', 'Layer', 'PaperSpace', 'SubClasses',
                           'Linetype', 'EntityHandle', 'Text', 'OGR_STYLE'])

            vertex_count = 0
            entity_count = 0
            for entity in msp:
                if entity.dxftype() == 'LWPOLYLINE':
                    layer = entity.dxf.layer
                    vertices = list(entity.get_points())

                    # 색상 정보
                    color_hex = layer_colors.get(layer, '#000000')
                    ogr_style = f"PEN(c:{color_hex})"

                    # 각 폴리곤마다 고유한 EntityHandle 생성 (16진수)
                    entity_handle = format(entity_count, 'X')

                    # 폴리곤 닫기: 첫 번째 꼭짓점을 마지막에 추가
                    if len(vertices) > 0:
                        vertices_closed = list(vertices) + [vertices[0]]
                    else:
                        vertices_closed = vertices

                    # 각 꼭짓점을 별도 행으로 출력
                    for v in vertices_closed:
                        writer.writerow([
                            f"{v[0]:.8f}",  # X
                            f"{v[1]:.8f}",  # Y
                            "0",            # Z
                            layer,          # Layer
                            "",             # PaperSpace
                            "AcDbEntity:AcDbPolyline",  # SubClasses
                            "",             # Linetype
                            entity_handle,  # EntityHandle (폴리곤 구분자)
                            "",             # Text
                            ogr_style       # OGR_STYLE
                        ])
                        vertex_count += 1

                    entity_count += 1

        print(f"✅ CSV 변환 완료!")
        print(f"   - 파일: {csv_file}")
        print(f"   - 폴리곤: {entity_count}개")
        print(f"   - 꼭짓점: {vertex_count}개")

    def aci_to_hex(self, aci_color):
        """AutoCAD ACI 색상을 RGB Hex로 변환"""
        # AutoCAD 기본 색상 매핑
        aci_colors = {
            1: '#FF0000',  # Red
            2: '#FFFF00',  # Yellow
            3: '#00FF00',  # Green
            4: '#00FFFF',  # Cyan
            5: '#0000FF',  # Blue
            6: '#FF00FF',  # Magenta
            7: '#000000',  # Black/White
            8: '#808080',  # Gray
            9: '#C0C0C0',  # Light Gray
        }
        return aci_colors.get(aci_color, '#000000')


def main():
    parser = argparse.ArgumentParser(description='Central.dxf 재가공 도구')
    parser.add_argument('input', help='입력 DXF 파일', default='central.dxf', nargs='?')
    parser.add_argument('--output-dxf', help='출력 DXF 파일', default='central_processed.dxf')
    parser.add_argument('--output-csv', help='출력 CSV 파일', default='central_processed.csv')
    parser.add_argument('--normalize', action='store_true', default=True, help='좌표 정규화')
    parser.add_argument('--layer-mapping', help='레이어 매핑 JSON 파일 경로', default=None)
    parser.add_argument('--tolerance', type=float, default=7.0, help='장애인 주차 재분류 거리 (m)')

    args = parser.parse_args()

    # 레이어 매핑 로드
    layer_mapping = None
    if args.layer_mapping:
        try:
            with open(args.layer_mapping, 'r', encoding='utf-8') as f:
                layer_mapping = json.load(f)
            print(f"✅ 레이어 매핑 로드: {len(layer_mapping)}개 블록")
        except Exception as e:
            print(f"⚠️ 레이어 매핑 로드 실패: {e}")
            print("   기본 매핑을 사용합니다.")

    # 처리 시작
    processor = CentralDXFProcessor(args.input, layer_mapping=layer_mapping)

    # Step 1: 주차면 추출
    processor.extract_all(tolerance=args.tolerance)

    # Step 2: 깨끗한 DXF 생성
    processor.create_clean_dxf(args.output_dxf, normalize=args.normalize)

    # Step 3: CSV 변환
    processor.convert_to_csv(args.output_dxf, args.output_csv)

    print("\n" + "=" * 70)
    print("✅ 모든 처리 완료!")
    print("=" * 70)
    print(f"\n생성된 파일:")
    print(f"  1. {args.output_dxf} (깨끗한 DXF - AutoCAD/QGIS에서 확인)")
    print(f"  2. {args.output_csv} (CSV - 뷰어에 업로드)")


if __name__ == '__main__':
    main()
