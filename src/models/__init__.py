"""
Models Module (Backward Compatibility Wrapper)

이 모듈은 하위 호환성을 위해 유지됩니다.
새 코드는 src.domain.entities를 직접 사용하세요.
"""
from ..domain.entities.dxf_entity import DXFEntity
from ..domain.entities.classification import Classification
from ..domain.entities.layer_info import LayerType, LayerCategory, LayerSchema

# ExtractedEntity는 DXFEntity의 별칭 (하위 호환성)
ExtractedEntity = DXFEntity

__all__ = [
    'DXFEntity',
    'ExtractedEntity',  # 별칭
    'Classification',
    'LayerType',
    'LayerCategory',
    'LayerSchema',
]
