"""
LLM-based Layer Classifier
LLM 기반 레이어 분류기
"""
import json
import logging
from typing import Optional, Dict, List
import anthropic
import yaml

from ..models.extracted_entity import Classification
from .cache_manager import CacheManager


class LLMLayerClassifier:
    """Claude API를 사용한 레이어 분류기"""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        prompt_config_path: str = "config/llm_prompts.yaml",
        enable_cache: bool = True,
        cache_file: str = ".layer_classification_cache.json"
    ):
        """
        Args:
            api_key: Anthropic API 키
            model: Claude 모델명
            prompt_config_path: 프롬프트 설정 파일 경로
            enable_cache: 캐싱 활성화 여부
            cache_file: 캐시 파일 경로
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.logger = logging.getLogger(__name__)

        # 프롬프트 로드
        self.prompts = self._load_prompts(prompt_config_path)

        # 캐시 관리자
        self.enable_cache = enable_cache
        self.cache = CacheManager(cache_file) if enable_cache else None

        # 통계
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'errors': 0
        }

    def _load_prompts(self, config_path: str) -> dict:
        """프롬프트 설정 로드"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.warning(f"프롬프트 설정 로드 실패: {e}, 기본값 사용")
            return {
                'system_prompt': "CAD 도면 블록을 분류하는 전문가입니다.",
                'classification_prompt': "블록을 분류해주세요: {block_name}"
            }

    def classify(
        self,
        block_name: str,
        context: Optional[Dict] = None
    ) -> Classification:
        """
        단일 블록 분류

        Args:
            block_name: 블록 이름
            context: 추가 문맥 정보
                - geometry_type: 엔티티 타입
                - area: 면적
                - vertex_count: 꼭짓점 수
                - nearby_blocks: 주변 블록 리스트

        Returns:
            Classification 객체
        """
        self.stats['total_requests'] += 1

        # 캐시 확인
        if self.enable_cache and self.cache:
            cached = self.cache.get(block_name)
            if cached:
                self.stats['cache_hits'] += 1
                self.logger.debug(f"캐시 히트: {block_name}")
                return Classification(
                    category=cached['category'],
                    type=cached['type'],
                    confidence=cached['confidence'],
                    reasoning=cached['reasoning'],
                    method='cached'
                )

        # LLM API 호출
        try:
            result = self._call_llm_api(block_name, context or {})
            self.stats['api_calls'] += 1

            classification = Classification(
                category=result['category'],
                type=result['type'],
                confidence=result['confidence'],
                reasoning=result['reasoning'],
                method='llm'
            )

            # 캐시 저장
            if self.enable_cache and self.cache:
                self.cache.set(block_name, result)

            return classification

        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"분류 실패 ({block_name}): {e}")

            # 폴백: 미분류로 반환
            return Classification(
                category='other',
                type='unclassified',
                confidence=0.0,
                reasoning=f"분류 실패: {str(e)}",
                method='error'
            )

    def _call_llm_api(
        self,
        block_name: str,
        context: Dict
    ) -> dict:
        """
        Claude API 호출

        Args:
            block_name: 블록 이름
            context: 문맥 정보

        Returns:
            분류 결과 딕셔너리
        """
        # 프롬프트 생성
        user_prompt = self.prompts['classification_prompt'].format(
            block_name=block_name,
            geometry_type=context.get('geometry_type', 'N/A'),
            area=f"{context.get('area', 0):.2f}" if context.get('area') else 'N/A',
            vertex_count=context.get('vertex_count', 'N/A'),
            nearby_blocks=', '.join(context.get('nearby_blocks', [])[:5]) or 'N/A'
        )

        self.logger.debug(f"LLM API 호출: {block_name}")

        # API 호출
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            system=self.prompts['system_prompt'],
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        # 응답 파싱
        response_text = response.content[0].text

        # JSON 추출 (마크다운 코드 블록 처리)
        if '```json' in response_text:
            json_start = response_text.find('```json') + 7
            json_end = response_text.find('```', json_start)
            response_text = response_text[json_start:json_end].strip()
        elif '```' in response_text:
            json_start = response_text.find('```') + 3
            json_end = response_text.find('```', json_start)
            response_text = response_text[json_start:json_end].strip()

        result = json.loads(response_text)

        # 필수 필드 검증
        required_fields = ['category', 'type', 'confidence', 'reasoning']
        for field in required_fields:
            if field not in result:
                raise ValueError(f"응답에 필수 필드 누락: {field}")

        return result

    def batch_classify(
        self,
        blocks: List[Dict]
    ) -> List[Classification]:
        """
        여러 블록 일괄 분류 (비용 절감)

        Args:
            blocks: 블록 정보 리스트
                [{'name': 'PARK_일반', 'context': {...}}, ...]

        Returns:
            Classification 리스트
        """
        # 캐시되지 않은 블록만 필터링
        uncached_blocks = []
        results = []

        for block in blocks:
            block_name = block['name']
            if self.enable_cache and self.cache:
                cached = self.cache.get(block_name)
                if cached:
                    self.stats['cache_hits'] += 1
                    results.append(Classification(
                        category=cached['category'],
                        type=cached['type'],
                        confidence=cached['confidence'],
                        reasoning=cached['reasoning'],
                        method='cached'
                    ))
                    continue

            uncached_blocks.append(block)

        # 캐시되지 않은 블록만 API 호출
        if uncached_blocks:
            # 개별 호출 (batch API는 향후 구현 가능)
            for block in uncached_blocks:
                classification = self.classify(
                    block['name'],
                    block.get('context')
                )
                results.append(classification)

        return results

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
        else:
            stats['cache_hit_rate'] = 0.0

        return stats
