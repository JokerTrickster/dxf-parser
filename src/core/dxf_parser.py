"""
DXF Parser - Output Generation
DXF 파서 - 출력 생성
"""
import ezdxf
from typing import List
import logging

from ..models.extracted_entity import ExtractedEntity
from ..models.layer_schema import LayerSchema


class DXFParser:
    """DXF 파일 읽기/쓰기"""

    def __init__(self, layer_schema: LayerSchema):
        """
        Args:
            layer_schema: 레이어 스키마
        """
        self.layer_schema = layer_schema
        self.logger = logging.getLogger(__name__)

    def read(self, dxf_path: str) -> ezdxf.document.Drawing:
        """
        DXF 파일 읽기

        Args:
            dxf_path: DXF 파일 경로

        Returns:
            ezdxf Document 객체
        """
        self.logger.info(f"DXF 파일 읽기: {dxf_path}")
        return ezdxf.readfile(dxf_path)

    def create_output_dxf(
        self,
        entities: List[ExtractedEntity],
        output_path: str,
        add_labels: bool = True
    ):
        """
        분류된 엔티티로 새 DXF 파일 생성

        Args:
            entities: 분류된 엔티티 리스트
            output_path: 출력 파일 경로
            add_labels: ID 라벨 추가 여부
        """
        self.logger.info(f"DXF 파일 생성 시작: {output_path}")

        # 새 DXF 문서 생성
        doc = ezdxf.new('R2010')
        msp = doc.modelspace()

        # 레이어 생성 (중복 제거)
        layer_colors = {}
        for entity in entities:
            if not entity.classification:
                continue

            layer_name = entity.output_layer
            category = entity.classification.category
            type_name = entity.classification.type

            if layer_name not in layer_colors:
                color = self.layer_schema.get_color(category, type_name)
                doc.layers.add(layer_name, color=color)
                layer_colors[layer_name] = color

        # 엔티티 그리기
        for idx, entity in enumerate(entities, start=1):
            if not entity.vertices:
                continue

            layer_name = entity.output_layer

            # LWPOLYLINE 생성
            points = [(x, y) for x, y in entity.vertices]
            msp.add_lwpolyline(
                points,
                close=True,
                dxfattribs={'layer': layer_name}
            )

            # ID 라벨 추가
            if add_labels:
                center = entity.center
                msp.add_mtext(
                    str(idx),
                    dxfattribs={
                        'layer': layer_name,
                        'insert': (center[0], center[1]),
                        'char_height': 200,
                        'attachment_point': 5  # 중앙
                    }
                )

        # 저장
        doc.saveas(output_path)
        self.logger.info(f"DXF 파일 생성 완료: {output_path}")

    def export_to_csv(
        self,
        entities: List[ExtractedEntity],
        csv_path: str
    ):
        """
        엔티티를 CSV로 내보내기

        Args:
            entities: 엔티티 리스트
            csv_path: CSV 파일 경로
        """
        import csv

        self.logger.info(f"CSV 파일 생성: {csv_path}")

        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # 헤더
            writer.writerow([
                'id',
                'block_name',
                'category',
                'type',
                'confidence',
                'layer',
                'center_x',
                'center_y',
                'rotation',
                'area',
                'vertex_count',
                'vertices',
                'reasoning'
            ])

            # 데이터
            for idx, entity in enumerate(entities, start=1):
                classification = entity.classification

                # 꼭짓점을 문자열로 변환
                vertices_str = ';'.join([
                    f"{x:.2f},{y:.2f}" for x, y in entity.vertices
                ])

                writer.writerow([
                    idx,
                    entity.block_name,
                    classification.category if classification else 'N/A',
                    classification.type if classification else 'N/A',
                    f"{classification.confidence:.2f}" if classification else '0.00',
                    entity.output_layer,
                    f"{entity.center[0]:.2f}",
                    f"{entity.center[1]:.2f}",
                    f"{entity.rotation:.2f}",
                    f"{entity.area:.2f}" if entity.area else '0.00',
                    len(entity.vertices),
                    vertices_str,
                    classification.reasoning if classification else 'N/A'
                ])

        self.logger.info(f"CSV 파일 생성 완료: {csv_path}")
