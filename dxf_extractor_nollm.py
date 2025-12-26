#!/usr/bin/env python3
"""
DXF Multi-Layer Extractor (LLM 불필요 버전)

규칙 기반 자동 분류 시스템
- 비용: $0
- 정확도: ~85%
- 속도: 즉시

Usage:
    python3 dxf_extractor_nollm.py input.dxf -o output.dxf --csv data.csv
"""
import argparse
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.dxf_parser import DXFParser
from src.core.block_extractor import BlockExtractor
from src.ai.rule_based_classifier import RuleBasedClassifier
from src.models.layer_schema import LayerSchema, LayerCategory, LayerType
from src.utils.logger import setup_logger
from src.utils.validator import DXFValidator


def load_layer_schema(config_path: str) -> LayerSchema:
    """레이어 스키마 로드"""
    with open(config_path, 'r', encoding='utf-8') as f:
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

    return LayerSchema(categories=categories)


def main():
    # 인자 파싱
    parser = argparse.ArgumentParser(
        description='DXF 다중 레이어 추출기 (LLM 불필요, 규칙 기반)'
    )
    parser.add_argument('input', help='입력 DXF 파일')
    parser.add_argument('-o', '--output', help='출력 DXF 파일')
    parser.add_argument('--csv', help='CSV 출력 파일')
    parser.add_argument('--no-labels', action='store_true', help='ID 라벨 제외')
    parser.add_argument('--max-depth', type=int, default=10, help='최대 블록 탐색 깊이')
    parser.add_argument('--no-cache', action='store_true', help='캐싱 비활성화')
    parser.add_argument('--clear-cache', action='store_true', help='캐시 초기화')
    parser.add_argument('--stats', action='store_true', help='통계 출력')
    parser.add_argument('--log-level', default='INFO', help='로그 레벨')
    parser.add_argument('--show-unclassified', action='store_true', help='미분류 블록 표시')

    args = parser.parse_args()

    # 로거 설정
    logger = setup_logger(level=args.log_level)

    logger.info("=== DXF 다중 레이어 추출기 (규칙 기반) ===")
    logger.info("비용: $0 | LLM 불필요 | 즉시 실행\n")

    # DXF 파일 검증
    is_valid, msg = DXFValidator.validate_file(args.input)
    if not is_valid:
        logger.error(f"DXF 파일 검증 실패: {msg}")
        return 1

    logger.info(f"DXF 파일 검증 성공: {msg}")

    # 출력 파일명 생성
    if not args.output:
        base_name = os.path.splitext(args.input)[0]
        args.output = f"{base_name}_converted.dxf"

    if not args.csv:
        base_name = os.path.splitext(args.input)[0]
        args.csv = f"{base_name}_layers.csv"

    # 레이어 스키마 로드
    logger.info("레이어 스키마 로드 중...")
    schema = load_layer_schema('config/layer_categories.yaml')

    # 규칙 기반 분류기 초기화
    logger.info("규칙 기반 분류기 초기화 중...")
    classifier = RuleBasedClassifier(
        enable_cache=not args.no_cache
    )

    # 캐시 초기화 옵션
    if args.clear_cache and classifier.cache:
        classifier.cache.clear()
        logger.info("캐시 초기화 완료")

    # DXF 파서 초기화
    dxf_parser = DXFParser(schema)

    # DXF 파일 읽기
    logger.info("DXF 파일 읽기 중...")
    doc = dxf_parser.read(args.input)

    # 블록 추출
    logger.info("블록 추출 중...")
    extractor = BlockExtractor(doc)
    entities = extractor.extract_all_blocks(max_depth=args.max_depth)

    logger.info(f"추출된 블록: {len(entities)}개")

    if not entities:
        logger.warning("추출된 블록이 없습니다.")
        return 1

    # 규칙 기반 분류 실행
    logger.info("\n규칙 기반 분류 시작...")
    logger.info("=" * 60)

    unclassified_blocks = []
    classified_by_category = {}

    for idx, entity in enumerate(entities, start=1):
        if idx % 100 == 0 or idx == len(entities):
            logger.info(f"진행: {idx}/{len(entities)} ({idx*100//len(entities)}%)")

        # 주변 블록 정보 수집
        nearby_blocks = [
            e.block_name for e in entities
            if e != entity and e.block_name != entity.block_name
        ][:5]

        # 분류
        classification = classifier.classify(
            block_name=entity.block_name,
            context={
                'geometry_type': entity.geometry_type,
                'area': entity.area,
                'vertex_count': len(entity.vertices),
                'nearby_blocks': nearby_blocks
            }
        )

        entity.classification = classification

        # 통계 수집
        category = classification.category
        if category not in classified_by_category:
            classified_by_category[category] = 0
        classified_by_category[category] += 1

        # 미분류 블록 수집
        if classification.category == 'other':
            unclassified_blocks.append((entity.block_name, entity.area))

        # 상세 로그 (DEBUG)
        logger.debug(
            f"  {entity.block_name} → "
            f"{classification.category}/{classification.type} "
            f"(확신도: {classification.confidence:.2f})"
        )

    logger.info("=" * 60)

    # 캐시 저장
    if not args.no_cache:
        classifier.save_cache()

    # 통계 출력
    logger.info("\n=== 분류 통계 ===")
    stats = classifier.get_stats()
    logger.info(f"총 블록: {stats['total_requests']}")
    logger.info(f"캐시 히트: {stats['cache_hits']} ({stats['cache_hit_rate']:.1%})")
    logger.info(f"규칙 매칭: {stats['rule_matches']}")
    logger.info(f"미분류: {stats['unclassified']}")
    logger.info(f"분류율: {stats['classification_rate']:.1%}")

    logger.info("\n=== 카테고리별 분포 ===")
    for category, count in sorted(classified_by_category.items()):
        percentage = count * 100 / len(entities)
        logger.info(f"  {category}: {count}개 ({percentage:.1f}%)")

    # 미분류 블록 표시
    if args.show_unclassified and unclassified_blocks:
        logger.info("\n=== 미분류 블록 (상위 20개) ===")
        # 고유한 블록명만 추출
        unique_unclassified = {}
        for block_name, area in unclassified_blocks:
            if block_name not in unique_unclassified:
                unique_unclassified[block_name] = area

        for idx, (block_name, area) in enumerate(
            list(unique_unclassified.items())[:20], 1
        ):
            area_str = f"{area:.2f}m²" if area else "N/A"
            logger.info(f"  {idx}. {block_name} (면적: {area_str})")

        if len(unique_unclassified) > 20:
            logger.info(f"  ... 외 {len(unique_unclassified) - 20}개")

    # DXF 파일 생성
    logger.info("\nDXF 파일 생성 중...")
    dxf_parser.create_output_dxf(
        entities,
        args.output,
        add_labels=not args.no_labels
    )

    # CSV 내보내기
    logger.info("CSV 파일 생성 중...")
    dxf_parser.export_to_csv(entities, args.csv)

    logger.info("\n" + "=" * 60)
    logger.info("=== 완료 ===")
    logger.info("=" * 60)
    logger.info(f"출력 DXF: {args.output}")
    logger.info(f"출력 CSV: {args.csv}")
    logger.info(f"총 추출: {len(entities)}개")
    logger.info(f"분류 성공: {stats['rule_matches']}개 ({stats['classification_rate']:.1%})")
    logger.info(f"미분류: {stats['unclassified']}개")
    logger.info("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
