"""
Classification Entity
분류 결과 엔티티
"""
from dataclasses import dataclass


@dataclass
class Classification:
    """LLM 분류 결과"""
    category: str
    type: str
    confidence: float
    reasoning: str
    method: str = "llm"  # llm, rule, embedding
