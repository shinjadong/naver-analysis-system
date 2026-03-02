"""
CareOn Traffic Engine API
캠페인 관리 및 트래픽 실행 API 서버

실행 방법:
    python -m src.api.main
    또는
    uvicorn src.api.main:app --reload --port 8000
"""

import os
import logging

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv()
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .routes import campaigns, traffic, status

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# ========== 인증 미들웨어 ==========

async def verify_api_key(x_api_key: str = Header(None)):
    """
    API 키 검증

    헤더: X-API-Key
    """
    expected_key = os.getenv("FASTAPI_API_KEY")

    # 개발 환경에서 API 키 없으면 패스
    if not expected_key:
        logger.warning("FASTAPI_API_KEY not set, skipping authentication")
        return None

    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="X-API-Key header required"
        )

    if x_api_key != expected_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    return x_api_key


# ========== 앱 초기화 ==========

@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행"""
    # 시작 시
    logger.info("=" * 50)
    logger.info("CareOn Traffic Engine API Starting...")
    logger.info(f"Port: {os.getenv('FASTAPI_PORT', 8000)}")
    logger.info("=" * 50)

    yield

    # 종료 시
    logger.info("Traffic Engine API Shutting down...")


app = FastAPI(
    title="CareOn Traffic Engine API",
    description="""
캠페인 트래픽 부스팅 엔진 API

## 기능

- **캠페인 관리**: 캠페인 조회, 시작, 정지, 상태 확인
- **트래픽 실행**: 단일/배치 트래픽 실행
- **상태 모니터링**: 디바이스, 페르소나, 엔진 상태 조회

## 인증

모든 엔드포인트는 `X-API-Key` 헤더가 필요합니다.
    """,
    version="1.0.0",
    lifespan=lifespan,
)


# ========== CORS 설정 ==========

# 허용된 오리진 (kt-cctv-landing)
ALLOWED_ORIGINS = [
    "https://kt-cctv.vercel.app",
    "https://kt-cctv-landing.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 라우터 등록 ==========

# 캠페인 관리 API
app.include_router(
    campaigns.router,
    prefix="/campaigns",
    tags=["campaigns"],
    dependencies=[Depends(verify_api_key)]
)

# 트래픽 실행 API
app.include_router(
    traffic.router,
    prefix="/traffic",
    tags=["traffic"],
    dependencies=[Depends(verify_api_key)]
)

# 상태 조회 API
app.include_router(
    status.router,
    prefix="/status",
    tags=["status"],
    dependencies=[Depends(verify_api_key)]
)


# ========== 기본 엔드포인트 ==========

@app.get("/", tags=["root"])
async def root():
    """API 정보"""
    return {
        "service": "CareOn Traffic Engine",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", tags=["health"])
async def health_check():
    """
    헬스 체크

    인증 없이 접근 가능
    """
    return {
        "status": "ok",
        "service": "traffic-engine",
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }


# ========== 메인 실행 ==========

if __name__ == "__main__":
    port = int(os.getenv("FASTAPI_PORT", 8000))

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
