"""
DXF Repository Interface
DXF 파일 읽기/쓰기 인터페이스
"""
from abc import ABC, abstractmethod
from typing import List, Any
from ..entities.dxf_entity import DXFEntity


class IDXFRepository(ABC):
    """DXF 파일 접근 인터페이스"""

    @abstractmethod
    def read(self, file_path: str) -> Any:
        """
        DXF 파일 읽기

        Args:
            file_path: DXF 파일 경로

        Returns:
            DXF 문서 객체
        """
        pass

    @abstractmethod
    def write(self, doc: Any, file_path: str) -> None:
        """
        DXF 파일 쓰기

        Args:
            doc: DXF 문서 객체
            file_path: 출력 파일 경로
        """
        pass

    @abstractmethod
    def extract_entities(self, doc: Any) -> List[DXFEntity]:
        """
        DXF 문서에서 엔티티 추출

        Args:
            doc: DXF 문서 객체

        Returns:
            추출된 엔티티 리스트
        """
        pass

    @abstractmethod
    def create_layers(self, doc: Any, entities: List[DXFEntity]) -> None:
        """
        DXF 문서에 레이어 생성

        Args:
            doc: DXF 문서 객체
            entities: 엔티티 리스트
        """
        pass

    @abstractmethod
    def add_entities(self, doc: Any, entities: List[DXFEntity]) -> None:
        """
        DXF 문서에 엔티티 추가

        Args:
            doc: DXF 문서 객체
            entities: 추가할 엔티티 리스트
        """
        pass
