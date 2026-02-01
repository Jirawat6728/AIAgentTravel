"""
เซอร์วิส Text-to-Speech ด้วย Gemini TTS API
แปลงข้อความเป็นเสียง (รองรับภาษาไทย) สำหรับเล่นในแชทโหมดเสียง
"""

from __future__ import annotations
import io
import struct
import os
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import LLMException

logger = get_logger(__name__)

# โมเดล TTS ของ Gemini (รับข้อความ ส่งคืนเสียงเท่านั้น)
DEFAULT_TTS_MODEL = "gemini-2.5-flash-preview-tts"
# PCM จาก API: 24kHz, 16-bit, mono
TTS_SAMPLE_RATE = 24000
TTS_SAMPLE_WIDTH = 2  # 16-bit
TTS_CHANNELS = 1


def _pcm_to_wav(pcm_bytes: bytes) -> bytes:
    """ใส่ WAV header ให้ PCM (16-bit, mono) แล้วส่งคืนเป็น bytes."""
    n_frames = len(pcm_bytes) // (TTS_SAMPLE_WIDTH * TTS_CHANNELS)
    data_size = n_frames * TTS_CHANNELS * TTS_SAMPLE_WIDTH
    header_size = 44
    file_size = header_size + data_size

    buf = io.BytesIO()
    # RIFF header
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", file_size - 8))
    buf.write(b"WAVE")
    # fmt chunk
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))  # chunk size (PCM)
    buf.write(struct.pack("<H", 1))   # audio format (1 = PCM)
    buf.write(struct.pack("<H", TTS_CHANNELS))
    buf.write(struct.pack("<I", TTS_SAMPLE_RATE))
    buf.write(struct.pack("<I", TTS_SAMPLE_RATE * TTS_CHANNELS * TTS_SAMPLE_WIDTH))
    buf.write(struct.pack("<H", TTS_CHANNELS * TTS_SAMPLE_WIDTH))
    buf.write(struct.pack("<H", 8 * TTS_SAMPLE_WIDTH))
    # data chunk
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(pcm_bytes)
    return buf.getvalue()


class TTSService:
    """แปลงข้อความเป็นเสียงด้วย Gemini TTS API"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or getattr(settings, "gemini_api_key", None) or "").strip()
        if not self.api_key:
            raise LLMException("GEMINI_API_KEY is required for TTS")
        self.model_id = os.getenv("GEMINI_TTS_MODEL", DEFAULT_TTS_MODEL).strip() or DEFAULT_TTS_MODEL

    async def generate_speech(
        self,
        text: str,
        voice_name: str = "Kore",
        language: str = "th",
        audio_format: str = "MP3",
    ) -> bytes:
        """
        แปลงข้อความเป็นเสียงด้วย Gemini TTS

        Args:
            text: ข้อความที่ต้องการให้อ่าน
            voice_name: ชื่อเสียง (Kore, Aoede, Callirrhoe, Puck ฯลฯ)
            language: รหัสภาษา (เช่น th สำหรับไทย)
            audio_format: MP3 หรือ LINEAR16 (ปัจจุบันส่งคืน WAV สำหรับทั้งคู่)

        Returns:
            bytes ของไฟล์เสียง (WAV)
        """
        from google import genai
        from google.genai import types

        if not text or not text.strip():
            raise ValueError("text is required")

        # เติมบริบทภาษาให้โมเดล (Gemini TTS รองรับหลายภาษา)
        if language == "th":
            content = f"อ่านด้วยน้ำเสียงสุภาพเป็นกันเอง: {text.strip()}"
        else:
            content = text.strip()

        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            ),
        )

        client = genai.Client(api_key=self.api_key)
        response = await client.aio.models.generate_content(
            model=self.model_id,
            contents=content,
            config=config,
        )

        if not response.candidates or not response.candidates[0].content.parts:
            logger.warning("TTS response had no candidates or parts")
            raise LLMException("TTS returned no audio")

        part = response.candidates[0].content.parts[0]
        if not part.inline_data or not part.inline_data.data:
            logger.warning("TTS response part had no inline_data.data")
            raise LLMException("TTS returned no audio data")

        pcm_bytes = part.inline_data.data
        if isinstance(pcm_bytes, str):
            import base64
            pcm_bytes = base64.b64decode(pcm_bytes)

        wav_bytes = _pcm_to_wav(bytes(pcm_bytes))

        # ปัจจุบันส่งคืน WAV เสมอ (เบราว์เซอร์เล่นได้); ถ้าต้องการ MP3 ต้องแปลงเพิ่ม
        if audio_format.upper() == "MP3":
            # คืน WAV แทน MP3 (frontend ใช้ Audio() เล่น WAV ได้)
            return wav_bytes
        return wav_bytes
