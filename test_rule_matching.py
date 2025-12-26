#!/usr/bin/env python3
"""
규칙 매칭 테스트
"""
import sys
sys.path.insert(0, '.')

from src.ai.rule_based_classifier import RuleBasedClassifier

# 분류기 초기화 (캐시 없이)
classifier = RuleBasedClassifier(enable_cache=False)

# 테스트 블록명
test_blocks = [
    "지하1층평면도$0$PARK_일반",
    "지하1층평면도$0$PARK_확장",
    "지하1층평면도$0$PARK_장애인",
    "지하1층평면도$0$PARK_경차",
    "지하1층평면도$0$Park-환경친화",
    "지하1층평면도$0$PARK-EC",
    "지하1층평면도$0$가족배려주차(확장형)",
    "지하1층평면도$0$교통약자우선",
    "지하1층평면도$0$core_B1F계단_260",
    "지하1층평면도$0$FSD-1100",
]

print("=== 규칙 매칭 테스트 ===\n")

for block_name in test_blocks:
    result = classifier.classify(
        block_name,
        context={'area': 12.5, 'vertex_count': 4}
    )

    print(f"블록: {block_name.split('$')[-1]}")
    print(f"  → {result.category}/{result.type}")
    print(f"  → 확신도: {result.confidence:.2f}")
    print(f"  → 근거: {result.reasoning}")
    print()
