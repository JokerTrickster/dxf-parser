"""
Extract Parking Spaces Use Case
주차면 추출 유즈케이스
"""
from typing import List
from ...domain.entities.dxf_entity import DXFEntity
from ...domain.repositories.dxf_repository import IDXFRepository
from ...domain.repositories.classifier_repository import IClassifier


class ExtractParkingSpacesUseCase:
    """주차면 추출 유즈케이스"""

    def __init__(
        self,
        dxf_repository: IDXFRepository,
        classifier: IClassifier
    ):
        """
        Args:
            dxf_repository: DXF 저장소 인터페이스 구현체
            classifier: 분류기 인터페이스 구현체
        """
        self.dxf_repository = dxf_repository
        self.classifier = classifier

    def execute(self, input_path: str, output_path: str) -> int:
        """
        주차면 추출 및 DXF 파일로 저장

        Args:
            input_path: 입력 DXF 파일 경로
            output_path: 출력 DXF 파일 경로

        Returns:
            추출된 주차면 수

        Raises:
            Exception: 파일 읽기/쓰기 실패 시
        """
        # DXF 파일 읽기
        doc = self.dxf_repository.read(input_path)

        # 엔티티 추출
        entities = self.dxf_repository.extract_entities(doc)

        # 분류 (분류기가 사용 가능한 경우)
        if self.classifier.is_available():
            classifications = self.classifier.classify_batch(entities)
            for entity, classification in zip(entities, classifications):
                entity.classification = classification

        # 주차면만 필터링
        parking_entities = [
            e for e in entities
            if e.classification and e.classification.category == 'parking'
        ]

        # 새 DXF 문서 생성
        output_doc = self.dxf_repository.read(input_path)  # 템플릿으로 사용

        # 레이어 생성
        self.dxf_repository.create_layers(output_doc, parking_entities)

        # 엔티티 추가
        self.dxf_repository.add_entities(output_doc, parking_entities)

        # DXF 파일 저장
        self.dxf_repository.write(output_doc, output_path)

        return len(parking_entities)
