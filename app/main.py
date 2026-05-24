import asyncio
import logging
from datetime import datetime

import os

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.response import ApiResponse
from app.core.security import _cleanup_expired_data
from app.db.session import db_instance
from app.services.kg_service import kg_service
from app.services.ner_service import ner_service

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="全周期健康管理系统，集成知识图谱与 DeepSeek 大模型",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
static_dir = os.path.join(os.path.dirname(__file__), '..', 'static')
os.makedirs(os.path.join(static_dir, 'uploads'), exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 包含 API 路由
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {
        "message": "健康管理系统 API 服务运行中 (Modular Version)",
        "version": settings.VERSION,
        "status": "healthy",
        "api_docs": "/docs",
    }


@app.get("/health")
async def health_check():
    db_status = (
        "connected"
        if db_instance.connection and db_instance.connection.is_connected()
        else "disconnected"
    )
    neo4j_status = "connected" if kg_service.client else "disconnected"

    return {
        "status": "healthy",
        "service": "postop-mgmt-api",
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        "neo4j": neo4j_status,
    }


@app.on_event("startup")
async def startup_event():
    print("=" * 50)
    print(f"{settings.PROJECT_NAME} 启动中...")

    # Validate SECRET_KEY
    if settings.SECRET_KEY in ("YOUR_SECRET_KEY", "", "changeme"):
        raise RuntimeError("SECRET_KEY 未配置或使用了占位符，请在 .env 中设置真实密钥")

    # 尝试连接数据库
    if db_instance.connect():
        print("数据库连接成功")
    else:
        print("数据库连接失败")

    print(f"API 文档地址: http://localhost:8000/docs")
    asyncio.create_task(_cleanup_expired_data())
    print("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    db_instance.close()
    print("数据库连接已关闭")


# ── 全局异常处理 ──────────────────────────────────────────────


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse.fail(message=str(exc.detail), code=exc.status_code),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content=ApiResponse.fail(message="请求参数验证失败", code=422, data=exc.errors()),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.exception(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content=ApiResponse.fail(message="服务器内部错误", code=500),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
