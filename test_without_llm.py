#!/usr/bin/env python3
"""
LLM 없이 기본 구조만 테스트
(크레딧 없이 DXF 파싱이 제대로 작동하는지 확인)
"""
import sys
sys.path.insert(0, '.')

from src.core.dxf_parser import DXFParser
from src.core.block_extractor import BlockExtractor
from src.models.layer_schema import LayerSchema, LayerCategory, LayerType
from src.models.extracted_entity import ExtractedEntity, Classification
import ezdxf
import yaml

print("=== DXF 파싱 테스트 (LLM 없이) ===\n")

# 1. 레이어 스키마 로드
print("1. 레이어 스키마 로드 중...")
with open('config/layer_categories.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

categories = {}
for cat_name, cat_data in config['categories'].items():
    types = {}
    for type_name, type_data in cat_data['types'].items():
        types[type_name] = LayerType(
            name=type_data['name'],
            output_layer=type_data['output_layer'],
            color=type_data['color'],
            typical_keywords=type_data.get('typical_keywords', [])
        )
    categories[cat_name] = LayerCategory(
        description=cat_data['description'],
        types=types
    )

schema = LayerSchema(categories=categories)
print(f"✓ {len(categories)}개 카테고리 로드 완료\n")

# 2. DXF 파일 읽기
print("2. DXF 파일 읽기 중...")
try:
    doc = ezdxf.readfile('osong-b1.dxf')
    print("✓ DXF 파일 읽기 성공\n")
except Exception as e:
    print(f"✗ DXF 파일 읽기 실패: {e}\n")
    sys.exit(1)

# 3. 블록 추출
print("3. 블록 추출 중...")
extractor = BlockExtractor(doc)
entities = extractor.extract_all_blocks(max_depth=10)
print(f"✓ {len(entities)}개 블록 추출 완료\n")

# 4. 추출된 블록 샘플 출력
print("4. 추출된 블록 샘플 (상위 10개):")
print("-" * 60)
for idx, entity in enumerate(entities[:10], 1):
    print(f"{idx}. {entity.block_name}")
    print(f"   - 타입: {entity.geometry_type}")
    print(f"   - 면적: {entity.area:.2f} m²" if entity.area else "   - 면적: N/A")
    print(f"   - 꼭짓점: {len(entity.vertices)}개")
    print()

if len(entities) > 10:
    print(f"... 외 {len(entities) - 10}개 블록\n")

# 5. 블록명 패턴 분석
print("5. 블록명 패턴 분석:")
print("-" * 60)
block_names = set(e.block_name for e in entities)
print(f"고유 블록 타입: {len(block_names)}개\n")

for name in sorted(block_names)[:20]:
    count = sum(1 for e in entities if e.block_name == name)
    print(f"  {name}: {count}개")

print("\n" + "=" * 60)
print("✅ DXF 파싱 엔진 정상 작동 확인!")
print("\nLLM 분류기만 활성화하면 바로 사용 가능합니다:")
print("  1. https://console.anthropic.com/settings/billing")
print("  2. 크레딧 충전 ($5 이상)")
print("  3. python3 dxf_ai_extractor.py osong-b1.dxf --stats")
print("=" * 60)
