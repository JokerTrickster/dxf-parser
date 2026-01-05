"""
API Schemas
Pydantic 스키마 정의
"""
from pydantic import BaseModel
from typing import Dict, Optional


class ConvertResponse(BaseModel):
    """DXF → CSV 변환 응답"""
    success: bool
    filename: str
    statistics: Dict
    message: Optional[str] = None


class DXFInfoResponse(BaseModel):
    """DXF 파일 정보 응답"""
    filename: str
    total_entities: int
    entity_types: Dict[str, int]
    layers: Dict[str, int]
    dxf_version: str


class ErrorResponse(BaseModel):
    """에러 응답"""
    detail: str
