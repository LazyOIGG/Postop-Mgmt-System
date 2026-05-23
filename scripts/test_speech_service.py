import os
import sys

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.speech_service import speech_service

async def test_speech_service():
    # 读取测试音频文件
    audio_file_path = os.path.join(os.path.dirname(__file__), '标准录音 3(1)_mono_16k.wav')
    
    with open(audio_file_path, 'rb') as f:
        audio_data = f.read()
    
    print(f"Testing speech_service with audio file: {audio_file_path}")
    print(f"Audio data size: {len(audio_data)} bytes")
    
    # 调用语音识别服务
    result = await speech_service.transcribe(audio_data)
    
    print(f"Recognition result: {result}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_speech_service())