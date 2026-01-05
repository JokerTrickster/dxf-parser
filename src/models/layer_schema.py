"""
Layer Schema Models (Backward Compatibility Wrapper)

이 모듈은 하위 호환성을 위해 유지됩니다.
실제 엔티티는 src.domain.entities로 이동되었습니다.
"""
from ..domain.entities.layer_info import LayerType, LayerCategory, LayerSchema

__all__ = ['LayerType', 'LayerCategory', 'LayerSchema']
