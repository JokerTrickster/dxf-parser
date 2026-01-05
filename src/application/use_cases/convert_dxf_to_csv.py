"""
Convert DXF to CSV Use Case
DXF 파일을 CSV로 변환하는 유즈케이스
"""
from typing import Dict
from ...domain.repositories.converter_repository import IConverter


class ConvertDXFToCSVUseCase:
    """DXF → CSV 변환 유즈케이스"""

    def __init__(self, converter: IConverter):
        """
        Args:
            converter: CSV 변환기 인터페이스 구현체
        """
        self.converter = converter

    def execute(self, dxf_path: str, csv_path: str) -> Dict:
        """
        DXF 파일을 CSV로 변환

        Args:
            dxf_path: 입력 DXF 파일 경로
            csv_path: 출력 CSV 파일 경로

        Returns:
            변환 통계 (total, lwpolyline, line, arc)

        Raises:
            ValueError: 입력 파일이 유효하지 않은 경우
            Exception: 변환 실패 시
        """
        # 입력 파일 검증
        if not self.converter.validate_input(dxf_path):
            raise ValueError(f"Invalid DXF file: {dxf_path}")

        # 변환 실행
        stats = self.converter.convert(dxf_path, csv_path)

        return stats
