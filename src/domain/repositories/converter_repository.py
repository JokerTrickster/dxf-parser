"""
Converter Repository Interface
변환기 인터페이스
"""
from abc import ABC, abstractmethod
from typing import Dict


class IConverter(ABC):
    """파일 변환 인터페이스"""

    @abstractmethod
    def convert(self, input_path: str, output_path: str) -> Dict:
        """
        파일 변환

        Args:
            input_path: 입력 파일 경로
            output_path: 출력 파일 경로

        Returns:
            변환 통계 딕셔너리
        """
        pass

    @abstractmethod
    def validate_input(self, file_path: str) -> bool:
        """
        입력 파일 유효성 검증

        Args:
            file_path: 파일 경로

        Returns:
            유효성 여부
        """
        pass
