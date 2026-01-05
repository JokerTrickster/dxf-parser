"""
API Routes
"""
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from typing import Dict

from ..services.converter import DXFConverterService

logger = logging.getLogger(__name__)
router = APIRouter()
converter_service = DXFConverterService()


@router.get("/")
async def root() -> Dict[str, str]:
    """서버 상태 확인"""
    return {
        "service": "DXF to CSV Converter",
        "version": "1.0.0",
        "status": "running"
    }


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """헬스 체크"""
    return {"status": "healthy"}


@router.post("/convert")
async def convert_dxf_to_csv(
    file: UploadFile = File(..., description="DXF 파일")
) -> FileResponse:
    """
    DXF 파일을 CSV로 변환

    - **file**: DXF 파일 (.dxf 확장자)

    Returns:
        CSV 파일 다운로드
    """
    # 파일 확장자 검증
    if not file.filename.lower().endswith('.dxf'):
        raise HTTPException(
            status_code=400,
            detail="DXF 파일만 업로드 가능합니다. (.dxf 확장자 필요)"
        )

    logger.info(f"변환 요청: {file.filename}")

    try:
        # 파일 읽기
        content = await file.read()

        # 변환
        csv_path, csv_filename, stats = await converter_service.convert_file(
            content, file.filename
        )

        logger.info(f"변환 통계: {stats}")

        # CSV 파일 응답
        return FileResponse(
            path=csv_path,
            media_type='text/csv',
            filename=csv_filename,
            background=lambda: converter_service.cleanup_csv(csv_path)
        )

    except Exception as e:
        logger.error(f"변환 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"DXF 변환 중 오류 발생: {str(e)}"
        )


@router.post("/convert/info")
async def get_conversion_info(
    file: UploadFile = File(..., description="DXF 파일")
) -> Dict:
    """
    DXF 파일 정보 조회 (변환 전 미리보기)

    - **file**: DXF 파일

    Returns:
        DXF 파일 정보 (엔티티 수, 레이어 등)
    """
    import ezdxf
    import tempfile
    import os

    if not file.filename.lower().endswith('.dxf'):
        raise HTTPException(
            status_code=400,
            detail="DXF 파일만 업로드 가능합니다."
        )

    temp_path = None
    try:
        # 임시 파일로 저장
        content = await file.read()
        temp_path = os.path.join(tempfile.gettempdir(), f"info_{file.filename}")
        with open(temp_path, 'wb') as f:
            f.write(content)

        # DXF 분석
        doc = ezdxf.readfile(temp_path)
        msp = doc.modelspace()

        # 엔티티 타입별 카운트
        from collections import Counter
        entity_types = Counter()
        layers = Counter()

        for entity in msp:
            entity_types[entity.dxftype()] += 1
            if hasattr(entity.dxf, 'layer'):
                layers[entity.dxf.layer] += 1

        return {
            "filename": file.filename,
            "total_entities": len(list(msp)),
            "entity_types": dict(entity_types),
            "layers": dict(layers),
            "dxf_version": doc.dxfversion
        }

    except Exception as e:
        logger.error(f"파일 분석 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"DXF 파일 분석 실패: {str(e)}"
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
