import os
import sys
import subprocess
import time
import socket
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


def check_port(port):
    """检查端口是否被占用"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    except:
        return False


def kill_process_on_port(port):
    """终止占用指定端口的进程"""
    try:
        cmd = f"netstat -ano | findstr :{port}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = parts[4]
                    try:
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                        logger.info("port_process_killed", port=port, pid=pid)
                    except:
                        pass
    except:
        pass


sys.path.append(str(Path(__file__).parent))


def start_backend():
    """启动 FastAPI 后端"""
    port = 8000
    logger.info("checking_port", port=port)
    if check_port(port):
        logger.info("port_occupied_cleaning", port=port)
        kill_process_on_port(port)
        time.sleep(2)
    logger.info("starting_backend")
    logger.info("api_docs", url=f"http://localhost:{port}/docs")
    logger.info("api_base", url=f"http://localhost:{port}/api/v1/")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(port)],
        env=os.environ.copy()
    )


if __name__ == "__main__":
    proc = None
    try:
        proc = start_backend()
        logger.info("backend_started", msg="按 Ctrl+C 停止")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("interrupt_received", msg="正在关闭服务...")
    finally:
        if proc:
            proc.terminate()
        logger.info("backend_stopped")
