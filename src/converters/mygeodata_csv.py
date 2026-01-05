"""
MyGeoData.cloud CSV Format Converter
DXF 파일을 MyGeoData.cloud와 동일한 형식의 CSV로 변환

[Backward Compatibility Wrapper]
이 모듈은 하위 호환성을 위해 유지됩니다.
실제 구현은 src.infrastructure.converters.mygeodata_csv_converter에 있습니다.
"""
from typing import Dict
from ..infrastructure.converters.mygeodata_csv_converter import (
    MyGeoDataCSVConverter as _InfraConverter
)


class MyGeoDataCSVConverter:
    """
    DXF to MyGeoData CSV Converter (하위 호환성 래퍼)

    실제 구현은 infrastructure 레이어로 이동되었습니다.
    기존 코드 호환성을 위해 클래스 메서드 인터페이스를 유지합니다.
    """

    @classmethod
    def convert(cls, dxf_path: str, csv_path: str) -> Dict:
        """
        DXF 파일을 MyGeoData CSV 형식으로 변환

        Args:
            dxf_path: 입력 DXF 파일 경로
            csv_path: 출력 CSV 파일 경로

        Returns:
            변환 통계 딕셔너리
        """
        converter = _InfraConverter()
        return converter.convert(dxf_path, csv_path)
