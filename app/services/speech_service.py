import os
import traceback
import tempfile
from typing import Optional
from app.core.config import settings


try:
    import dashscope
    from dashscope.audio.asr import Recognition
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False


try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


class SpeechService:
    """语音识别服务 - 基于阿里云 Fun-ASR API"""

    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.enabled = DASHSCOPE_AVAILABLE and bool(self.api_key)
        self._setup_dashscope()

    def _setup_dashscope(self):
        """配置阿里云 DashScope SDK"""
        if self.enabled:
            try:
                dashscope.api_key = self.api_key
                print("[SUCCESS] 阿里云 DashScope (Fun-ASR) 配置成功")
            except Exception as e:
                print(f"[ERROR] 阿里云 DashScope 配置失败: {e}")
                self.enabled = False

    def _convert_audio_to_wav(self, audio_data: bytes) -> bytes:
        """将音频数据转换为 16kHz 单声道的 WAV 格式"""
        if not PYDUB_AVAILABLE:
            print("[WARN] pydub 未安装，无法自动转换音频格式")
            return audio_data
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio_data)
                temp_path = tmp.name
            
            sound = AudioSegment.from_file(temp_path)
            
            print(f"[DEBUG] 原始音频: 通道数={sound.channels}, 采样率={sound.frame_rate} Hz, 时长={len(sound)/1000}秒")
            
            if sound.channels != 1:
                sound = sound.set_channels(1)
                print("[DEBUG] 已转换为单声道")
            
            if sound.frame_rate != 16000:
                sound = sound.set_frame_rate(16000)
                print("[DEBUG] 已转换为 16000 Hz")
            
            output_path = temp_path + "_converted.wav"
            sound.export(output_path, format="wav")
            
            with open(output_path, 'rb') as f:
                converted_data = f.read()
            
            os.unlink(temp_path)
            os.unlink(output_path)
            
            print(f"[DEBUG] 转换后音频: 大小={len(converted_data)} bytes")
            return converted_data
            
        except Exception as e:
            print(f"[ERROR] 音频转换失败: {e}")
            traceback.print_exc()
            return audio_data

    async def transcribe(self, audio_data: bytes) -> Optional[str]:
        """
        将语音转换为文本 (STT)

        Args:
            audio_data: 音频文件的二进制数据（支持 wav, pcm, mp3, aac 等）

        Returns:
            识别出的文本，失败时返回 None 或错误信息
        """
        if not self.enabled:
            return "语音识别服务未启用，请检查 API Key 和 dashscope 依赖"

        temp_file_path = None
        try:
            audio_data = self._convert_audio_to_wav(audio_data)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio_data)
                temp_file_path = tmp.name

            print(f"[INFO] 音频数据大小: {len(audio_data)} bytes，临时文件: {temp_file_path}")

            recognition = Recognition(model='fun-asr-realtime-2026-02-28',
                                  format='wav',
                                  sample_rate=16000,
                                  language_hints=['zh', 'en'],
                                  callback=None)
            
            result = recognition.call(temp_file_path)

            if result.status_code == 200:
                sentence_result = result.get_sentence()
                if sentence_result:
                    recognized_text = ''.join([item['text'] for item in sentence_result])
                    print(f"[INFO] Fun-ASR 识别成功: {recognized_text}")
                    return recognized_text
                else:
                    print("[INFO] Fun-ASR 识别成功，但无结果")
                    return ""
            else:
                error_msg = f"语音识别失败，状态码: {result.status_code}"
                print(f"[ERROR] {error_msg}")
                return error_msg

        except Exception as e:
            print(f"[ERROR] 语音识别过程中发生异常: {e}")
            traceback.print_exc()
            return f"语音识别失败: {str(e)}"
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    async def synthesize(self, text: str) -> Optional[bytes]:
        """
        文本转语音 (TTS) - 预留接口
        """
        return None


speech_service = SpeechService()