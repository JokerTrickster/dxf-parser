"""
DXF to CSV Conversion Service
"""
import os
import tempfile
import logging
from pathlib import Path
from typing import Tuple, Dict

# Clean Architecture: infrastructure 레이어 변환기 사용
from src.infrastructure.converters.mygeodata_csv_converter import MyGeoDataCSVConverter

logger = logging.getLogger(__name__)


class DXFConverterService:
    """DXF to CSV 변환 서비스"""

    @staticmethod
    async def convert_file(dxf_content: bytes, filename: str) -> Tuple[str, str, Dict]:
        """
        DXF 파일을 CSV로 변환

        Args:
            dxf_content: DXF 파일 바이너리 내용
            filename: 원본 파일명

        Returns:
            Tuple[csv_path, csv_filename, stats]: CSV 파일 경로, 파일명, 변환 통계

        Raises:
            Exception: 변환 실패 시
        """
        temp_dir = tempfile.gettempdir()

        # 임시 DXF 파일 저장
        dxf_path = os.path.join(temp_dir, f"input_{filename}")
        with open(dxf_path, 'wb') as f:
            f.write(dxf_content)

        logger.info(f"DXF 파일 저장 완료: {dxf_path}")

        # CSV 출력 경로 생성
        csv_filename = filename.replace('.dxf', '.csv')
        csv_path = os.path.join(temp_dir, f"output_{csv_filename}")

        try:
            # 변환 실행
            logger.info(f"변환 시작: {dxf_path} -> {csv_path}")
            converter = MyGeoDataCSVConverter()
            stats = converter.convert(dxf_path, csv_path)
            logger.info(f"변환 완료: {csv_path} (엔티티 {stats['total']}개)")

            return csv_path, csv_filename, stats

        except Exception as e:
            logger.error(f"변환 실패: {e}")
            # 임시 파일 정리
            if os.path.exists(dxf_path):
                os.remove(dxf_path)
            raise

        finally:
            # DXF 임시 파일 삭제
            if os.path.exists(dxf_path):
                os.remove(dxf_path)

    @staticmethod
    def cleanup_csv(csv_path: str):
        """CSV 임시 파일 정리"""
        try:
            if os.path.exists(csv_path):
                os.remove(csv_path)
                logger.info(f"임시 파일 정리: {csv_path}")
        except Exception as e:
            logger.warning(f"임시 파일 정리 실패: {e}")
