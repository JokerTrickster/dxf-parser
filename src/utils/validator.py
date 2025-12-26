"""
Input Validation Utilities
입력 검증 유틸리티
"""
import os
from typing import Tuple
import ezdxf


class DXFValidator:
    """DXF 파일 검증기"""

    @staticmethod
    def validate_file(dxf_path: str) -> Tuple[bool, str]:
        """
        DXF 파일 유효성 검증

        Args:
            dxf_path: DXF 파일 경로

        Returns:
            (유효 여부, 메시지)
        """
        # 파일 존재 확인
        if not os.path.exists(dxf_path):
            return False, f"파일이 존재하지 않습니다: {dxf_path}"

        # 확장자 확인
        if not dxf_path.lower().endswith('.dxf'):
            return False, "DXF 파일이 아닙니다"

        # 파일 크기 확인
        file_size = os.path.getsize(dxf_path)
        if file_size == 0:
            return False, "빈 파일입니다"

        # DXF 구조 검증
        try:
            doc = ezdxf.readfile(dxf_path)

            # 모델 스페이스 확인
            if not hasattr(doc, 'modelspace'):
                return False, "MODEL_SPACE가 없습니다"

            # 블록 정의 확인
            if not hasattr(doc, 'blocks'):
                return False, "블록 정의가 없습니다"

            return True, "유효한 DXF 파일"

        except ezdxf.DXFStructureError as e:
            return False, f"DXF 구조 오류: {str(e)}"
        except Exception as e:
            return False, f"파일 읽기 실패: {str(e)}"

    @staticmethod
    def validate_api_key(api_key: str) -> Tuple[bool, str]:
        """
        API 키 검증

        Args:
            api_key: Anthropic API 키

        Returns:
            (유효 여부, 메시지)
        """
        if not api_key:
            return False, "API 키가 설정되지 않았습니다"

        if not api_key.startswith('sk-'):
            return False, "유효하지 않은 API 키 형식입니다"

        return True, "유효한 API 키"
