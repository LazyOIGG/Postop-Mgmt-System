"""Prometheus 监控指标"""

from fastapi import APIRouter, Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()

# ── HTTP 指标 ──
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ── WebSocket 指标 ──
ACTIVE_WEBSOCKETS = Gauge(
    "websocket_connections_active",
    "Active WebSocket connections",
)

# ── LLM 指标 ──
LLM_CALL_COUNT = Counter(
    "llm_calls_total",
    "Total LLM API calls",
    ["model", "status"],
)
LLM_CALL_LATENCY = Histogram(
    "llm_call_duration_seconds",
    "LLM call latency in seconds",
    ["model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0],
)
LLM_TOKEN_COUNT = Counter(
    "llm_tokens_total",
    "Total LLM tokens consumed",
    ["model", "type"],  # type: prompt / completion
)


@router.get("/metrics")
async def metrics():
    """Prometheus 指标端点"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
