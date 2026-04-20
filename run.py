import uvicorn
import os
import sys
import subprocess
import time
import webbrowser
import socket
from pathlib import Path

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
        # 使用netstat命令查找占用端口的进程
        cmd = f"netstat -ano | findstr :{port}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # 解析输出，获取PID
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = parts[4]
                    try:
                        # 终止进程
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                        print(f"[INFO] 已终止占用端口 {port} 的进程 (PID: {pid})")
                    except:
                        pass
    except:
        pass

# 添加根目录到路径
sys.path.append(str(Path(__file__).parent))

def start_fastapi():
    """启动 FastAPI 后端"""
    port = 8000
    print(f"[INFO] 检查端口 {port} 是否被占用...")
    if check_port(port):
        print(f"[INFO] 端口 {port} 被占用，正在清理...")
        kill_process_on_port(port)
        time.sleep(2)  # 等待进程完全终止
    print("[INFO] 启动 FastAPI 服务...")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        env=os.environ.copy()
    )

def start_streamlit():
    """启动 Streamlit 前端"""
    port = 8501
    print(f"[INFO] 检查端口 {port} 是否被占用...")
    if check_port(port):
        print(f"[INFO] 端口 {port} 被占用，正在清理...")
        kill_process_on_port(port)
        time.sleep(2)  # 等待进程完全终止
    print("[INFO] 启动 Streamlit 应用...")
    time.sleep(5) # 等待后端就绪
    
    url = "http://localhost:8501"
    process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "streamlit_app.py", "--server.port", "8501", "--server.headless", "true"],
        env=os.environ.copy()
    )
    
    print(f"[SUCCESS] 浏览器访问地址: {url}")
    webbrowser.open(url)
    return process

if __name__ == "__main__":
    f_proc = None; s_proc = None
    try:
        f_proc = start_fastapi()
        s_proc = start_streamlit()
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] 检测到中断，正在关闭服务...")
    finally:
        if s_proc: s_proc.terminate()
        if f_proc: f_proc.terminate()
        print("[SUCCESS] 所有服务已关闭")
