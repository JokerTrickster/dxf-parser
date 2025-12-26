"""
Layer Schema Models
레이어 스키마 데이터 모델
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class LayerType:
    """세부 레이어 타입"""
    name: str
    output_layer: str
    color: int
    typical_keywords: List[str]


@dataclass
class LayerCategory:
    """레이어 카테고리"""
    description: str
    types: dict[str, LayerType]


@dataclass
class LayerSchema:
    """전체 레이어 스키마"""
    categories: dict[str, LayerCategory]

    def get_output_layer(self, category: str, type_name: str) -> Optional[str]:
        """카테고리와 타입으로 출력 레이어명 조회"""
        if category not in self.categories:
            return None

        category_obj = self.categories[category]
        if type_name not in category_obj.types:
            return None

        return category_obj.types[type_name].output_layer

    def get_color(self, category: str, type_name: str) -> int:
        """카테고리와 타입으로 색상 조회"""
        if category not in self.categories:
            return 7  # Default white

        category_obj = self.categories[category]
        if type_name not in category_obj.types:
            return 7

        return category_obj.types[type_name].color
