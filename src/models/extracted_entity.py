"""
Extracted Entity Models
추출된 엔티티 데이터 모델
"""
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class Classification:
    """LLM 분류 결과"""
    category: str
    type: str
    confidence: float
    reasoning: str
    method: str = "llm"  # llm, rule, embedding


@dataclass
class ExtractedEntity:
    """추출된 DXF 엔티티"""
    block_name: str
    geometry_type: str  # LWPOLYLINE, CIRCLE, LINE 등
    vertices: List[Tuple[float, float]]
    area: Optional[float]
    insert_point: Tuple[float, float]
    rotation: float
    classification: Optional[Classification] = None

    @property
    def center(self) -> Tuple[float, float]:
        """중심점 계산"""
        if not self.vertices:
            return self.insert_point

        x_coords = [v[0] for v in self.vertices]
        y_coords = [v[1] for v in self.vertices]

        return (
            sum(x_coords) / len(x_coords),
            sum(y_coords) / len(y_coords)
        )

    @property
    def output_layer(self) -> str:
        """출력 레이어명"""
        if not self.classification:
            return "x-other-unclassified"

        category = self.classification.category
        type_name = self.classification.type

        # 레이어명 생성: prefix-category-type
        prefix_map = {
            'parking': 'p',
            'structure': 's',
            'circulation': 'c',
            'facility': 'f',
            'other': 'x'
        }

        prefix = prefix_map.get(category, 'x')
        return f"{prefix}-{category}-{type_name}"
