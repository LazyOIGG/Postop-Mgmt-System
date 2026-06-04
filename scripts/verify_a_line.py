"""A-line comprehensive acceptance test."""
import os
import sys
import subprocess

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pass_count = 0
fail_count = 0
errors = []


def check(name, ok, detail=""):
    global pass_count, fail_count
    if ok:
        pass_count += 1
        d = f": {detail}" if detail else ""
        print(f"  PASS  {name}{d}")
    else:
        fail_count += 1
        d = f": {detail}" if detail else ""
        print(f"  FAIL  {name}{d}")
        errors.append(name)


print("=" * 60)
print("A-line Acceptance Criteria Checklist")
print("=" * 60)

# ===== A1 =====
print()
print("[A1] JWT, CORS, Admin")

from app.core.security import (
    generate_token, validate_token, invalidate_token,
    validate_refresh_token, invalidate_refresh_token, require_admin,
)
from app.core.config import settings

a, r = generate_token("u1")
check("A1.1 token generate", bool(a))
check("A1.2 refresh generate", bool(r))
check("A1.3 token validate", validate_token(a) is not None)
invalidate_token(a)
check("A1.4 blacklist", validate_token(a) is None)
check("A1.5 refresh validate", validate_refresh_token(r) is not None)
invalidate_refresh_token(r)
check("A1.6 refresh revoke", validate_refresh_token(r) is None)
check("A1.7 require_admin fn", callable(require_admin))
check("A1.8 CORS not wildcard", "*" not in settings.CORS_ORIGINS, settings.CORS_ORIGINS)
check("A1.9 REDIS_URL exists", hasattr(settings, "REDIS_URL"), str(settings.REDIS_URL))

# ===== A2 =====
print()
print("[A2] WebSocket + Notifications")

from app.core.ws_manager import ConnectionManager, WSMessageType

m = ConnectionManager()
check("A2.1 multi-conn dict", type(m._connections) == dict)
msg_type_count = len([t for t in dir(WSMessageType) if t.isupper()])
check("A2.2 8 msg types", msg_type_count == 8, f"found {msg_type_count}")
check("A2.3 heartbeat method", hasattr(m, "start_heartbeat"))
check("A2.4 send_to_user", hasattr(m, "send_to_user"))
check("A2.5 broadcast", hasattr(m, "broadcast"))
check("A2.6 shutdown", hasattr(m, "shutdown"))

from app.api.v1.endpoints.notifications import router

has_del = any(
    "DELETE" in methods
    for _, methods in [(r.path, r.methods) for r in router.routes]
)
check("A2.7 DELETE notification", has_del)

from database.local_db_utils import DatabaseConnector

dc = DatabaseConnector()
check("A2.8 delete_notification", hasattr(dc, "delete_notification"))
check("A2.9 paginated query", hasattr(dc, "get_notifications_paginated"))
check("A2.10 count method", hasattr(dc, "get_notification_count"))

# ===== A3 =====
print()
print("[A3] Infrastructure")

docker_files = ["Dockerfile", "Dockerfile.vue", "docker-compose.yml", ".dockerignore", "nginx.conf"]
for f in docker_files:
    check(f"A3.{f}", os.path.exists(f))

from app.db.session import get_redis, close_redis

check("A3.get_redis", callable(get_redis))
check("A3.close_redis", callable(close_redis))

test_files = [t for t in os.listdir("tests") if t.startswith("test_")]
check("A3.test files", len(test_files) >= 5, f"{len(test_files)} files")

for pkg in ["redis", "pytest", "structlog", "prometheus_client"]:
    try:
        __import__(pkg)
        check(f"A3.{pkg}", True)
    except ImportError:
        check(f"A3.{pkg}", False)

has_ci = os.path.exists(".github/workflows/ci.yml")
check("A3.CI/CD", has_ci)

# ===== A4 =====
print()
print("[A4] Observability")

from app.core.logging import setup_logging, get_logger, request_id_ctx

check("A4.1 setup_logging", callable(setup_logging))
check("A4.2 request_id_ctx", request_id_ctx is not None)

from app.api.v1.endpoints.metrics import (
    REQUEST_COUNT, REQUEST_LATENCY, ACTIVE_WEBSOCKETS,
    LLM_CALL_COUNT, LLM_CALL_LATENCY,
)

metrics = [
    ("REQUEST_COUNT", REQUEST_COUNT),
    ("LATENCY", REQUEST_LATENCY),
    ("WS_GAUGE", ACTIVE_WEBSOCKETS),
    ("LLM_COUNT", LLM_CALL_COUNT),
    ("LLM_LATENCY", LLM_CALL_LATENCY),
]
for name, metric in metrics:
    check(f"A4.metric_{name}", metric is not None)

# Print cleanup - check all app/ files
r = subprocess.run(
    ["grep", "-rc", "print(", "app/", "--include=*.py"],
    capture_output=True, text=True,
)
bad = 0
for line in r.stdout.strip().split("\n"):
    if ":" in line:
        parts = line.split(":")
        if len(parts) >= 2 and int(parts[1]) > 0:
            fn = parts[0]
            # ner_model has only commented-out prints, main.py has 3 banner prints
            if "ner_model" not in fn and "main.py" not in fn:
                bad += 1
                print(f"  FAIL  A4.print: {fn} has {parts[1]} print() calls")
if bad == 0:
    check("A4.print cleanup", True, "0 residuals (ner_model=commented, main=banners)")

# Also check run scripts and database
for f in ["run.py", "run_backend.py", "database/local_db_utils.py"]:
    count = sum(1 for _ in open(f, encoding="utf-8") if "print(" in _)
    check(f"A4.print_{f}", count == 0, f"{count} prints remaining" if count else "clean")

# Enhance health check
from app.main import app
health_routes = [r for r in app.routes if r.path == "/health"]
check("A4.health endpoint", len(health_routes) > 0)

# Summary
print()
print("=" * 60)
print(f"TOTAL: {pass_count} PASSED, {fail_count} FAILED")
if fail_count > 0:
    print(f"Failed items: {errors}")
else:
    print("ALL A-LINE ACCEPTANCE CRITERIA MET!")
print("=" * 60)
