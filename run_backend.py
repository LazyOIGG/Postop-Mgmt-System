import os
import sys
import subprocess
import time
import socket
from pathlib import Path


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
                        print(f"[INFO] 已终止占用端口 {port} 的进程 (PID: {pid})")
                    except:
                        pass
    except:
        pass


sys.path.append(str(Path(__file__).parent))


def start_backend():
    """启动 FastAPI 后端"""
    port = 8000
    print(f"[INFO] 检查端口 {port} 是否被占用...")
    if check_port(port):
        print(f"[INFO] 端口 {port} 被占用，正在清理...")
        kill_process_on_port(port)
        time.sleep(2)
    print("[INFO] 启动 FastAPI 后端服务...")
    print(f"[INFO] API 文档: http://localhost:{port}/docs")
    print(f"[INFO] 接口地址: http://localhost:{port}/api/v1/")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(port)],
        env=os.environ.copy()
    )


if __name__ == "__main__":
    proc = None
    try:
        proc = start_backend()
        print("[SUCCESS] 后端服务已启动，按 Ctrl+C 停止")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] 检测到中断，正在关闭服务...")
    finally:
        if proc:
            proc.terminate()
        print("[SUCCESS] 后端服务已关闭")
