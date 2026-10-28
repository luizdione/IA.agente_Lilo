"""opencode/opencode.json coerente com o Modelfile.lilo-code e sem segredos."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = ROOT / "opencode" / "opencode.json"
MODELFILE = ROOT / "ollama" / "Modelfile.lilo-code"


def _cfg() -> dict:
    return json.loads(CFG.read_text(encoding="utf-8"))


def test_json_valido_e_sem_segredos():
    texto = CFG.read_text(encoding="utf-8")
    json.loads(texto)
    assert not re.search(r"sk-[A-Za-z0-9]{8,}|Bearer [A-Za-z0-9_\-]{20,}", texto)
    assert "{env:LILO_HOST_TOKEN}" in texto


def test_modelo_local_coerente_com_o_modelfile():
    c = _cfg()
    m = c["provider"]["ollama"]["models"]["lilo-code"]
    assert m["temperature"] is True            # senao o /v1 do Ollama 0.40 forca temperature=1.0
    assert m["tool_call"] is True and m["reasoning"] is False
    num_ctx = int(re.search(r"^PARAMETER num_ctx (\d+)", MODELFILE.read_text(encoding="utf-8"), re.M).group(1))
    assert m["limit"]["context"] == num_ctx    # sem limit.context o OpenCode nunca compacta
    assert m["limit"]["output"] <= num_ctx // 2
    assert c["provider"]["ollama"]["options"]["baseURL"].startswith("http://127.0.0.1:11434")
    assert not re.search(r"^SYSTEM", MODELFILE.read_text(encoding="utf-8"), re.M)   # o OpenCode manda o dele


def test_permissoes_e_mcp():
    c = _cfg()
    assert c["permission"]["edit"] == "ask" and c["permission"]["bash"]["*"] == "ask"
    assert c["permission"]["bash"]["git push*"] == "deny" and c["permission"]["webfetch"] == "deny"
    assert set(c["mcp"]) == {"conhecimento", "analise", "exec"}
    assert all(v["type"] == "remote" and v["url"].startswith("http://127.0.0.1:8790/") for v in c["mcp"].values())
    assert c["agent"]["ciencia"]["permission"]["conhecimento_resumir_arquivo"] == "deny"
    for a in ("build", "plan", "ciencia"):
        assert c["agent"][a]["temperature"] == 0.7 and c["agent"][a]["top_p"] == 0.8
    assert c["autoupdate"] is False and c["share"] == "disabled"
