"""
Classify Entities Use Case
엔티티 분류 유즈케이스
"""
from typing import List
from ...domain.entities.dxf_entity import DXFEntity
from ...domain.repositories.classifier_repository import IClassifier


class ClassifyEntitiesUseCase:
    """엔티티 분류 유즈케이스"""

    def __init__(self, classifier: IClassifier):
        """
        Args:
            classifier: 분류기 인터페이스 구현체
        """
        self.classifier = classifier

    def execute(self, entities: List[DXFEntity]) -> List[DXFEntity]:
        """
        엔티티 리스트 분류

        Args:
            entities: 분류할 DXF 엔티티 리스트

        Returns:
            분류 결과가 포함된 엔티티 리스트

        Raises:
            RuntimeError: 분류기를 사용할 수 없는 경우
        """
        # 분류기 사용 가능 여부 확인
        if not self.classifier.is_available():
            raise RuntimeError("Classifier is not available")

        # 일괄 분류
        classifications = self.classifier.classify_batch(entities)

        # 분류 결과를 엔티티에 할당
        for entity, classification in zip(entities, classifications):
            entity.classification = classification

        return entities
