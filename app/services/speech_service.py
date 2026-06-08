import os
import traceback
import tempfile
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


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
                logger.info("dashscope_configured service=%s", "Fun-ASR")
            except Exception as e:
                logger.error("dashscope_config_failed error=%s", str(e))
                self.enabled = False

    def _convert_audio_to_wav(self, audio_data: bytes) -> bytes:
        """将音频数据转换为 16kHz 单声道的 WAV 格式"""
        if not PYDUB_AVAILABLE:
            logger.warning("pydub_not_available")
            return audio_data

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio_data)
                temp_path = tmp.name

            sound = AudioSegment.from_file(temp_path)

            logger.debug("original_audio channels=%s sample_rate=%s duration_s=%s", sound.channels, sound.frame_rate, len(sound)/1000)

            if sound.channels != 1:
                sound = sound.set_channels(1)
                logger.debug("audio_converted_to_mono")

            if sound.frame_rate != 16000:
                sound = sound.set_frame_rate(16000)
                logger.debug("audio_resampled target_rate=%s", 16000)

            output_path = temp_path + "_converted.wav"
            sound.export(output_path, format="wav")

            with open(output_path, 'rb') as f:
                converted_data = f.read()

            os.unlink(temp_path)
            os.unlink(output_path)

            logger.debug("audio_converted size_bytes=%s", len(converted_data))
            return converted_data

        except Exception as e:
            logger.error("audio_conversion_failed error=%s", str(e))
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

            logger.info("asr_begin size_bytes=%s", len(audio_data), temp_file=temp_file_path)

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
                    logger.info("asr_success text=%s", recognized_text)
                    return recognized_text
                else:
                    logger.info("asr_empty_result")
                    return ""
            else:
                error_msg = f"语音识别失败，状态码: {result.status_code}"
                logger.error("asr_failed status_code=%s", result.status_code)
                return error_msg

        except Exception as e:
            logger.error("asr_exception error=%s", str(e))
            traceback.print_exc()
            return f"语音识别失败: {str(e)}"
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    async def synthesize(self, text: str, voice: str = None) -> Optional[bytes]:
        """文本转语音 (TTS) — 对接 DashScope CosyVoice"""
        if not self.enabled:
            logger.warning("tts_not_enabled")
            return None
        try:
            from dashscope.audio.tts import SpeechSynthesizer
            result = SpeechSynthesizer.call(
                model='cosyvoice-v1',
                voice=voice or settings.TTS_VOICE,
                text=text,
                format='mp3'
            )
            audio_data = result.get_audio_data()
            if audio_data is not None:
                logger.info("tts_success size_bytes=%s", len(audio_data))
                return audio_data
            else:
                logger.error("tts_failed response=%s", str(result.get_response()))
                return None
        except Exception as e:
            logger.error("tts_exception error=%s", str(e))
            traceback.print_exc()
            return None

    @property
    def tts_enabled(self) -> bool:
        return self.enabled and settings.TTS_ENABLED


speech_service = SpeechService()
