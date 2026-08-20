"""shared/scrubber.py — E5b: redacao de segredos antes do envio a cloud.

Complementa o gate E5 (shared/exec_mode + llm_client._cloud_gate): o gate
DECIDE se envia (confirma/bloqueia por modo de execucao); o scrubber garante
que o conteudo que SAI da maquina nao carrega credenciais.

Principio: padroes de ALTA confianca (prefixo-ancorados). Este e um projeto de
bioinformatica — o prompt costuma ter sequencias (ACGT...), IDs de genes/
proteinas e numeros. Um scrubber ganancioso mutilaria dados legitimos, entao
so redigimos o que tem cara inequivoca de segredo. Nunca logamos o valor — so
o rotulo e a contagem (ver `summarize`).

Envs:
  LILO_SCRUB         "1" (default) liga; "0"/"false"/"off" desliga tudo.
  LILO_SCRUB_EMAILS  "0" (default) — e-mails NAO sao redigidos por padrao
                     (podem ser conteudo cientifico legitimo, ex.: autor de
                     paper); "1"/"true"/"on" liga a redacao de e-mails.
"""
from __future__ import annotations

import os
import re
from collections import Counter

# ‹REDIGIDO:label› — marcador visivel, sem revelar nada do valor original.
_PLACEHOLDER = "‹REDIGIDO:%s›"

# (rotulo, regex). Ordem importa: o mais especifico primeiro (ex.: sk-ant-
# antes do sk- generico da OpenAI).
_PATTERNS = [
    ("private_key", re.compile(
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"
        r"[\s\S]*?-----END (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("openai_key", re.compile(
        r"sk-proj-[A-Za-z0-9_\-]{20,}|sk-[A-Za-z0-9]{32,}")),
    ("github_token", re.compile(
        r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}")),
    ("aws_akid", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("google_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("slack_token", re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}")),
    ("jwt", re.compile(
        r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}")),
    ("bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{20,}")),
]

_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

# key=value / key: value cujo VALOR "parece" segredo. Pos-validado em codigo
# (ver _value_is_secretish) para nao redigir prosa do tipo "Token: introducao".
_KV = re.compile(
    r"(?i)\b(api[_-]?key|apikey|secret|password|passwd|pwd|token|authorization)"
    r"\s*[:=]\s*(\"[^\"]{6,}\"|'[^']{6,}'|[A-Za-z0-9._\-]{12,})")


def _enabled() -> bool:
    # Literal inline no environ.get (nao via wrapper): mantem a env visivel ao
    # detector de "doc morta" do /diagnostico_lilo (scripts/diagnostico_lilo.py).
    return str(os.environ.get("LILO_SCRUB", "1")).strip().lower() not in (
        "0", "false", "off")


def _emails_on() -> bool:
    return str(os.environ.get("LILO_SCRUB_EMAILS", "0")).strip().lower() in (
        "1", "true", "on")


def _value_is_secretish(v: str) -> bool:
    """Valor entre aspas => trata como segredo; senao, exige >=1 digito para
    evitar falso-positivo em prosa (ex.: 'token: bioinformatica')."""
    if v[:1] in "\"'" and v[-1:] in "\"'":
        return True
    return any(c.isdigit() for c in v)


def scrub_secrets(text):
    """Redige segredos em `text`.

    Retorna (texto_redigido, findings), onde findings e uma lista de rotulos
    (pode repetir) para o chamador contar/logar SEM expor o valor. Seguro em
    texto vazio/None e quando LILO_SCRUB=0 (retorna o texto intacto)."""
    if not text or not _enabled():
        return (text or "", [])
    findings: list = []
    out = text

    for label, rx in _PATTERNS:
        def _sub(m, _label=label):
            findings.append(_label)
            return _PLACEHOLDER % _label
        out = rx.sub(_sub, out)

    def _kv_sub(m):
        val = m.group(2)
        if _value_is_secretish(val):
            findings.append("kv_secret")
            pre = m.group(0)[: m.start(2) - m.start(0)]
            return pre + (_PLACEHOLDER % "kv_secret")
        return m.group(0)
    out = _KV.sub(_kv_sub, out)

    if _emails_on():
        def _em(m):
            findings.append("email")
            return _PLACEHOLDER % "email"
        out = _EMAIL.sub(_em, out)

    return (out, findings)


def summarize(findings) -> str:
    """'anthropic_key×1, jwt×2' a partir da lista de findings (p/ log)."""
    c = Counter(findings or [])
    return ", ".join("%s×%d" % (k, n) for k, n in sorted(c.items()))
