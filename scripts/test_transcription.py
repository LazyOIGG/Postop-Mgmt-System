import os
from http import HTTPStatus
import dashscope

# 设置 API Key
dashscope.api_key = "sk-d9a533762e444fd7846a33f16aaf2942"

# 先测试 Recognition 类（与 test.py 相同）
try:
    temp_file_path = os.path.join(os.path.dirname(__file__), '标准录音 3(1)_mono_16k.wav')
    
    from dashscope.audio.asr import Recognition
    recognition = Recognition(model='fun-asr-realtime-2026-02-28',
                          format='wav',
                          sample_rate=16000,
                          language_hints=['zh', 'en'],
                          callback=None)
    
    print(f"Testing Recognition with file: {temp_file_path}")
    result2 = recognition.call(temp_file_path)
    print(f"Recognition result status code: {result2.status_code}")
    print(f"Recognition result: {result2.get_sentence()}")
    
except Exception as e:
    print(f"Recognition Error: {e}")
    import traceback
    traceback.print_exc()

# 再测试 Transcription 类
try:
    # 使用与 speech_service 相同的方式
    temp_file_path = os.path.join(os.path.dirname(__file__), '标准录音 3(1)_mono_16k.wav')
    file_url = f"file://{temp_file_path}"
    
    from dashscope.audio.asr import Transcription
    print(f"\nTesting Transcription with file: {file_url}")
    
    # 尝试使用 Transcription.call
    result = Transcription.call(
        model="paraformer-16k-1",
        file_urls=[file_url]
    )
    
    print(f"Result status code: {result.status_code}")
    print(f"Result output: {result.output}")
    
except Exception as e:
    print(f"Transcription Error: {e}")
    import traceback
    traceback.print_exc()