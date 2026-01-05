"""
Models Module (Backward Compatibility Wrapper)

t ¨È@ X 8X1D t  À)Èä.
ä Ôðð” src.domain.entities\ tÙÈµÈä.
"""
from ..domain.entities.dxf_entity import DXFEntity
from ..domain.entities.classification import Classification
from ..domain.entities.layer_info import LayerType, LayerCategory, LayerSchema

# ExtractedEntity” DXFEntityX Äm (X 8X1)
ExtractedEntity = DXFEntity

__all__ = [
    'DXFEntity',
    'ExtractedEntity',  # Äm
    'Classification',
    'LayerType',
    'LayerCategory',
    'LayerSchema',
]
