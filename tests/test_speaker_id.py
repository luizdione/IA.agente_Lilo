"""tests/test_speaker_id.py — reconhecimento de locutor (V14.2), offline.

Usa "vozes" sintéticas (formantes distintas) para validar o PIPELINE
(embedding + enroll + verify + discriminação relativa), não a acurácia em voz
real. Isola o voiceprint num tmp (monkeypatch de _OWNER).
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _synth(path, formants, dur=1.2, sr=16000, seed=0, noise=0.01):
    import numpy as np
    import soundfile as sf
    rng = np.random.default_rng(seed)
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    y = sum(np.sin(2 * np.pi * f * t) for f in formants) / len(formants)
    y = y + noise * rng.standard_normal(len(t))
    sf.write(str(path), y.astype("float32"), sr)
    return Path(path).read_bytes()


@pytest.fixture()
def sid(tmp_path, monkeypatch):
    from shared import speaker_id as s
    monkeypatch.setattr(s, "_OWNER", tmp_path / "owner.npz")
    return s


def test_available(sid):
    assert sid.is_available() is True


def test_embedding_shape(sid, tmp_path):
    emb = sid.embedding(_synth(tmp_path / "a.wav", [300, 2200, 2900], seed=1))
    assert emb is not None and emb.shape == (80,)


def test_enroll_and_verify_owner(sid, tmp_path):
    assert sid.is_enrolled() is False
    for k in range(3):                                   # enrolla o "dono" (voz A)
        r = sid.enroll(_synth(tmp_path / f"a{k}.wav", [300, 2200, 2900], seed=k))
        assert r["ok"]
    assert sid.is_enrolled() is True and sid.n_samples() == 3
    # voz A de novo -> reconhece; outra voz (B) -> score menor
    va = sid.verify(_synth(tmp_path / "a_test.wav", [300, 2200, 2900], seed=99))
    vb = sid.verify(_synth(tmp_path / "b_test.wav", [550, 1100, 2400], seed=99))
    assert va["enrolled"] and 0.0 <= va["score"] <= 1.0
    assert va["score"] > vb["score"]                     # discrimina A de B


def test_verify_without_enrollment(sid, tmp_path):
    out = sid.verify(_synth(tmp_path / "x.wav", [300, 900], seed=2))
    assert out["enrolled"] is False and out["is_owner"] is False
