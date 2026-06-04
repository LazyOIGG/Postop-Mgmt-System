import asyncio
import time
import uuid
from datetime import datetime, timezone

import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.api import api_router
from app.api.v1.endpoints.metrics import router as metrics_router
from app.core.config import settings
from app.core.response import ApiResponse
from app.core.security import _cleanup_expired_data
from app.db.session import db_instance
from app.services.kg_service import kg_service
from app.services.ner_service import ner_service
from app.core.logging import setup_logging, get_logger, request_id_ctx

logger = get_logger(__name__)

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
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
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
# 注册 Prometheus 指标端点（独立于 API v1 前缀）
app.include_router(metrics_router, tags=["监控指标"])


# ── 日志中间件 ───────────────────────────────────────────────────

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """记录请求日志 + 注入 trace_id + Prometheus 指标"""
    trace_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
    request_id_ctx.set(trace_id)

    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000

    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2),
        trace_id=trace_id,
    )

    # Prometheus 指标
    try:
        from app.api.v1.endpoints.metrics import REQUEST_COUNT, REQUEST_LATENCY
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration_ms / 1000)
    except Exception:
        pass

    response.headers["X-Request-ID"] = trace_id
    return response


# ── 根端点 ───────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "message": "健康管理系统 API 服务运行中 (Modular Version)",
        "version": settings.VERSION,
        "status": "healthy",
        "api_docs": "/docs",
    }


# ── 增强健康检查 ─────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """增强健康检查: 检测 MySQL / Neo4j / Redis / LLM 各组件状态"""
    checks = {}

    # MySQL
    try:
        db_ok = db_instance.connection and db_instance.connection.is_connected()
    except Exception:
        db_ok = False
    checks["mysql"] = {"ok": db_ok, "status": "connected" if db_ok else "disconnected"}

    # Neo4j
    try:
        neo4j_ok = kg_service.client is not None
    except Exception:
        neo4j_ok = False
    checks["neo4j"] = {"ok": neo4j_ok, "status": "connected" if neo4j_ok else "disconnected"}

    # Redis
    try:
        from app.db.session import get_redis
        redis_client = await get_redis()
        if redis_client:
            redis_ok = await redis_client.ping()
            checks["redis"] = {"ok": redis_ok, "status": "connected" if redis_ok else "disconnected"}
        else:
            checks["redis"] = {"ok": True, "status": "not_configured"}
    except Exception as e:
        checks["redis"] = {"ok": False, "status": f"error: {str(e)[:80]}"}

    # LLM
    llm_configured = bool(settings.DEEPSEEK_API_KEY and settings.DEEPSEEK_API_KEY not in (
        "your-deepseek-api-key", "YOUR_DEEPSEEK_API_KEY", "sk-your-key-here"))
    checks["llm"] = {"ok": llm_configured, "status": "configured" if llm_configured else "not_configured"}

    # 聚合状态
    critical = ["mysql", "neo4j"]
    all_critical_ok = all(checks[c]["ok"] for c in critical)
    status = "healthy" if all_critical_ok else "degraded"

    result = {
        "status": status,
        "service": "postop-mgmt-api",
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
    if status == "degraded":
        return JSONResponse(content=result, status_code=503)
    return result


# ── 启动 / 关闭 ──────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    # 初始化结构化日志
    setup_logging("DEBUG" if settings.DEBUG else "INFO")

    logger.info("startup_begin", project=settings.PROJECT_NAME)
    print("=" * 50)
    print(f"{settings.PROJECT_NAME} 启动中...")

    # Validate SECRET_KEY
    if settings.SECRET_KEY in ("YOUR_SECRET_KEY", "", "changeme"):
        raise RuntimeError("SECRET_KEY 未配置或使用了占位符，请在 .env 中设置真实密钥")

    # 尝试连接数据库
    if db_instance.connect():
        logger.info("database_connected")
    else:
        logger.warning("database_connection_failed")

    logger.info("api_docs", url="http://localhost:8000/docs")
    asyncio.create_task(_cleanup_expired_data())

    # Start WebSocket heartbeat
    from app.core.ws_manager import ws_manager
    ws_manager.start_heartbeat()

    logger.info("startup_complete")
    print("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("shutdown_begin")
    db_instance.close()
    from app.db.session import close_redis
    await close_redis()
    from app.core.ws_manager import ws_manager
    await ws_manager.shutdown()
    logger.info("shutdown_complete")


# ── 全局异常处理 ──────────────────────────────────────────────────


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
