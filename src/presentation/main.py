"""
FastAPI Main Application
메인 애플리케이션 진입점
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router

# FastAPI 앱 생성
app = FastAPI(
    title="DXF to CSV Converter API",
    description="DXF 파일을 MyGeoData.cloud 형식의 CSV로 변환하는 API (Clean Architecture)",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(router, prefix="/api/v1", tags=["DXF Converter"])


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "DXF to CSV Converter API",
        "version": "2.0.0",
        "architecture": "Clean Architecture",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7000)
