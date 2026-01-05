"""
MyGeoData.cloud CSV Format Converter
DXF 파일을 MyGeoData.cloud와 동일한 형식의 CSV로 변환
"""
import ezdxf
import math
import os
import logging
from typing import List, Dict
from ...domain.repositories.converter_repository import IConverter

logger = logging.getLogger(__name__)


class MyGeoDataCSVConverter(IConverter):
    """DXF to MyGeoData CSV Converter (IConverter 구현)"""

    # 레이어별 색상 매핑 (AutoCAD 컬러 인덱스 기반)
    LAYER_COLOR_MAP = {
        'p-parking-basic': '#000000',
        'p-parking-large': '#00ff00',
        'p-parking-disable': '#ff0000',
        'p-parking-disabled': '#ff0000',
        'p-parking-small': '#ffff00',
        'p-parking-compact': '#ffff00',
        'p-parking-electric': '#0000ff',
        'p-parking-large-electric': '#0000ff',
        'p-parking-women': '#ff00ff',
        'p-parking-large-women': '#ff00ff',
        's-structure-column': '#00ffff',
        's-structure-wall': '#808080',
        'c-circulation-stairs': '#ffa500',
        'building-outline': '#808080',
    }

    CSV_HEADERS = [
        'X', 'Y', 'Z', 'Layer', 'PaperSpace',
        'SubClasses', 'Linetype', 'EntityHandle',
        'Text', 'OGR_STYLE'
    ]

    def convert(self, input_path: str, output_path: str) -> Dict:
        """
        DXF 파일을 MyGeoData CSV 형식으로 변환

        Args:
            input_path: 입력 DXF 파일 경로
            output_path: 출력 CSV 파일 경로

        Returns:
            변환 통계 딕셔너리
        """
        logger.info(f"DXF 파일 읽기: {input_path}")
        doc = ezdxf.readfile(input_path)
        msp = doc.modelspace()

        rows = []
        stats = {
            'lwpolyline': 0,
            'line': 0,
            'arc': 0,
            'other': 0,
            'total': 0
        }

        # 모든 엔티티 처리
        for entity in msp:
            entity_type = entity.dxftype()

            try:
                if entity_type == 'LWPOLYLINE':
                    entity_rows = self._process_lwpolyline(entity)
                    rows.extend(entity_rows)
                    stats['lwpolyline'] += 1

                elif entity_type == 'LINE':
                    entity_rows = self._process_line(entity)
                    rows.extend(entity_rows)
                    stats['line'] += 1

                elif entity_type == 'ARC':
                    entity_rows = self._process_arc(entity)
                    rows.extend(entity_rows)
                    stats['arc'] += 1

                else:
                    stats['other'] += 1

            except Exception as e:
                logger.warning(f"엔티티 처리 실패 ({entity_type}): {e}")
                stats['other'] += 1

        stats['total'] = stats['lwpolyline'] + stats['line'] + stats['arc']

        # CSV 파일 쓰기
        logger.info(f"CSV 파일 쓰기: {output_path}")
        self._write_csv(output_path, rows)

        logger.info(f"변환 완료: {stats['total']}개 엔티티, {len(rows)}개 행")
        return stats

    def validate_input(self, file_path: str) -> bool:
        """
        입력 파일 유효성 검증

        Args:
            file_path: 파일 경로

        Returns:
            유효성 여부
        """
        # 파일 존재 여부
        if not os.path.exists(file_path):
            return False

        # DXF 확장자 확인
        if not file_path.lower().endswith('.dxf'):
            return False

        # DXF 파일 읽기 시도
        try:
            ezdxf.readfile(file_path)
            return True
        except Exception:
            return False

    def _get_layer_color(self, layer_name: str) -> str:
        """레이어 이름으로부터 색상 코드 반환"""
        return self.LAYER_COLOR_MAP.get(layer_name, '#000000')

    def _format_coordinate(self, value: float) -> str:
        """좌표값을 MyGeoData 형식으로 포맷팅"""
        return f"{value:.12f}".rstrip('0').rstrip('.')

    def _process_lwpolyline(self, entity) -> List[List]:
        """LWPOLYLINE 엔티티 처리"""
        layer = entity.dxf.layer
        handle = entity.dxf.handle
        color_hex = self._get_layer_color(layer)

        # 폴리라인의 모든 점 추출
        points = list(entity.get_points('xy'))

        # 닫힌 폴리곤인 경우 첫 점을 마지막에 추가
        if entity.closed and len(points) > 0:
            points.append(points[0])

        rows = []
        for point in points:
            x, y = point[0], point[1]
            z = 0

            row = [
                self._format_coordinate(x),
                self._format_coordinate(y),
                str(z),
                layer,
                '',
                'AcDbEntity:AcDbPolyline',
                '',
                handle,
                '',
                f'PEN(c:{color_hex})'
            ]
            rows.append(row)

        return rows

    def _process_line(self, entity) -> List[List]:
        """LINE 엔티티 처리"""
        layer = entity.dxf.layer
        handle = entity.dxf.handle
        color_hex = self._get_layer_color(layer)

        start = entity.dxf.start
        end = entity.dxf.end

        rows = []
        for point in [start, end]:
            row = [
                self._format_coordinate(point.x),
                self._format_coordinate(point.y),
                self._format_coordinate(point.z),
                layer,
                '',
                'AcDbEntity:AcDbLine',
                '',
                handle,
                '',
                f'PEN(c:{color_hex})'
            ]
            rows.append(row)

        return rows

    def _process_arc(self, entity, segments: int = 32) -> List[List]:
        """ARC 엔티티 처리 (다각형으로 근사)"""
        layer = entity.dxf.layer
        handle = entity.dxf.handle
        color_hex = self._get_layer_color(layer)

        center = entity.dxf.center
        radius = entity.dxf.radius
        start_angle = math.radians(entity.dxf.start_angle)
        end_angle = math.radians(entity.dxf.end_angle)

        # 각도 정규화
        if end_angle < start_angle:
            end_angle += 2 * math.pi

        angle_step = (end_angle - start_angle) / segments

        rows = []
        for i in range(segments + 1):
            angle = start_angle + i * angle_step
            x = center.x + radius * math.cos(angle)
            y = center.y + radius * math.sin(angle)
            z = center.z

            row = [
                self._format_coordinate(x),
                self._format_coordinate(y),
                self._format_coordinate(z),
                layer,
                '',
                'AcDbEntity:AcDbCircle:AcDbArc',
                '',
                handle,
                '',
                f'PEN(c:{color_hex})'
            ]
            rows.append(row)

        return rows

    def _write_csv(self, csv_path: str, rows: List[List]):
        """CSV 파일 작성 (MyGeoData 형식)"""
        with open(csv_path, 'w', encoding='utf-8') as f:
            # 헤더
            f.write(','.join(self.CSV_HEADERS) + '\n')

            # 데이터 행
            for row in rows:
                formatted_row = []
                for i, value in enumerate(row):
                    if i == 7:  # EntityHandle 필드
                        formatted_row.append(f'"{value}"')
                    elif value == '':
                        formatted_row.append('')
                    else:
                        formatted_row.append(str(value))
                f.write(','.join(formatted_row) + '\n')
