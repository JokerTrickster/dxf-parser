#!/usr/bin/env python3
"""
DXF AI-Enhanced Extractor
LLM 기반 다중 레이어 추출기

Usage:
    python dxf_ai_extractor.py input.dxf -o output.dxf --csv data.csv
"""
import argparse
import os
import sys
import yaml
from dotenv import load_dotenv

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.dxf_parser import DXFParser
from src.core.block_extractor import BlockExtractor
from src.ai.llm_classifier import LLMLayerClassifier
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
    # 환경 변수 로드
    load_dotenv()

    # 인자 파싱
    parser = argparse.ArgumentParser(
        description='LLM 기반 DXF 다중 레이어 추출기'
    )
    parser.add_argument('input', help='입력 DXF 파일')
    parser.add_argument('-o', '--output', help='출력 DXF 파일')
    parser.add_argument('--csv', help='CSV 출력 파일')
    parser.add_argument('--no-labels', action='store_true', help='ID 라벨 제외')
    parser.add_argument('--max-depth', type=int, default=10, help='최대 블록 탐색 깊이')
    parser.add_argument('--no-cache', action='store_true', help='캐싱 비활성화')
    parser.add_argument('--clear-cache', action='store_true', help='캐시 초기화')
    parser.add_argument('--stats', action='store_true', help='통계 출력')
    parser.add_argument('--log-level', default='INFO', help='로그 레벨 (DEBUG/INFO/WARNING/ERROR)')

    args = parser.parse_args()

    # 로거 설정
    logger = setup_logger(level=args.log_level)

    # API 키 확인
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        logger.error("ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")
        logger.error(".env 파일을 생성하거나 환경 변수를 설정하세요.")
        return 1

    # API 키 검증
    is_valid, msg = DXFValidator.validate_api_key(api_key)
    if not is_valid:
        logger.error(f"API 키 검증 실패: {msg}")
        return 1

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

    # LLM 분류기 초기화
    logger.info("LLM 분류기 초기화 중...")
    classifier = LLMLayerClassifier(
        api_key=api_key,
        model=os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022'),
        prompt_config_path='config/llm_prompts.yaml',
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

    # LLM 분류 실행
    logger.info("LLM 분류 시작...")
    for idx, entity in enumerate(entities, start=1):
        logger.info(f"분류 중... ({idx}/{len(entities)}) {entity.block_name}")

        # 주변 블록 정보 수집 (간단한 구현)
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

        logger.debug(
            f"  → {classification.category}/{classification.type} "
            f"(확신도: {classification.confidence:.2f})"
        )

    # 캐시 저장
    if not args.no_cache:
        classifier.save_cache()

    # 통계 출력
    if args.stats:
        stats = classifier.get_stats()
        logger.info("\n=== 분류 통계 ===")
        logger.info(f"총 요청: {stats['total_requests']}")
        logger.info(f"캐시 히트: {stats['cache_hits']}")
        logger.info(f"API 호출: {stats['api_calls']}")
        logger.info(f"캐시 히트율: {stats['cache_hit_rate']:.1%}")
        logger.info(f"오류: {stats['errors']}")

        if 'cache_categories' in stats:
            logger.info("\n카테고리별 분포:")
            for cat, count in stats['cache_categories'].items():
                logger.info(f"  {cat}: {count}")

    # DXF 파일 생성
    logger.info("DXF 파일 생성 중...")
    dxf_parser.create_output_dxf(
        entities,
        args.output,
        add_labels=not args.no_labels
    )

    # CSV 내보내기
    logger.info("CSV 파일 생성 중...")
    dxf_parser.export_to_csv(entities, args.csv)

    logger.info("\n=== 완료 ===")
    logger.info(f"출력 DXF: {args.output}")
    logger.info(f"출력 CSV: {args.csv}")
    logger.info(f"추출된 레이어: {len(entities)}개")

    return 0


if __name__ == '__main__':
    sys.exit(main())
