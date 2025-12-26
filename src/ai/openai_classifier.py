"""
OpenAI GPT-4 기반 레이어 분류기 (Claude 대안)
무료 크레딧: 신규 가입 시 $5
"""
import json
import logging
from typing import Optional, Dict
import openai
import yaml

from ..models.extracted_entity import Classification
from .cache_manager import CacheManager


class OpenAILayerClassifier:
    """OpenAI GPT-4를 사용한 레이어 분류기 (Claude 대안)"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",  # 저렴한 모델 (Claude Haiku와 유사)
        prompt_config_path: str = "config/llm_prompts.yaml",
        enable_cache: bool = True,
        cache_file: str = ".layer_classification_cache.json"
    ):
        """
        Args:
            api_key: OpenAI API 키
            model: GPT 모델명 (gpt-4o-mini, gpt-4o, gpt-4-turbo)
            prompt_config_path: 프롬프트 설정 파일 경로
            enable_cache: 캐싱 활성화 여부
            cache_file: 캐시 파일 경로
        """
        openai.api_key = api_key
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

        # OpenAI API 호출
        try:
            result = self._call_openai_api(block_name, context or {})
            self.stats['api_calls'] += 1

            classification = Classification(
                category=result['category'],
                type=result['type'],
                confidence=result['confidence'],
                reasoning=result['reasoning'],
                method='openai'
            )

            # 캐시 저장
            if self.enable_cache and self.cache:
                self.cache.set(block_name, result)

            return classification

        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"분류 실패 ({block_name}): {e}")

            return Classification(
                category='other',
                type='unclassified',
                confidence=0.0,
                reasoning=f"분류 실패: {str(e)}",
                method='error'
            )

    def _call_openai_api(
        self,
        block_name: str,
        context: Dict
    ) -> dict:
        """
        OpenAI API 호출

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

        self.logger.debug(f"OpenAI API 호출: {block_name}")

        # API 호출
        response = openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.prompts['system_prompt']},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"}  # JSON 모드 강제
        )

        # 응답 파싱
        response_text = response.choices[0].message.content
        result = json.loads(response_text)

        # 필수 필드 검증
        required_fields = ['category', 'type', 'confidence', 'reasoning']
        for field in required_fields:
            if field not in result:
                raise ValueError(f"응답에 필수 필드 누락: {field}")

        return result

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
