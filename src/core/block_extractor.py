"""
Block Extraction from DXF
DXF에서 블록 추출
"""
from typing import List, Tuple, Optional, Dict
import ezdxf
from ezdxf.math import Matrix44
import logging

from ..models.extracted_entity import ExtractedEntity
from .geometry_processor import GeometryProcessor


class BlockExtractor:
    """DXF 블록 추출기"""

    def __init__(self, doc: ezdxf.document.Drawing):
        """
        Args:
            doc: ezdxf Document 객체
        """
        self.doc = doc
        self.logger = logging.getLogger(__name__)
        self.geometry_processor = GeometryProcessor()
        self.block_geometry_cache: Dict[str, List[Tuple[float, float]]] = {}

    def extract_all_blocks(
        self,
        max_depth: int = 10
    ) -> List[ExtractedEntity]:
        """
        모델 스페이스에서 모든 블록 추출

        Args:
            max_depth: 최대 재귀 깊이

        Returns:
            추출된 엔티티 리스트
        """
        entities = []
        modelspace = self.doc.modelspace()

        self.logger.info(f"모델 스페이스 탐색 시작 (최대 깊이: {max_depth})")

        # 모든 INSERT 엔티티 탐색
        for entity in modelspace:
            if entity.dxftype() == 'INSERT':
                extracted = self._extract_from_insert(
                    entity,
                    depth=0,
                    max_depth=max_depth
                )
                entities.extend(extracted)

        self.logger.info(f"총 {len(entities)}개 블록 추출 완료")
        return entities

    def _extract_from_insert(
        self,
        insert_entity,
        depth: int,
        max_depth: int,
        parent_transform: Optional[Matrix44] = None
    ) -> List[ExtractedEntity]:
        """
        INSERT 엔티티에서 재귀적으로 블록 추출

        Args:
            insert_entity: INSERT 엔티티
            depth: 현재 재귀 깊이
            max_depth: 최대 재귀 깊이
            parent_transform: 부모 변환 행렬

        Returns:
            추출된 엔티티 리스트
        """
        if depth > max_depth:
            self.logger.warning(f"최대 재귀 깊이 {max_depth} 초과")
            return []

        entities = []
        block_name = insert_entity.dxf.name

        # 블록 정의 조회
        if block_name not in self.doc.blocks:
            self.logger.warning(f"블록 정의 없음: {block_name}")
            return []

        block = self.doc.blocks[block_name]

        # 블록 기하학 추출
        geometry = self._extract_block_geometry(block)

        if geometry:
            # 변환 정보
            insert_point = (insert_entity.dxf.insert.x, insert_entity.dxf.insert.y)
            rotation = insert_entity.dxf.rotation
            scale_x = getattr(insert_entity.dxf, 'xscale', 1.0)
            scale_y = getattr(insert_entity.dxf, 'yscale', 1.0)

            # 좌표 변환 적용
            transformed_vertices = self.geometry_processor.transform_vertices(
                geometry,
                insert_point,
                rotation,
                scale_x,
                scale_y
            )

            # 면적 계산
            area = self.geometry_processor.calculate_area(transformed_vertices)

            # 엔티티 생성
            entity = ExtractedEntity(
                block_name=block_name,
                geometry_type='LWPOLYLINE',  # 기본값
                vertices=transformed_vertices,
                area=area,
                insert_point=insert_point,
                rotation=rotation
            )
            entities.append(entity)

        # 중첩된 블록 재귀 탐색
        for nested_entity in block:
            if nested_entity.dxftype() == 'INSERT':
                nested_entities = self._extract_from_insert(
                    nested_entity,
                    depth=depth + 1,
                    max_depth=max_depth,
                    parent_transform=None
                )
                entities.extend(nested_entities)

        return entities

    def _extract_block_geometry(
        self,
        block
    ) -> Optional[List[Tuple[float, float]]]:
        """
        블록에서 기하학적 정보 추출 (가장 큰 LWPOLYLINE 선택)

        Args:
            block: 블록 정의

        Returns:
            꼭짓점 리스트 또는 None
        """
        block_name = block.name

        # 캐시 확인
        if block_name in self.block_geometry_cache:
            return self.block_geometry_cache[block_name]

        largest_polyline = None
        largest_area = 0.0

        for entity in block:
            vertices = None

            # LWPOLYLINE
            if entity.dxftype() == 'LWPOLYLINE':
                vertices = [
                    (point[0], point[1])
                    for point in entity.get_points('xy')
                ]

            # POLYLINE
            elif entity.dxftype() == 'POLYLINE':
                vertices = [
                    (vertex.dxf.location.x, vertex.dxf.location.y)
                    for vertex in entity.vertices
                ]

            # CIRCLE
            elif entity.dxftype() == 'CIRCLE':
                center = (entity.dxf.center.x, entity.dxf.center.y)
                radius = entity.dxf.radius
                vertices = self.geometry_processor.extract_circle_vertices(
                    center, radius
                )

            # 면적 계산
            if vertices and len(vertices) >= 3:
                area = self.geometry_processor.calculate_area(vertices)
                if area > largest_area:
                    largest_area = area
                    largest_polyline = vertices

        # 캐시 저장
        if largest_polyline:
            self.block_geometry_cache[block_name] = largest_polyline

        return largest_polyline
