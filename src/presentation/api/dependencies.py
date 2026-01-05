"""
Dependency Injection Container
FastAPI 의존성 주입 컨테이너
"""
from ...application.use_cases.convert_dxf_to_csv import ConvertDXFToCSVUseCase
from ...infrastructure.converters.mygeodata_csv_converter import MyGeoDataCSVConverter


def get_convert_use_case() -> ConvertDXFToCSVUseCase:
    """
    DXF → CSV 변환 유즈케이스 인스턴스 생성

    Returns:
        ConvertDXFToCSVUseCase 인스턴스
    """
    converter = MyGeoDataCSVConverter()
    return ConvertDXFToCSVUseCase(converter)
