"""
Ollama 로컬 LLM 기반 레이어 분류기 (완전 무료)

설치:
  brew install ollama
  ollama pull llama3.2:3b

사용:
  python3 dxf_ai_extractor.py input.dxf --use-ollama
"""
import json
import logging
from typing import Optional, Dict
import requests
import yaml

from ..models.extracted_entity import Classification
from .cache_manager import CacheManager


class OllamaLayerClassifier:
    """Ollama 로컬 LLM을 사용한 레이어 분류기 (완전 무료)"""

    def __init__(
        self,
        model: str = "llama3.2:3b",
        prompt_config_path: str = "config/llm_prompts.yaml",
        enable_cache: bool = True,
        cache_file: str = ".layer_classification_cache.json",
        ollama_host: str = "http://localhost:11434"
    ):
        """
        Args:
            model: Ollama 모델명 (llama3.2:3b, llama3.1:8b, qwen2.5:7b)
            prompt_config_path: 프롬프트 설정 파일 경로
            enable_cache: 캐싱 활성화 여부
            cache_file: 캐시 파일 경로
            ollama_host: Ollama 서버 주소
        """
        self.model = model
        self.ollama_host = ollama_host
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

        # Ollama 연결 확인
        self._check_ollama_connection()

    def _check_ollama_connection(self):
        """Ollama 서버 연결 확인"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=2)
            if response.status_code == 200:
                models = [m['name'] for m in response.json().get('models', [])]

                if self.model not in models:
                    self.logger.warning(
                        f"모델 '{self.model}'이 설치되지 않았습니다.\n"
                        f"설치된 모델: {models}\n"
                        f"다음 명령어로 설치하세요: ollama pull {self.model}"
                    )
                else:
                    self.logger.info(f"✓ Ollama 연결 성공 (모델: {self.model})")
            else:
                raise ConnectionError("Ollama 서버 응답 오류")

        except requests.exceptions.ConnectionError:
            self.logger.error(
                "Ollama 서버에 연결할 수 없습니다.\n"
                "다음을 확인하세요:\n"
                "  1. Ollama 설치: brew install ollama\n"
                "  2. Ollama 실행: ollama serve\n"
                "  3. 모델 다운로드: ollama pull llama3.2:3b"
            )
            raise

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

        # Ollama API 호출
        try:
            result = self._call_ollama_api(block_name, context or {})
            self.stats['api_calls'] += 1

            classification = Classification(
                category=result['category'],
                type=result['type'],
                confidence=result['confidence'],
                reasoning=result['reasoning'],
                method='ollama'
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

    def _call_ollama_api(
        self,
        block_name: str,
        context: Dict
    ) -> dict:
        """
        Ollama API 호출

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

        full_prompt = f"{self.prompts['system_prompt']}\n\n{user_prompt}"

        self.logger.debug(f"Ollama API 호출: {block_name}")

        # API 호출
        response = requests.post(
            f"{self.ollama_host}/api/generate",
            json={
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "format": "json"  # JSON 응답 강제
            },
            timeout=60  # 로컬이라 느릴 수 있음
        )

        if response.status_code != 200:
            raise RuntimeError(f"Ollama API 오류: {response.text}")

        # 응답 파싱
        response_data = response.json()
        response_text = response_data.get('response', '{}')

        # JSON 파싱
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 텍스트에서 추출 시도
            self.logger.warning(f"JSON 파싱 실패, 텍스트 분석: {response_text}")
            result = self._extract_from_text(response_text, block_name)

        # 필수 필드 검증 및 기본값 설정
        required_fields = {
            'category': 'other',
            'type': 'unclassified',
            'confidence': 0.5,
            'reasoning': '자동 분류'
        }

        for field, default in required_fields.items():
            if field not in result:
                result[field] = default

        return result

    def _extract_from_text(self, text: str, block_name: str) -> dict:
        """텍스트에서 분류 정보 추출 (폴백)"""
        # 간단한 키워드 매칭
        text_lower = text.lower() + block_name.lower()

        if any(kw in text_lower for kw in ['주차', 'park', 'parking']):
            return {
                'category': 'parking',
                'type': 'basic',
                'confidence': 0.7,
                'reasoning': '주차 키워드 감지'
            }
        elif any(kw in text_lower for kw in ['기둥', 'column']):
            return {
                'category': 'structure',
                'type': 'column',
                'confidence': 0.7,
                'reasoning': '기둥 키워드 감지'
            }
        elif any(kw in text_lower for kw in ['벽', 'wall']):
            return {
                'category': 'structure',
                'type': 'wall',
                'confidence': 0.7,
                'reasoning': '벽 키워드 감지'
            }

        return {
            'category': 'other',
            'type': 'unclassified',
            'confidence': 0.3,
            'reasoning': '분류 불가'
        }

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
