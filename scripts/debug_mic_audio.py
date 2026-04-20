import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.speech_service import speech_service

async def test_mic_audio():
    """
    模拟麦克风音频测试
    由于无法直接获取麦克风数据，这里只是测试音频转换功能
    """
    # 创建一个测试音频文件（模拟静音）
    import wave
    import tempfile

    # 创建 1 秒的静音 WAV 文件
    sample_rate = 48000
    channels = 2
    duration = 1
    sample_width = 2

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        temp_path = tmp.name

    with wave.open(temp_path, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        # 写入静音（零值）
        wav_file.writeframes(b'\x00\x00' * sample_rate * channels * duration)

    with open(temp_path, 'rb') as f:
        audio_data = f.read()

    print(f"测试静音音频: {temp_path}")
    print(f"音频大小: {len(audio_data)} bytes")
    print(f"通道数: {channels}, 采样率: {sample_rate} Hz, 时长: {duration}秒")

    # 测试语音识别
    print("\n测试语音识别（静音音频）:")
    result = await speech_service.transcribe(audio_data)
    print(f"识别结果: '{result}'")

    # 清理
    os.unlink(temp_path)

    # 测试正常音频
    print("\n" + "="*50)
    print("测试正常音频:")
    audio_file_path = os.path.join(os.path.dirname(__file__), '标准录音 3(1)_mono_16k.wav')
    with open(audio_file_path, 'rb') as f:
        audio_data = f.read()
    print(f"音频大小: {len(audio_data)} bytes")
    result = await speech_service.transcribe(audio_data)
    print(f"识别结果: '{result}'")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_mic_audio())