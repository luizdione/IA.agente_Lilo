"""Testes do scrubber de segredos pre-cloud (E5b).

Offline/herméticos: exercitam shared/scrubber.py (padroes, opt-in de e-mail,
kill-switch, ausencia de falso-positivo em texto cientifico) e a integracao
com llm_client._maybe_cloud_prepare (scrub so no destino cloud).
"""
import importlib

import pytest

scrubber = importlib.import_module("shared.scrubber")


# --- helpers ---------------------------------------------------------------
def _clean_env(monkeypatch):
    monkeypatch.delenv("LILO_SCRUB", raising=False)
    monkeypatch.delenv("LILO_SCRUB_EMAILS", raising=False)


# --- padroes de segredo ----------------------------------------------------
@pytest.mark.parametrize("secret,label", [
    ("sk-ant-" + "A" * 40, "anthropic_key"),
    ("sk-" + "B" * 40, "openai_key"),
    ("ghp_" + "C" * 36, "github_token"),
    ("AKIA" + "1234567890ABCDEF", "aws_akid"),
    ("AIza" + "a" * 35, "google_key"),
    ("xoxb-123456789012-abcdefghijkl", "slack_token"),
    ("eyJhbGciOiJIUzI1.eyJzdWIiOiIxMjM0.SflKxwRJSMeKKF2QT4", "jwt"),
])
def test_redige_padroes(monkeypatch, secret, label):
    _clean_env(monkeypatch)
    out, findings = scrubber.scrub_secrets("antes " + secret + " depois")
    assert secret not in out, "o segredo bruto nao pode sobrar"
    assert "REDIGIDO" in out
    assert label in findings


def test_redige_chave_privada(monkeypatch):
    _clean_env(monkeypatch)
    pem = ("-----BEGIN RSA PRIVATE KEY-----\nMIIBOgIBAAJB\nabc\n"
           "-----END RSA PRIVATE KEY-----")
    out, findings = scrubber.scrub_secrets("cfg:\n" + pem)
    assert "PRIVATE KEY" not in out
    assert "private_key" in findings


def test_bearer(monkeypatch):
    _clean_env(monkeypatch)
    out, findings = scrubber.scrub_secrets("Authorization: Bearer " + "z" * 30)
    assert "bearer" in findings
    assert "z" * 30 not in out


# --- key=value pos-validado ------------------------------------------------
def test_kv_com_digito_ou_aspas(monkeypatch):
    _clean_env(monkeypatch)
    out, findings = scrubber.scrub_secrets('password = "hunter2islongenough"')
    assert "kv_secret" in findings
    assert "hunter2islongenough" not in out
    out2, f2 = scrubber.scrub_secrets("api_key=abcdef123456789")
    assert "kv_secret" in f2


def test_kv_prosa_nao_redige(monkeypatch):
    """'Token: introducao' NAO e segredo (sem digito, sem aspas)."""
    _clean_env(monkeypatch)
    txt = "Token: introducao do artigo sobre metabolismo"
    out, findings = scrubber.scrub_secrets(txt)
    assert out == txt
    assert findings == []


# --- ausencia de falso-positivo em texto cientifico ------------------------
def test_texto_cientifico_intacto(monkeypatch):
    _clean_env(monkeypatch)
    txt = ("Sequencia ACGTACGTACGTTTGGCCAA do gene ENSG00000139618, "
           "p-value = 0.003, n = 42 amostras. Proteina P53 (TP53).")
    out, findings = scrubber.scrub_secrets(txt)
    assert out == txt
    assert findings == []


# --- e-mails: opt-in -------------------------------------------------------
def test_email_default_off(monkeypatch):
    _clean_env(monkeypatch)
    txt = "contato autor: fulano@exemplo.org"
    out, findings = scrubber.scrub_secrets(txt)
    assert out == txt
    assert "email" not in findings


def test_email_opt_in(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("LILO_SCRUB_EMAILS", "1")
    out, findings = scrubber.scrub_secrets("autor: fulano@exemplo.org")
    assert "fulano@exemplo.org" not in out
    assert "email" in findings


# --- kill-switch e bordas --------------------------------------------------
def test_kill_switch(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("LILO_SCRUB", "0")
    raw = "sk-ant-" + "A" * 40
    out, findings = scrubber.scrub_secrets(raw)
    assert out == raw
    assert findings == []


def test_vazio_e_none(monkeypatch):
    _clean_env(monkeypatch)
    assert scrubber.scrub_secrets("") == ("", [])
    assert scrubber.scrub_secrets(None) == ("", [])


def test_summarize():
    s = scrubber.summarize(["jwt", "anthropic_key", "jwt"])
    assert "jwt×2" in s
    assert "anthropic_key×1" in s


# --- integracao com llm_client._maybe_cloud_prepare ------------------------
def test_prepare_scrub_cloud(monkeypatch):
    _clean_env(monkeypatch)
    lc = importlib.import_module("shared.llm_client")
    mc = importlib.import_module("shared.model_catalog")

    class _Info:
        provider = "anthropic"  # != PROVIDER_OLLAMA -> destino cloud

    monkeypatch.setattr(mc, "get_model_info", lambda m: _Info())
    monkeypatch.setattr(lc, "_cloud_gate", lambda *a, **k: None)  # gate libera

    prompt = "minha chave e sk-ant-" + "A" * 40
    blocked, p2, s2 = lc._maybe_cloud_prepare("claude-sonnet-4-5", prompt, None)
    assert blocked is None
    assert "sk-ant-" not in p2
    assert "REDIGIDO" in p2


def test_prepare_noop_local(monkeypatch):
    _clean_env(monkeypatch)
    lc = importlib.import_module("shared.llm_client")
    mc = importlib.import_module("shared.model_catalog")

    class _Info:
        provider = mc.PROVIDER_OLLAMA  # destino LOCAL -> no-op

    monkeypatch.setattr(mc, "get_model_info", lambda m: _Info())
    prompt = "chave local sk-ant-" + "A" * 40
    blocked, p2, s2 = lc._maybe_cloud_prepare("qwen2.5", prompt, None)
    assert blocked is None
    assert p2 == prompt  # conteudo LOCAL nao e mexido
