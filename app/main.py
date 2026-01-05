"""
DXF to CSV Converter FastAPI Application

[Backward Compatibility Wrapper]
실제 구현은 src.presentation으로 이동되었습니다.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Clean Architecture: 새로운 presentation 레이어에서 import
from src.presentation.api.routes import router

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="DXF to CSV Converter API",
    description="DXF 파일을 MyGeoData.cloud 형식의 CSV로 변환하는 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 미들웨어 설정 (프론트엔드 연동용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(router, prefix="/api/v1", tags=["DXF Converter"])


# 전역 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "내부 서버 오류가 발생했습니다.",
            "error": str(exc)
        }
    )


# 시작 이벤트
@app.on_event("startup")
async def startup_event():
    logger.info("DXF to CSV Converter API 시작")


# 종료 이벤트
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("DXF to CSV Converter API 종료")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=7000,
        reload=True,
        log_level="info"
    )
