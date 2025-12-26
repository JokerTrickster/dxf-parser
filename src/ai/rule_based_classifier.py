"""
Rule-based Layer Classifier (LLM 불필요)
키워드 매칭 + 기하학 분석으로 레이어 자동 분류

정확도: ~85% (LLM 없이)
비용: $0
속도: 즉시
"""
import logging
from typing import Optional, Dict, List, Tuple
import re

from ..models.extracted_entity import Classification
from .cache_manager import CacheManager


class RuleBasedClassifier:
    """규칙 기반 레이어 분류기 (LLM 불필요)"""

    def __init__(
        self,
        enable_cache: bool = True,
        cache_file: str = ".layer_classification_cache.json"
    ):
        self.logger = logging.getLogger(__name__)

        # 캐시 관리자
        self.enable_cache = enable_cache
        self.cache = CacheManager(cache_file) if enable_cache else None

        # 통계
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'rule_matches': 0,
            'geometry_matches': 0,
            'unclassified': 0
        }

        # 키워드 규칙 정의 (우선순위 순)
        self.rules = self._build_rules()

    def _build_rules(self) -> List[Dict]:
        """분류 규칙 구축 (한국 CAD 도면 최적화)"""
        return [
            # ===== 소방/안전 설비 (circulation - 출구/비상구) =====
            {
                'category': 'circulation',
                'type': 'exit',
                'confidence': 0.95,
                'keywords': [
                    'FSD', 'FSD-\\d+', 'FIRE.?SAFETY', '소방', '방화', '비상'
                ],
                'area_range': (1, 100000000)  # Very wide range for fire doors
            },

            # ===== 계단 (circulation - stairs) =====
            {
                'category': 'circulation',
                'type': 'stairs',
                'confidence': 0.98,
                'keywords': [
                    '계단', 'STAIR', 'STEP', 'STA', 'core.*계단',
                    '층계', 'B[0-9]+F계단', 'STA_'
                ],
                'area_range': (5, 100000000)  # 매우 넓은 범위 (단위 이슈)
            },

            # ===== 주차 공간 (parking) =====
            # 면적 단위: mm² (도면 단위)
            {
                'category': 'parking',
                'type': 'disabled',
                'confidence': 0.95,
                'keywords': [
                    '장애인', 'DISABLED', 'HANDICAP', 'HANDICAPPED',
                    '배리어프리', 'BARRIER.?FREE', 'ACCESSIBLE',
                    '장애', 'DISABLE'
                ],
                'area_range': (15000000, 20000000)  # 15-20 m² (mm² 단위)
            },
            {
                'category': 'parking',
                'type': 'electric',
                'confidence': 0.95,
                'keywords': [
                    '전기차', 'ELECTRIC', 'EV', 'E.?V',
                    '환경친화', 'ECO', 'CHARGE', '충전',
                    'PARK.?EC', 'EC.?PARK'
                ],
                'area_range': (10000000, 15000000)  # 10-15 m²
            },
            {
                'category': 'parking',
                'type': 'women',
                'confidence': 0.95,
                'keywords': [
                    '여성', 'WOMEN', 'WOMAN', 'FEMALE',
                    '가족', 'FAMILY', '배려',
                    '교통약자', 'PRIORITY'
                ],
                'area_range': (10000000, 15000000)  # 10-15 m²
            },
            {
                'category': 'parking',
                'type': 'compact',
                'confidence': 0.95,
                'keywords': [
                    '경차', 'COMPACT', 'SMALL', 'MINI',
                    '소형', 'LIGHT'
                ],
                'area_range': (7000000, 10000000)  # 7-10 m²
            },
            {
                'category': 'parking',
                'type': 'large',
                'confidence': 0.90,
                'keywords': [
                    '확장', 'LARGE', 'EXTENDED', 'EXPAND',
                    'SUV', '대형', 'BIG'
                ],
                'area_range': (13000000, 18000000)  # 13-18 m²
            },
            {
                'category': 'parking',
                'type': 'basic',
                'confidence': 0.90,
                'keywords': [
                    '일반', 'NORMAL', 'STANDARD', 'REGULAR',
                    'BASIC', 'STD', 'PARK', '주차',
                    'PARKING', 'CAR.?SPACE'
                ],
                'area_range': (10000000, 15000000)  # 10-15 m²
            },

            # ===== 구조물 (structure) =====
            {
                'category': 'structure',
                'type': 'column',
                'confidence': 0.95,
                'keywords': [
                    '기둥', 'COLUMN', 'COL', 'PILLAR',
                    'POST', 'C\\d+', '^C-', 'PIER',
                    '\\d+x\\d+',  # 500x700 같은 치수
                    '^\\d{3,4}$'  # 500, 700 같은 숫자만
                ],
                'area_range': (100000, 1000000000),  # 매우 넓은 범위 (mm²)
                'vertex_range': (4, 100)  # 사각/원형
            },
            {
                'category': 'structure',
                'type': 'wall',
                'confidence': 0.95,
                'keywords': [
                    '벽', 'WALL', 'PARTITION', 'BARRIER',
                    '외벽', 'EXTERIOR', '내벽', 'INTERIOR',
                    'FENCE', '칸막이'
                ],
                'area_range': (0.1, 100)
            },
            {
                'category': 'structure',
                'type': 'beam',
                'confidence': 0.90,
                'keywords': [
                    '보', 'BEAM', 'GIRDER', 'JOIST',
                    'B\\d+', '^B-'
                ],
                'area_range': (0.5, 10)
            },

            # ===== 동선 (circulation) =====
            {
                'category': 'circulation',
                'type': 'entrance',
                'confidence': 0.95,
                'keywords': [
                    '출입구', 'ENTRANCE', 'ENTRY', 'ACCESS',
                    'GATE', '입구', '게이트',
                    'IN', 'INGRESS', '자동문', 'AUTO.?DOOR',
                    '접이문', 'FOLDING', '슬라이딩', 'SLIDING'
                ],
                'area_range': (10000, 50000000)
            },
            {
                'category': 'circulation',
                'type': 'exit',
                'confidence': 0.95,
                'keywords': [
                    '출구', 'EXIT', 'EGRESS', 'OUT',
                    '비상구', 'EMERGENCY', 'ESCAPE',
                    'SSD', 'SFD'  # Safety/Smoke Door
                ],
                'area_range': (10000, 50000000)
            },
            {
                'category': 'circulation',
                'type': 'ramp',
                'confidence': 0.95,
                'keywords': [
                    '경사로', 'RAMP', 'SLOPE', 'INCLINE',
                    'GRADIENT', '램프'
                ],
                'area_range': (10, 100)
            },
            {
                'category': 'circulation',
                'type': 'stairs',
                'confidence': 0.95,
                'keywords': [
                    '계단', 'STAIRS', 'STAIR', 'STEP',
                    'STAIRWAY', 'STAIRCASE'
                ],
                'area_range': (5, 30)
            },
            {
                'category': 'circulation',
                'type': 'elevator',
                'confidence': 0.95,
                'keywords': [
                    '엘리베이터', 'ELEVATOR', 'LIFT', 'EV',
                    '승강기', 'HOIST', 'E.?L'
                ],
                'area_range': (3, 10)
            },

            # ===== 시설 (facility) =====
            {
                'category': 'facility',
                'type': 'restroom',
                'confidence': 0.95,
                'keywords': [
                    '화장실', 'RESTROOM', 'TOILET', 'WC',
                    '변기', '세면대', 'SINK', '소변기',
                    'URIN', '샤워', 'SHOWER', '욕실',
                    'WASH', 'BASIN', 'LAVATORY'
                ],
                'area_range': (1000, 50000000)
            },
            {
                'category': 'facility',
                'type': 'storage',
                'confidence': 0.90,
                'keywords': [
                    '신발장', 'LOCKER', 'CABINET', 'SHOE',
                    '수납', 'STORAGE', '보관', '창고'
                ],
                'area_range': (100000, 20000000)
            },
            {
                'category': 'facility',
                'type': 'mechanical',
                'confidence': 0.90,
                'keywords': [
                    '기계실', 'MECHANICAL', 'MACHINE', 'MECH',
                    '설비실', 'EQUIPMENT', 'UTILITY',
                    'M/R', 'MR', '제연'
                ],
                'area_range': (1000000, 50000000)
            },
            {
                'category': 'facility',
                'type': 'electrical',
                'confidence': 0.90,
                'keywords': [
                    '전기실', 'ELECTRICAL', 'ELECTRIC', 'ELEC',
                    'POWER', 'E/R', 'ER', '배전'
                ],
                'area_range': (1000000, 50000000)
            },
            {
                'category': 'facility',
                'type': 'recreation',
                'confidence': 0.85,
                'keywords': [
                    '골프', 'GOLF', '운동', 'GYM', 'FITNESS',
                    '휴게', '레저', 'RECREATION'
                ],
                'area_range': (5000000, 100000000)
            },
            {
                'category': 'facility',
                'type': 'room',
                'confidence': 0.70,
                'keywords': [
                    '실', 'ROOM', 'SPACE', 'AREA',
                    'ZONE', 'RM', 'B\\d{3}', 'B-\\d{3}'  # B105, B-108 같은 방번호
                ],
                'area_range': (100000, 100000000)  # Wider range for rooms
            }
        ]

    def classify(
        self,
        block_name: str,
        context: Optional[Dict] = None
    ) -> Classification:
        """
        블록 분류

        Args:
            block_name: 블록 이름
            context: 기하학 정보 (area, vertex_count 등)

        Returns:
            Classification 객체
        """
        self.stats['total_requests'] += 1

        # 캐시 확인
        if self.enable_cache and self.cache:
            cached = self.cache.get(block_name)
            if cached:
                self.stats['cache_hits'] += 1
                return Classification(
                    category=cached['category'],
                    type=cached['type'],
                    confidence=cached['confidence'],
                    reasoning=cached['reasoning'],
                    method='cached'
                )

        # 규칙 기반 분류
        result = self._classify_by_rules(block_name, context or {})

        # 캐시 저장
        if self.enable_cache and self.cache:
            self.cache.set(block_name, {
                'category': result.category,
                'type': result.type,
                'confidence': result.confidence,
                'reasoning': result.reasoning
            })

        return result

    def _classify_by_rules(
        self,
        block_name: str,
        context: Dict
    ) -> Classification:
        """규칙 기반 분류 수행"""

        best_match = None
        best_confidence = 0.0

        # 모든 규칙을 검사하여 가장 높은 확신도 찾기
        for rule in self.rules:
            match_score = self._match_keywords(block_name, rule['keywords'])

            if match_score > 0:
                # 기하학 검증 (선택적)
                geo_score = self._match_geometry(context, rule)

                # 최종 확신도 계산
                final_confidence = rule['confidence'] * match_score * geo_score

                # 더 좋은 매칭 발견
                if final_confidence > best_confidence:
                    best_confidence = final_confidence

                    reasoning = f"키워드 매칭: {match_score:.0%}"
                    if geo_score < 1.0:
                        reasoning += f", 기하학 검증: {geo_score:.0%}"

                    best_match = Classification(
                        category=rule['category'],
                        type=rule['type'],
                        confidence=final_confidence,
                        reasoning=reasoning,
                        method='rule-based'
                    )

        # 가장 좋은 매칭 반환 (확신도 0.5 이상)
        if best_match and best_confidence > 0.5:
            self.stats['rule_matches'] += 1
            return best_match

        # 매칭 실패 → 미분류
        self.stats['unclassified'] += 1
        return Classification(
            category='other',
            type='unclassified',
            confidence=0.3,
            reasoning='규칙 매칭 실패',
            method='rule-based'
        )

    def _match_keywords(
        self,
        block_name: str,
        keywords: List[str]
    ) -> float:
        """
        키워드 매칭 점수 계산

        Returns:
            0.0 ~ 1.0 (매칭 점수)
        """
        # 블록명에서 실제 블록 부분만 추출 ($ 구분자로 split)
        # 예: "지하1층평면도$0$PARK_일반" → "PARK_일반"
        block_parts = block_name.split('$')

        for keyword in keywords:
            # 정규표현식 매칭
            pattern = re.compile(keyword, re.IGNORECASE)

            # 전체 블록명에서 매칭
            if pattern.search(block_name):
                return 1.0

            # 각 파트에서 매칭 (더 정확한 매칭)
            for part in block_parts:
                if pattern.search(part):
                    return 1.0

        return 0.0

    def _match_geometry(
        self,
        context: Dict,
        rule: Dict
    ) -> float:
        """
        기하학 조건 검증

        Returns:
            0.0 ~ 1.0 (검증 점수)
        """
        score = 1.0

        # 면적 검증
        if 'area_range' in rule and context.get('area'):
            area = context['area']
            min_area, max_area = rule['area_range']

            if min_area <= area <= max_area:
                score *= 1.0  # 완전 일치
            elif area < min_area * 0.5 or area > max_area * 2:
                score *= 0.3  # 크게 벗어남
            else:
                score *= 0.7  # 약간 벗어남

        # 꼭짓점 수 검증 (기둥 판별 등)
        if 'vertex_range' in rule and context.get('vertex_count'):
            vertex_count = context['vertex_count']
            min_v, max_v = rule['vertex_range']

            if min_v <= vertex_count <= max_v:
                score *= 1.0
            else:
                score *= 0.5

        return score

    def save_cache(self):
        """캐시 저장"""
        if self.cache:
            self.cache.save_cache()

    def get_stats(self) -> dict:
        """통계 조회"""
        stats = {**self.stats}

        if self.cache:
            cache_stats = self.cache.get_stats()
            stats['cache_size'] = cache_stats['total']
            stats['cache_categories'] = cache_stats.get('categories', {})

        if stats['total_requests'] > 0:
            stats['cache_hit_rate'] = stats['cache_hits'] / stats['total_requests']
            stats['classification_rate'] = (
                stats['rule_matches'] / stats['total_requests']
            )
        else:
            stats['cache_hit_rate'] = 0.0
            stats['classification_rate'] = 0.0

        return stats
