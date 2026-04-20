import os
import sys
import tempfile

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.speech_service import speech_service

async def debug_audio_format():
    """
    调试音频格式问题
    """
    # 读取测试音频文件
    audio_file_path = os.path.join(os.path.dirname(__file__), '标准录音 3(1)_mono_16k.wav')

    with open(audio_file_path, 'rb') as f:
        audio_data = f.read()

    print(f"测试音频文件: {audio_file_path}")
    print(f"音频数据大小: {len(audio_data)} bytes")

    # 检查文件头
    print(f"\n文件头 (前20 bytes): {audio_data[:20]}")

    # 保存临时文件并检查
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_data)
        temp_path = tmp.name

    # 检查 WAV 文件信息
    try:
        import wave
        with wave.open(temp_path, 'rb') as wav_file:
            print(f"\nWAV 文件信息:")
            print(f"  通道数: {wav_file.getnchannels()}")
            print(f"  采样宽度: {wav_file.getsampwidth()} bytes")
            print(f"  采样率: {wav_file.getframerate()} Hz")
            print(f"  帧数: {wav_file.getnframes()}")
            print(f"  压缩类型: {wav_file.getcomptype()}")
    except Exception as e:
        print(f"检查 WAV 文件失败: {e}")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    # 测试语音识别
    print("\n测试语音识别:")
    result = await speech_service.transcribe(audio_data)
    print(f"识别结果: '{result}'")

    # 对比：直接使用文件路径测试
    print("\n直接使用文件路径测试:")
    from app.services.speech_service import speech_service as ss
    import dashscope
    from dashscope.audio.asr import Recognition

    dashscope.api_key = ss.api_key
    recognition = Recognition(model='fun-asr-realtime-2026-02-28',
                              format='wav',
                              sample_rate=16000,
                              language_hints=['zh', 'en'],
                              callback=None)

    result2 = recognition.call(audio_file_path)
    print(f"状态码: {result2.status_code}")
    print(f"识别结果: {result2.get_sentence()}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug_audio_format())