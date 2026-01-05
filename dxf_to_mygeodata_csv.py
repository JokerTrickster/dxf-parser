#!/usr/bin/env python3
"""
DXF to MyGeoData CSV Converter
DXF 파일을 MyGeoData.cloud와 동일한 형식의 CSV로 변환

Usage:
    python dxf_to_mygeodata_csv.py input.dxf output.csv
"""

import sys
import csv
import ezdxf
from typing import List, Tuple


def get_layer_color_hex(layer_name: str) -> str:
    """
    레이어 이름으로부터 색상 코드 반환

    Args:
        layer_name: 레이어 이름

    Returns:
        Hex 색상 코드 (예: #000000, #00ff00)
    """
    # 레이어별 색상 매핑 (AutoCAD 컬러 인덱스 기반)
    color_map = {
        'p-parking-basic': '#000000',       # 흰색/검은색
        'p-parking-large': '#00ff00',       # 초록색
        'p-parking-disable': '#ff0000',     # 빨간색
        'p-parking-disabled': '#ff0000',    # 빨간색
        'p-parking-small': '#ffff00',       # 노란색
        'p-parking-compact': '#ffff00',     # 노란색
        'p-parking-electric': '#0000ff',    # 파란색
        'p-parking-large-electric': '#0000ff',  # 파란색
        'p-parking-women': '#ff00ff',       # 마젠타
        'p-parking-large-women': '#ff00ff', # 마젠타
        's-structure-column': '#00ffff',    # 시안
        's-structure-wall': '#808080',      # 회색
        'c-circulation-stairs': '#ffa500',  # 주황색
        'building-outline': '#808080',      # 회색
    }

    return color_map.get(layer_name, '#000000')


def convert_dxf_to_mygeodata_csv(dxf_path: str, csv_path: str):
    """
    DXF 파일을 MyGeoData.cloud 형식의 CSV로 변환

    Args:
        dxf_path: 입력 DXF 파일 경로
        csv_path: 출력 CSV 파일 경로
    """
    print(f"DXF 파일 읽기: {dxf_path}")
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    # CSV 헤더
    headers = [
        'X', 'Y', 'Z', 'Layer', 'PaperSpace',
        'SubClasses', 'Linetype', 'EntityHandle',
        'Text', 'OGR_STYLE'
    ]

    rows = []
    entity_count = 0

    # 모든 엔티티 처리
    for entity in msp:
        entity_type = entity.dxftype()

        # LWPOLYLINE 처리
        if entity_type == 'LWPOLYLINE':
            entity_count += 1
            layer = entity.dxf.layer
            handle = entity.dxf.handle
            color_hex = get_layer_color_hex(layer)

            # 폴리라인의 모든 점 추출
            points = list(entity.get_points('xy'))

            # 닫힌 폴리곤인 경우 첫 점을 마지막에 추가
            if entity.closed and len(points) > 0:
                points.append(points[0])

            # 각 점을 CSV 행으로 변환
            for point in points:
                x, y = point[0], point[1]
                z = 0  # 2D 도면이므로 Z=0

                # 숫자를 mygeodata.cloud 형식으로 포맷팅
                x_str = f"{x:.12f}".rstrip('0').rstrip('.')
                y_str = f"{y:.12f}".rstrip('0').rstrip('.')

                row = [
                    x_str,                          # X (formatted)
                    y_str,                          # Y (formatted)
                    str(z),                         # Z
                    layer,                          # Layer
                    '',                             # PaperSpace
                    'AcDbEntity:AcDbPolyline',      # SubClasses
                    '',                             # Linetype
                    handle,                         # EntityHandle (no quotes, csv writer will add)
                    '',                             # Text
                    f'PEN(c:{color_hex})'          # OGR_STYLE
                ]
                rows.append(row)

        # LINE 처리
        elif entity_type == 'LINE':
            entity_count += 1
            layer = entity.dxf.layer
            handle = entity.dxf.handle
            color_hex = get_layer_color_hex(layer)

            # LINE은 시작점과 끝점만 있음
            start = entity.dxf.start
            end = entity.dxf.end

            for point in [start, end]:
                # 숫자를 mygeodata.cloud 형식으로 포맷팅
                x_str = f"{point.x:.12f}".rstrip('0').rstrip('.')
                y_str = f"{point.y:.12f}".rstrip('0').rstrip('.')
                z_str = f"{point.z:.12f}".rstrip('0').rstrip('.')

                row = [
                    x_str,                          # X (formatted)
                    y_str,                          # Y (formatted)
                    z_str,                          # Z (formatted)
                    layer,                          # Layer
                    '',                             # PaperSpace
                    'AcDbEntity:AcDbLine',          # SubClasses
                    '',                             # Linetype
                    handle,                         # EntityHandle (no quotes)
                    '',                             # Text
                    f'PEN(c:{color_hex})'          # OGR_STYLE
                ]
                rows.append(row)

        # ARC 처리
        elif entity_type == 'ARC':
            entity_count += 1
            layer = entity.dxf.layer
            handle = entity.dxf.handle
            color_hex = get_layer_color_hex(layer)

            # ARC를 여러 점으로 근사 (32개 점)
            import math
            center = entity.dxf.center
            radius = entity.dxf.radius
            start_angle = math.radians(entity.dxf.start_angle)
            end_angle = math.radians(entity.dxf.end_angle)

            # 각도 정규화
            if end_angle < start_angle:
                end_angle += 2 * math.pi

            # 32개 점으로 분할
            segments = 32
            angle_step = (end_angle - start_angle) / segments

            for i in range(segments + 1):
                angle = start_angle + i * angle_step
                x = center.x + radius * math.cos(angle)
                y = center.y + radius * math.sin(angle)
                z = center.z

                # 숫자를 mygeodata.cloud 형식으로 포맷팅
                x_str = f"{x:.12f}".rstrip('0').rstrip('.')
                y_str = f"{y:.12f}".rstrip('0').rstrip('.')
                z_str = f"{z:.12f}".rstrip('0').rstrip('.')

                row = [
                    x_str,                          # X (formatted)
                    y_str,                          # Y (formatted)
                    z_str,                          # Z (formatted)
                    layer,                          # Layer
                    '',                             # PaperSpace
                    'AcDbEntity:AcDbCircle:AcDbArc',  # SubClasses (mygeodata format)
                    '',                             # Linetype
                    handle,                         # EntityHandle (no quotes)
                    '',                             # Text
                    f'PEN(c:{color_hex})'          # OGR_STYLE
                ]
                rows.append(row)

    # CSV 파일 쓰기 (수동으로 작성하여 mygeodata.cloud 형식 정확히 재현)
    print(f"CSV 파일 쓰기: {csv_path}")
    with open(csv_path, 'w', encoding='utf-8') as f:
        # 헤더
        f.write(','.join(headers) + '\n')

        # 데이터 행
        for row in rows:
            # EntityHandle 필드만 따옴표로 감싸고 나머지는 그대로
            formatted_row = []
            for i, value in enumerate(row):
                if i == 7:  # EntityHandle 필드 (인덱스 7)
                    formatted_row.append(f'"{value}"')
                elif value == '':
                    formatted_row.append('')
                else:
                    formatted_row.append(str(value))
            f.write(','.join(formatted_row) + '\n')

    print(f"변환 완료!")
    print(f"  처리된 엔티티: {entity_count}개")
    print(f"  출력 행 수: {len(rows)}개 (헤더 제외)")


def main():
    if len(sys.argv) != 3:
        print("Usage: python dxf_to_mygeodata_csv.py <input.dxf> <output.csv>")
        print("\nExample:")
        print("  python dxf_to_mygeodata_csv.py osong-b1_B1_converted.dxf output.csv")
        sys.exit(1)

    dxf_path = sys.argv[1]
    csv_path = sys.argv[2]

    try:
        convert_dxf_to_mygeodata_csv(dxf_path, csv_path)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
