"""tests/test_transcribe.py — STT local (V14.1), offline (sem baixar modelo)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_available():
    from shared import transcribe as tx
    assert tx.is_available() is True   # faster-whisper instalado


def test_interface_and_config():
    from shared import transcribe as tx
    assert callable(tx.transcribe)
    assert tx.WHISPER_MODEL and tx.WHISPER_LANG    # defaults definidos


def test_transcribe_empty_is_graceful():
    from shared import transcribe as tx
    # bytes vazios -> string vazia, sem excecao (nao deve derrubar o chat)
    assert tx.transcribe(b"") == ""
