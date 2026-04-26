from http import HTTPStatus
from dashscope.audio.asr import Recognition

# 若没有将API Key配置到环境变量中，需将下面这行代码注释放开，并将apiKey替换为自己的API Key
import dashscope
import os
from dotenv import load_dotenv

load_dotenv()
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY", "")

recognition = Recognition(model='fun-asr-realtime-2026-02-28',
                          format='wav',
                          sample_rate=16000,
                          # “language_hints”只支持paraformer-realtime-v2模型
                          language_hints=['zh', 'en'],
                          callback=None)
import os
result = recognition.call(os.path.join(os.path.dirname(__file__), '标准录音 3(1)_mono_16k.wav'))
if result.status_code == HTTPStatus.OK:
    print('识别结果：')
    print(result.get_sentence())
else:
    print('Error: ', result.message)
    
print(
    '[Metric] requestId: {}, first package delay ms: {}, last package delay ms: {}'
    .format(
        recognition.get_last_request_id(),
        recognition.get_first_package_delay(),
        recognition.get_last_package_delay(),
    ))