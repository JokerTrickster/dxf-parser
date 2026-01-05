"""
Convert Request DTO
변환 요청 데이터 전송 객체
"""
from dataclasses import dataclass


@dataclass
class ConvertRequest:
    """DXF → CSV 변환 요청"""
    dxf_path: str
    csv_path: str
    validate: bool = True  # 입력 파일 검증 여부
