"""
Classification Cache Manager
분류 결과 캐싱 관리
"""
import json
import os
from typing import Optional, Dict
from datetime import datetime
import logging


class CacheManager:
    """LLM 분류 결과 캐시 관리"""

    def __init__(self, cache_file: str = ".layer_classification_cache.json"):
        """
        Args:
            cache_file: 캐시 파일 경로
        """
        self.cache_file = cache_file
        self.cache: Dict[str, dict] = {}
        self.logger = logging.getLogger(__name__)
        self._load_cache()

    def _load_cache(self):
        """캐시 파일 로드"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                self.logger.info(f"캐시 로드 완료: {len(self.cache)}개 항목")
            except Exception as e:
                self.logger.warning(f"캐시 로드 실패: {e}")
                self.cache = {}
        else:
            self.cache = {}

    def save_cache(self):
        """캐시 파일 저장"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            self.logger.info(f"캐시 저장 완료: {len(self.cache)}개 항목")
        except Exception as e:
            self.logger.error(f"캐시 저장 실패: {e}")

    def get(self, block_name: str) -> Optional[dict]:
        """
        캐시에서 분류 결과 조회

        Args:
            block_name: 블록 이름

        Returns:
            분류 결과 또는 None
        """
        return self.cache.get(block_name)

    def set(self, block_name: str, classification: dict):
        """
        분류 결과를 캐시에 저장

        Args:
            block_name: 블록 이름
            classification: 분류 결과
        """
        self.cache[block_name] = {
            **classification,
            'cached_at': datetime.now().isoformat()
        }

    def clear(self):
        """캐시 초기화"""
        self.cache = {}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        self.logger.info("캐시 초기화 완료")

    def get_stats(self) -> dict:
        """캐시 통계"""
        if not self.cache:
            return {'total': 0}

        categories = {}
        for item in self.cache.values():
            category = item.get('category', 'unknown')
            categories[category] = categories.get(category, 0) + 1

        return {
            'total': len(self.cache),
            'categories': categories
        }
