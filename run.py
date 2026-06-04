import uvicorn
import os
import sys
import subprocess
import time
import webbrowser
import socket
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


# 检查端口是否被占用
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


# 终止占用端口的进程
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


# 添加根目录到路径
sys.path.append(str(Path(__file__).parent))


def start_fastapi():
    """启动 FastAPI 后端"""
    port = 8000
    logger.info("checking_port", port=port)
    if check_port(port):
        logger.info("port_occupied_cleaning", port=port)
        kill_process_on_port(port)
        time.sleep(2)
    logger.info("starting_fastapi")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        env=os.environ.copy()
    )


def start_streamlit():
    """启动 Streamlit 前端"""
    port = 8501
    logger.info("checking_port", port=port)
    if check_port(port):
        logger.info("port_occupied_cleaning", port=port)
        kill_process_on_port(port)
        time.sleep(2)
    logger.info("starting_streamlit")
    time.sleep(5)

    url = "http://localhost:8501"
    process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "streamlit_app.py", "--server.port", "8501", "--server.headless", "true"],
        env=os.environ.copy()
    )

    logger.info("streamlit_ready", url=url)
    webbrowser.open(url)
    return process


def start_doctor_streamlit():
    """启动医生端 Streamlit"""
    port = 8502
    logger.info("checking_port", port=port)
    if check_port(port):
        logger.info("port_occupied_cleaning", port=port)
        kill_process_on_port(port)
        time.sleep(2)
    logger.info("starting_doctor_streamlit")

    url = "http://localhost:8502"
    process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "streamlit_doctor_app.py", "--server.port", "8502", "--server.headless", "true"],
        env=os.environ.copy()
    )

    logger.info("doctor_streamlit_ready", url=url)
    return process


if __name__ == "__main__":
    f_proc = None; s_proc = None; d_proc = None
    try:
        f_proc = start_fastapi()
        s_proc = start_streamlit()
        d_proc = start_doctor_streamlit()
        while True: time.sleep(1)
    except KeyboardInterrupt:
        logger.info("interrupt_received", msg="正在关闭服务...")
    finally:
        if s_proc: s_proc.terminate()
        if d_proc: d_proc.terminate()
        if f_proc: f_proc.terminate()
        logger.info("all_services_stopped")
