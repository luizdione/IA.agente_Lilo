"""
shared/transcribe.py — Transcrição de voz LOCAL (STT) do LILO. V14.1.
====================================================================
Converte áudio (do microfone via st.audio_input) em texto com faster-whisper,
100% local (roda em CPU por padrão; nenhum áudio sai da máquina). O modelo é
carregado lazy e cacheado no processo.

Config (env):
  LILO_WHISPER_MODEL   modelo whisper (tiny|base|small|medium|large-v3) — def "base"
  LILO_WHISPER_DEVICE  cpu | cuda — def cpu
  LILO_WHISPER_COMPUTE int8 | float16 | float32 — def int8 (rápido em CPU)
  LILO_WHISPER_LANG    idioma padrão — def pt
"""

import os
import tempfile

try:
    from .logger import get_logger
    log = get_logger("Transcribe")
except Exception:  # uso standalone
    import logging
    log = logging.getLogger("Transcribe")

WHISPER_MODEL = os.getenv("LILO_WHISPER_MODEL", "base")
WHISPER_DEVICE = os.getenv("LILO_WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE = os.getenv("LILO_WHISPER_COMPUTE", "int8")
WHISPER_LANG = os.getenv("LILO_WHISPER_LANG", "pt")

_MODEL = None


def is_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except Exception:
        return False


def _get_model():
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel
        log.info("Carregando Whisper '%s' (%s/%s)...", WHISPER_MODEL,
                 WHISPER_DEVICE, WHISPER_COMPUTE)
        _MODEL = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE,
                              compute_type=WHISPER_COMPUTE)
    return _MODEL


def transcribe(audio, language: str = None) -> str:
    """Transcreve `audio` (bytes WAV/mp3 OU caminho) -> texto. '' em falha.

    VAD filtra silêncio. Idioma default LILO_WHISPER_LANG (pt).
    """
    if not is_available():
        log.warning("faster-whisper ausente; STT indisponivel")
        return ""
    path, is_tmp = None, False
    try:
        if isinstance(audio, (bytes, bytearray)):
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
                fh.write(audio)
                path, is_tmp = fh.name, True
        else:
            path = str(audio)
        model = _get_model()
        segments, _info = model.transcribe(
            path, language=language or WHISPER_LANG, vad_filter=True)
        return " ".join(s.text.strip() for s in segments).strip()
    except Exception as e:
        log.error("Transcricao falhou: %s", e)
        return ""
    finally:
        if is_tmp and path:
            try:
                os.unlink(path)
            except OSError:
                pass
