"""
shared/speaker_id.py — Reconhecimento de LOCUTOR do LILO (leve, sem torch). V14.6.
==============================================================================
Verifica se a voz que comanda o LILO é a do DONO — biometria LOCAL e leve
(MFCC via librosa + cosseno; sem redes neurais pesadas / sem PyTorch). Pensado
para um PC pessoal de um único usuário: o valor é reconhecer o dono (e carregar
suas memórias) por conveniência.

⚠️  NÃO é uma fronteira de segurança forte: o embedding MFCC é pouco
discriminativo. NÃO gateie ações sensíveis SÓ por voz — combine com outro fator.

Endurecimento V14.6 (vs V14.2):
  - score = cosseno ao CENTROIDE do dono (robusto). Antes usava `max` sobre as
    amostras, o que era permissivo (bastava colar em UMA amostra).
  - limiar ADAPTATIVO/auto-calibrado: eff_thr = self_sim − margem, com piso
    `LILO_VOICE_THRESHOLD`. self_sim = auto-similaridade média do enrollment.
  - embedding mais rico: MFCC + delta + delta² (120-d) e trim de silêncio.
  - voiceprint VERSIONADO: o formato antigo (80-d) é detectado como incompatível
    e força re-enroll (sem crash de dimensão).

Fluxo:
  1. enroll(audio_bytes)  — adiciona uma amostra ao voiceprint do dono (≥3-5).
  2. verify(audio_bytes)  — {is_owner, score, threshold, self_sim, ...}.
O voiceprint (embeddings + centroide) é salvo em data/voiceprint/owner.npz.

Config (env):
  LILO_VOICE_THRESHOLD   PISO do limiar de cosseno (def 0.80)
  LILO_VOICE_MARGIN      folga subtraída da auto-similaridade (def 0.08)
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

# PISO do limiar (o limiar efetivo é adaptativo, ver verify()). Subiu de 0.75
# (V14.2) para 0.80 ao trocar max-sobre-amostras por cosseno-ao-centroide.
THRESHOLD = float(os.getenv("LILO_VOICE_THRESHOLD", "0.80"))
# Folga abaixo da auto-similaridade do dono: eff_thr = self_sim - MARGIN (>= piso).
MARGIN = float(os.getenv("LILO_VOICE_MARGIN", "0.08"))
# Versao do formato de embedding. 1 = 80-d (MFCC+delta, V14.2);
# 2 = 120-d (MFCC+delta+delta2 + trim). Mudou -> voiceprint antigo é descartado.
_EMB_VERSION = 2
_MIN_SECONDS = 0.5   # < 0.5s -> frames insuficientes p/ delta2 (largura 9)


def is_available() -> bool:
    try:
        import librosa  # noqa: F401
        import numpy  # noqa: F401
        return True
    except Exception:
        return False


def embedding(audio) -> "any":
    """Extrai um embedding fixo de voz (120,): média+desvio de MFCC(20), delta e
    delta². `audio`: bytes WAV/mp3 ou caminho. Retorna np.ndarray (120,) ou None.
    """
    import io
    import numpy as np
    import librosa
    try:
        if isinstance(audio, (bytes, bytearray)):
            y, sr = librosa.load(io.BytesIO(bytes(audio)), sr=16000, mono=True)
        else:
            y, sr = librosa.load(str(audio), sr=16000, mono=True)
        if y is None or len(y) < sr * _MIN_SECONDS:
            return None
        # remove silêncio das pontas (melhora a discriminação do locutor)
        y, _ = librosa.effects.trim(y, top_db=30)
        if len(y) < sr * _MIN_SECONDS:
            return None
        # NOTA: NÃO aplicar CMVN aqui — a média do MFCC carrega o timbre do
        # locutor (cue principal); normalizá-la a zero apagaria o sinal útil.
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
        d = librosa.feature.delta(mfcc)
        d2 = librosa.feature.delta(mfcc, order=2)
        vec = np.concatenate([mfcc.mean(1), mfcc.std(1),
                              d.mean(1), d.std(1),
                              d2.mean(1), d2.std(1)])      # (120,)
        n = np.linalg.norm(vec)
        return vec / n if n else vec
    except Exception as e:
        log.warning("embedding falhou: %s", e)
        return None


def _cosine(a, b) -> float:
    import numpy as np
    return float(np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) or 1.0))


def _load_owner():
    """Carrega (embs, centroid) do voiceprint SE compatível com a versão atual.
    Retorna None se ausente, ilegível ou de versão antiga (-> força re-enroll).
    Usa context manager: fecha o handle antes de qualquer escrita (lock Windows).
    """
    import numpy as np
    if not _OWNER.exists():
        return None
    try:
        with np.load(_OWNER) as data:
            ver = int(data["version"]) if "version" in data.files else 1
            if ver != _EMB_VERSION:
                return None
            return np.array(data["embs"]), np.array(data["centroid"])
    except Exception:
        return None


def enroll(audio) -> dict:
    """Adiciona uma amostra ao voiceprint do dono. Retorna {ok, n_samples}.
    Se houver um voiceprint de versão antiga/incompatível, recomeça do zero."""
    import numpy as np
    emb = embedding(audio)
    if emb is None:
        return {"ok": False, "error": "áudio inválido/curto (< %.1fs)" % _MIN_SECONDS,
                "n_samples": n_samples()}
    VOICEPRINT_DIR.mkdir(parents=True, exist_ok=True)
    owner = _load_owner()
    if owner is not None:
        embs = np.vstack([owner[0], emb])
    else:
        embs = emb.reshape(1, -1)   # fresh OU versão antiga incompatível -> recomeça
    np.savez(_OWNER, embs=embs, centroid=embs.mean(0), version=_EMB_VERSION)
    return {"ok": True, "n_samples": int(embs.shape[0])}


def n_samples() -> int:
    owner = _load_owner()
    return int(owner[0].shape[0]) if owner is not None else 0


def is_enrolled() -> bool:
    return n_samples() >= 3


def needs_reenroll() -> bool:
    """True se existe um voiceprint de versão ANTIGA (incompatível) -> o dashboard
    deve pedir re-enroll. False se ausente ou já na versão atual."""
    import numpy as np
    if not _OWNER.exists():
        return False
    try:
        with np.load(_OWNER) as data:
            ver = int(data["version"]) if "version" in data.files else 1
        return ver != _EMB_VERSION
    except Exception:
        return True


def verify(audio) -> dict:
    """Compara a voz com o voiceprint do dono. Retorna
    {is_owner, score, enrolled, threshold, floor, self_sim, needs_reenroll}.

    score      = cosseno ao centroide do dono (robusto).
    threshold  = limiar EFETIVO adaptativo = clamp(self_sim - MARGIN, floor, 0.99).
    self_sim   = auto-similaridade média do enrollment (consistência da voz do dono).
    """
    import numpy as np
    owner = _load_owner()
    if owner is None or owner[0].shape[0] < 3:
        return {"is_owner": False, "score": 0.0, "enrolled": False,
                "threshold": THRESHOLD, "floor": THRESHOLD,
                "needs_reenroll": needs_reenroll()}
    emb = embedding(audio)
    if emb is None:
        return {"is_owner": False, "score": 0.0, "enrolled": True,
                "threshold": THRESHOLD, "floor": THRESHOLD}
    embs, cen = owner
    # auto-calibração: limiar adaptativo a partir da auto-similaridade do dono.
    self_sim = float(np.mean([_cosine(e, cen) for e in embs]))
    eff_thr = min(0.99, max(THRESHOLD, self_sim - MARGIN))
    # score = cosseno ao CENTROIDE (sem max-sobre-amostras permissivo).
    score = _cosine(emb, cen)
    return {"is_owner": bool(score >= eff_thr), "score": round(score, 3),
            "enrolled": True, "threshold": round(eff_thr, 3),
            "floor": THRESHOLD, "self_sim": round(self_sim, 3),
            "needs_reenroll": False}


def reset() -> None:
    if _OWNER.exists():
        _OWNER.unlink()
