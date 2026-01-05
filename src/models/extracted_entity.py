"""
Extracted Entity Models (Backward Compatibility Wrapper)

이 모듈은 하위 호환성을 위해 유지됩니다.
실제 엔티티는 src.domain.entities로 이동되었습니다.
"""
from ..domain.entities.classification import Classification
from ..domain.entities.dxf_entity import DXFEntity

# ExtractedEntity는 DXFEntity의 별칭 (하위 호환성)
ExtractedEntity = DXFEntity

__all__ = ['Classification', 'ExtractedEntity']
