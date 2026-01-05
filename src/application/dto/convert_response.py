"""
Convert Response DTO
변환 응답 데이터 전송 객체
"""
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ConvertResponse:
    """DXF → CSV 변환 응답"""
    success: bool
    output_path: str
    statistics: Dict  # {total, lwpolyline, line, arc}
    error_message: Optional[str] = None
