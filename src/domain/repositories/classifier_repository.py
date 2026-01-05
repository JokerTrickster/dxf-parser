"""
Classifier Repository Interface
분류기 인터페이스
"""
from abc import ABC, abstractmethod
from typing import List
from ..entities.dxf_entity import DXFEntity
from ..entities.classification import Classification


class IClassifier(ABC):
    """엔티티 분류 인터페이스"""

    @abstractmethod
    def classify(self, entity: DXFEntity) -> Classification:
        """
        단일 엔티티 분류

        Args:
            entity: DXF 엔티티

        Returns:
            분류 결과
        """
        pass

    @abstractmethod
    def classify_batch(self, entities: List[DXFEntity]) -> List[Classification]:
        """
        다중 엔티티 일괄 분류

        Args:
            entities: DXF 엔티티 리스트

        Returns:
            분류 결과 리스트
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        분류기 사용 가능 여부

        Returns:
            사용 가능 여부
        """
        pass
