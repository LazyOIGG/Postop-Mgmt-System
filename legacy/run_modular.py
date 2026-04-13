import uvicorn
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True
    )
