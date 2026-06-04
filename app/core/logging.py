"""结构化日志配置 — 基于 structlog + 标准 logging"""

import logging
from contextvars import ContextVar

import structlog

# 请求级上下文变量
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
user_ctx: ContextVar[str] = ContextVar("user", default="anonymous")


def setup_logging(log_level: str = "INFO") -> None:
    """配置 structlog + 标准 logging 集成。

    开发环境 (log_level=DEBUG): 彩色 ConsoleRenderer
    生产环境 (log_level=INFO): JSONRenderer
    """

    timestamper = structlog.processors.TimeStamper(fmt="iso")

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if log_level.upper() == "DEBUG":
        # 开发环境: 彩色控制台输出
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        # 生产环境: JSON 输出
        renderer = structlog.processors.JSONRenderer(ensure_ascii=False)

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 同时配置标准 logging（兼容未迁移的代码）
    logging.basicConfig(
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=getattr(logging, log_level.upper(), logging.INFO),
        force=True,
    )


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """获取结构化日志记录器"""
    return structlog.get_logger(name or __name__)
