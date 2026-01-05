"""
Classification Service
분류 관련 비즈니스 로직 서비스
"""
from typing import List
from ...domain.entities.dxf_entity import DXFEntity


class ClassificationService:
    """분류 서비스"""

    @staticmethod
    def filter_by_category(
        entities: List[DXFEntity],
        category: str
    ) -> List[DXFEntity]:
        """
        카테고리로 엔티티 필터링

        Args:
            entities: DXF 엔티티 리스트
            category: 필터링할 카테고리

        Returns:
            필터링된 엔티티 리스트
        """
        return [
            e for e in entities
            if e.classification and e.classification.category == category
        ]

    @staticmethod
    def filter_by_type(
        entities: List[DXFEntity],
        type_name: str
    ) -> List[DXFEntity]:
        """
        타입으로 엔티티 필터링

        Args:
            entities: DXF 엔티티 리스트
            type_name: 필터링할 타입

        Returns:
            필터링된 엔티티 리스트
        """
        return [
            e for e in entities
            if e.classification and e.classification.type == type_name
        ]

    @staticmethod
    def get_unclassified(entities: List[DXFEntity]) -> List[DXFEntity]:
        """
        미분류 엔티티 조회

        Args:
            entities: DXF 엔티티 리스트

        Returns:
            미분류 엔티티 리스트
        """
        return [e for e in entities if e.classification is None]

    @staticmethod
    def get_statistics(entities: List[DXFEntity]) -> dict:
        """
        분류 통계 생성

        Args:
            entities: DXF 엔티티 리스트

        Returns:
            카테고리별, 타입별 통계 딕셔너리
        """
        from collections import Counter

        categories = Counter()
        types = Counter()

        for entity in entities:
            if entity.classification:
                categories[entity.classification.category] += 1
                types[entity.classification.type] += 1

        return {
            'total': len(entities),
            'classified': len([e for e in entities if e.classification]),
            'unclassified': len([e for e in entities if not e.classification]),
            'by_category': dict(categories),
            'by_type': dict(types)
        }
