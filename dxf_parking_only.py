#!/usr/bin/env python3
"""
DXF 주차장 도면 전용 추출기

주차장 도면에 필요한 레이어만 추출:
- 주차면 (일반, 장애인, 전기차, 경차, 확장, 여성)
- 기둥 (주차 동선에 중요)
- 계단 (비상구)
- 엘리베이터

불필요한 레이어 제거:
- 화장실, 수납공간, 방 등 시설물
- 벽, 보 등 상세 구조물
- CAD 메타데이터
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


# 주차장 도면에 필요한 카테고리만 필터링
ALLOWED_CATEGORIES = {'parking', 'structure', 'circulation'}
ALLOWED_TYPES = {
    'parking': {'basic', 'disabled', 'electric', 'women', 'compact', 'large'},
    'structure': {'column'},  # 기둥만 포함 (벽, 보 제외)
    'circulation': {'stairs', 'elevator', 'entrance', 'exit'}  # 계단, 엘리베이터, 출입구만
}


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


def filter_parking_entities(entities, logger):
    """주차장 도면에 필요한 엔티티만 필터링"""
    filtered = []
    stats = {'total': len(entities), 'kept': 0, 'removed': 0}

    for entity in entities:
        classification = entity.classification

        # 허용된 카테고리인지 확인
        if classification.category not in ALLOWED_CATEGORIES:
            stats['removed'] += 1
            continue

        # 허용된 타입인지 확인
        if classification.category in ALLOWED_TYPES:
            if classification.type not in ALLOWED_TYPES[classification.category]:
                stats['removed'] += 1
                continue

        filtered.append(entity)
        stats['kept'] += 1

    logger.info(f"필터링 결과: {stats['kept']}개 유지, {stats['removed']}개 제거")
    return filtered


def main():
    # 인자 파싱
    parser = argparse.ArgumentParser(
        description='DXF 주차장 도면 전용 추출기 (주차면 + 기둥 + 동선만)'
    )
    parser.add_argument('input', help='입력 DXF 파일')
    parser.add_argument('-o', '--output', help='출력 DXF 파일')
    parser.add_argument('--no-labels', action='store_true', help='ID 라벨 제외')
    parser.add_argument('--max-depth', type=int, default=10, help='최대 블록 탐색 깊이')
    parser.add_argument('--no-cache', action='store_true', help='캐싱 비활성화')
    parser.add_argument('--log-level', default='INFO', help='로그 레벨')

    args = parser.parse_args()

    # 로거 설정
    logger = setup_logger(level=args.log_level)

    logger.info("=== DXF 주차장 도면 전용 추출기 ===")
    logger.info("추출 대상: 주차면 + 기둥 + 계단/엘리베이터\n")

    # DXF 파일 검증
    is_valid, msg = DXFValidator.validate_file(args.input)
    if not is_valid:
        logger.error(f"DXF 파일 검증 실패: {msg}")
        return 1

    logger.info(f"DXF 파일 검증 성공: {msg}")

    # 출력 파일명 생성
    if not args.output:
        base_name = os.path.splitext(args.input)[0]
        args.output = f"{base_name}_B1_converted.dxf"

    # 레이어 스키마 로드
    logger.info("레이어 스키마 로드 중...")
    schema = load_layer_schema('config/layer_categories.yaml')

    # 규칙 기반 분류기 초기화
    logger.info("규칙 기반 분류기 초기화 중...")
    classifier = RuleBasedClassifier(
        enable_cache=not args.no_cache
    )

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

    for idx, entity in enumerate(entities, start=1):
        if idx % 100 == 0 or idx == len(entities):
            logger.info(f"진행: {idx}/{len(entities)} ({idx*100//len(entities)}%)")

        # 분류
        classification = classifier.classify(
            block_name=entity.block_name,
            context={
                'geometry_type': entity.geometry_type,
                'area': entity.area,
                'vertex_count': len(entity.vertices)
            }
        )

        entity.classification = classification

    logger.info("=" * 60)

    # 캐시 저장
    if not args.no_cache:
        classifier.save_cache()

    # 주차장 관련 엔티티만 필터링
    logger.info("\n주차장 관련 엔티티만 필터링 중...")
    filtered_entities = filter_parking_entities(entities, logger)

    # 필터링 후 통계
    logger.info("\n=== 필터링 후 통계 ===")
    category_stats = {}
    for entity in filtered_entities:
        cat = entity.classification.category
        typ = entity.classification.type
        key = f"{cat}/{typ}"
        category_stats[key] = category_stats.get(key, 0) + 1

    logger.info(f"총 유지: {len(filtered_entities)}개")
    logger.info("\n카테고리별 분포:")
    for key, count in sorted(category_stats.items()):
        percentage = count * 100 / len(filtered_entities)
        logger.info(f"  {key}: {count}개 ({percentage:.1f}%)")

    # DXF 파일만 생성 (CSV는 사용자가 별도 도구로 변환)
    logger.info("\nDXF 파일 생성 중...")
    dxf_parser.create_output_dxf(
        filtered_entities,
        args.output,
        add_labels=not args.no_labels
    )

    logger.info("\n" + "=" * 60)
    logger.info("=== 완료 ===")
    logger.info("=" * 60)
    logger.info(f"출력 DXF: {args.output}")
    logger.info(f"총 추출: {len(filtered_entities)}개 (원본: {len(entities)}개)")
    logger.info(f"제거: {len(entities) - len(filtered_entities)}개")
    logger.info("\n다음 단계: DXF 파일을 당신의 도구로 CSV 변환")
    logger.info("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
