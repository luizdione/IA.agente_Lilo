"""
shared/speaker_id.py — Reconhecimento de LOCUTOR do LILO (leve, sem torch). V14.2.
==============================================================================
Verifica se a voz que comanda o LILO é a do DONO — autenticação biométrica
LOCAL e leve (MFCC via librosa + similaridade de cosseno; sem redes neurais
pesadas / sem PyTorch). Pensado para um PC pessoal de um único usuário: o valor
principal é segurança ("só o dono comanda por voz") + carregar o perfil/memórias
do dono ao reconhecê-lo.

Fluxo:
  1. enroll(audio_bytes)  — adiciona uma amostra ao voiceprint do dono (≥3-5).
  2. verify(audio_bytes)  — (is_owner, score) comparando com o voiceprint.
O voiceprint (centroide dos embeddings) é salvo em data/voiceprint/owner.npz.

Config (env):
  LILO_VOICE_THRESHOLD   limiar de cosseno p/ aceitar (def 0.75)
  LILO_VOICEPRINT_DIR    pasta do voiceprint (def data/voiceprint)
"""

import os
from pathlib import Path

try:
    from .logger import get_logger
    log = get_logger("SpeakerID")
except Exception:
    import logging
    log = logging.getLogger("SpeakerID")

_ROOT = Path(__file__).resolve().parents[1]
VOICEPRINT_DIR = Path(os.getenv("LILO_VOICEPRINT_DIR", str(_ROOT / "data" / "voiceprint")))
_OWNER = VOICEPRINT_DIR / "owner.npz"
THRESHOLD = float(os.getenv("LILO_VOICE_THRESHOLD", "0.75"))


def is_available() -> bool:
    try:
        import librosa  # noqa: F401
        import numpy  # noqa: F401
        return True
    except Exception:
        return False


def embedding(audio) -> "any":
    """Extrai um embedding fixo de voz: média+desvio de MFCC(20) + delta.
    `audio`: bytes WAV/mp3 ou caminho. Retorna np.ndarray (80,) ou None.
    """
    import io
    import numpy as np
    import librosa
    try:
        if isinstance(audio, (bytes, bytearray)):
            y, sr = librosa.load(io.BytesIO(bytes(audio)), sr=16000, mono=True)
        else:
            y, sr = librosa.load(str(audio), sr=16000, mono=True)
        if y is None or len(y) < sr * 0.3:        # < 0.3s -> inútil
            return None
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
        d = librosa.feature.delta(mfcc)
        vec = np.concatenate([mfcc.mean(1), mfcc.std(1),
                              d.mean(1), d.std(1)])      # (80,)
        n = np.linalg.norm(vec)
        return vec / n if n else vec
    except Exception as e:
        log.warning("embedding falhou: %s", e)
        return None


def _cosine(a, b) -> float:
    import numpy as np
    return float(np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) or 1.0))


def enroll(audio) -> dict:
    """Adiciona uma amostra ao voiceprint do dono. Retorna {ok, n_samples}."""
    import numpy as np
    emb = embedding(audio)
    if emb is None:
        return {"ok": False, "error": "áudio inválido/curto", "n_samples": n_samples()}
    VOICEPRINT_DIR.mkdir(parents=True, exist_ok=True)
    if _OWNER.exists():
        # context manager fecha o NpzFile ANTES do savez no mesmo arquivo
        # (no Windows, um handle de leitura aberto bloqueia a escrita).
        with np.load(_OWNER) as data:
            embs = np.vstack([data["embs"], emb])
    else:
        embs = emb.reshape(1, -1)
    np.savez(_OWNER, embs=embs, centroid=embs.mean(0))
    return {"ok": True, "n_samples": int(embs.shape[0])}


def n_samples() -> int:
    import numpy as np
    if not _OWNER.exists():
        return 0
    try:
        with np.load(_OWNER) as data:   # fecha o handle (evita lock no Windows)
            return int(data["embs"].shape[0])
    except Exception:
        return 0


def is_enrolled() -> bool:
    return n_samples() >= 3


def verify(audio) -> dict:
    """Compara a voz com o voiceprint do dono. Retorna
    {is_owner, score, enrolled, threshold}."""
    import numpy as np
    if not is_enrolled():
        return {"is_owner": False, "score": 0.0, "enrolled": False,
                "threshold": THRESHOLD}
    emb = embedding(audio)
    if emb is None:
        return {"is_owner": False, "score": 0.0, "enrolled": True,
                "threshold": THRESHOLD}
    with np.load(_OWNER) as data:       # materializa e fecha o handle
        cen = data["centroid"]
        embs = data["embs"]
    # score = melhor entre cosseno ao centroide e à amostra mais próxima.
    best = max(_cosine(emb, cen),
               max((_cosine(emb, e) for e in embs), default=0.0))
    return {"is_owner": bool(best >= THRESHOLD), "score": round(best, 3),
            "enrolled": True, "threshold": THRESHOLD}


def reset() -> None:
    if _OWNER.exists():
        _OWNER.unlink()
