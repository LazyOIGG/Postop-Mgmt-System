import uvicorn
import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path

# 添加根目录到路径
sys.path.append(str(Path(__file__).parent))

def start_fastapi():
    """启动 FastAPI 后端"""
    print("[INFO] ℹ️ 启动 FastAPI 服务...")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        env=os.environ.copy()
    )

def start_streamlit():
    """启动 Streamlit 前端"""
    print("[INFO] ℹ️ 启动 Streamlit 应用...")
    time.sleep(5) # 等待后端就绪
    
    url = "http://localhost:8501"
    process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "streamlit_app.py", "--server.port", "8501", "--server.headless", "true"],
        env=os.environ.copy()
    )
    
    print(f"[SUCCESS] ✅ 浏览器访问地址: {url}")
    webbrowser.open(url)
    return process

if __name__ == "__main__":
    f_proc = None; s_proc = None
    try:
        f_proc = start_fastapi()
        s_proc = start_streamlit()
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] ℹ️ 检测到中断，正在关闭服务...")
    finally:
        if s_proc: s_proc.terminate()
        if f_proc: f_proc.terminate()
        print("[SUCCESS] ✅ 所有服务已关闭")
