"""
agents/skillsmith/agent.py — Criador de SUBAGENTES/SKILLS do LILO (V13.4).
========================================================================
Meta-skill: gera o SCAFFOLD de um novo subagente LILO (BaseAgent válido) a
partir de uma descrição. O scaffold é determinístico (template fixo que
compila); o LLM (cloud) só é usado para INFERIR os metadados (nome, keywords,
lista de tools) quando o chamador não os fornece.

Segurança: NÃO auto-registra o agente no roteamento (não modifica lilo.py) —
retorna as linhas exatas para o usuário revisar e colar. Não sobrescreve um
agente existente. Valida que o código gerado COMPILA antes de declarar sucesso.

Tools: propose_agent (LLM infere specs), create_agent_scaffold (escreve+valida).
"""

import json
import keyword
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared.base_agent import BaseAgent
from shared.llm_client import get_client
from shared.models import WORKER_CLOUD
from shared.utils import load_env, sanitize_query
from shared.logger import get_logger

load_env()
log = get_logger("SkillSmith")

SMITH_MODEL = os.getenv("LILO_SKILLSMITH_MODEL", WORKER_CLOUD)

_TEMPLATE = '''"""
agents/{name}/agent.py -- {description}
Scaffold gerado pelo skillsmith do LILO. Preencha a logica de run()/tools.
"""
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared.base_agent import BaseAgent
from shared.llm_client import get_client
from shared.utils import load_env, sanitize_query
from shared.logger import get_logger

load_env()
log = get_logger("{class_name}")


class {class_name}(BaseAgent):
    name = "{name}"
    description = {description_repr}
    KEYWORDS = {keywords_repr}
    cost_tier = "ollama"
    local_only = False
    latency_class = "fast"

    def __init__(self):
        super().__init__()
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_client()
        return self._llm

    def run(self, query: str, context: dict[str, Any] = {{}}) -> str:
        query = sanitize_query(query)
        log.info("{name}: %s", query[:80])
        # TODO: implemente a logica deste subagente (scaffold gerado).
        return "[{name}] scaffold ativo -- implemente run(). Recebi: " + query

    def get_tools(self) -> list[dict]:
        return {tools_repr}

    def health(self) -> dict:
        return {{"status": "ok", "agent": "{name}", "scaffold": True}}

    def capabilities(self) -> dict:
        return {{"name": "{name}", "keywords": self.KEYWORDS}}
'''


class SkillSmithAgent(BaseAgent):
    """Gera scaffolds de novos subagentes LILO a partir de uma descrição."""

    name = "skillsmith"
    description = (
        "Criador de subagentes/skills do LILO: gera o scaffold de um novo "
        "BaseAgent (codigo que compila) a partir de uma descricao, valida e "
        "retorna as instrucoes de registro. Nao auto-modifica o roteamento."
    )
    KEYWORDS = ["criar agente", "novo subagente", "criar skill", "nova skill",
                "scaffold", "gerar agente", "skill creator", "criar capacidade"]
    cost_tier = "ollama"
    local_only = False
    latency_class = "fast"

    def __init__(self):
        super().__init__()
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_client()
        return self._llm

    # ── helpers ──────────────────────────────────────────────────────────────
    @staticmethod
    def _valid_name(name: str) -> bool:
        return bool(re.fullmatch(r"[a-z][a-z0-9_]{1,30}", name or "")) \
            and not keyword.iskeyword(name)

    @staticmethod
    def _class_name(name: str) -> str:
        return "".join(p.capitalize() for p in name.split("_")) + "Agent"

    def _propose(self, description: str) -> dict:
        """LLM infere name/keywords/tools de uma descrição em linguagem natural."""
        prompt = (
            "A partir da descricao de um subagente, proponha os metadados. "
            "Responda APENAS JSON: {\"name\":\"snake_case_curto\","
            "\"keywords\":[\"...\"],\"tools\":[{\"name\":\"verbo_objeto\","
            "\"description\":\"...\"}]}.\n\nDESCRICAO: " + description)
        try:
            raw = self.llm.chat(prompt, system="Arquiteto de agentes. JSON valido.",
                                model=SMITH_MODEL, temperature=0.2, max_tokens=512)
            m = re.search(r"\{.*\}", raw or "", re.DOTALL)
            return json.loads(m.group(0)) if m else {}
        except Exception as e:
            log.warning("propose falhou: %s", e)
            return {}

    def _scaffold(self, name, description, keywords, tools) -> str:
        if not self._valid_name(name):
            return ("[skillsmith] nome invalido: '%s'. Use snake_case "
                    "(a-z, 0-9, _), iniciando por letra." % name)
        agent_dir = _ROOT / "agents" / name
        if agent_dir.exists():
            return "[skillsmith] ja existe agents/%s/ — escolha outro nome." % name
        tools = tools or [{"name": "%s_run" % name, "description": description}]
        tools_norm = [{"name": str(t.get("name", "")),
                       "description": str(t.get("description", "")),
                       "inputSchema": {"type": "object", "properties": {
                           "query": {"type": "string"}}, "required": ["query"]}}
                      for t in tools if t.get("name")]
        code = _TEMPLATE.format(
            name=name, class_name=self._class_name(name),
            description=description.replace('"', "'"),
            description_repr=repr(description),
            keywords_repr=repr(list(keywords or [])),
            tools_repr=repr(tools_norm))
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "__init__.py").write_text("", encoding="utf-8")
        agent_py = agent_dir / "agent.py"
        agent_py.write_text(code, encoding="utf-8")
        # valida que compila
        try:
            subprocess.run([sys.executable, "-m", "py_compile", str(agent_py)],
                           capture_output=True, text=True, timeout=60, check=True)
        except Exception as e:
            return "[skillsmith] scaffold gerado mas NAO compila: %s" % e
        cls = self._class_name(name)
        reg = ('        ("%s",%s"agents.%s.agent",%s"%s"),'
               % (name, " " * (9 - len(name)) if len(name) < 9 else " ",
                  name, " " * 8, cls))
        return (
            "## skillsmith — scaffold criado ✅\n\n"
            "- **Arquivo:** `agents/%s/agent.py` (compila; %d tool(s))\n"
            "- **Classe:** `%s`\n\n"
            "### Para ATIVAR (revise e cole em `lilo.py`)\n"
            "1. No `_AGENT_REGISTRY` de `_load_agents()`:\n```python\n%s\n```\n"
            "2. (opcional) keywords em `_KEYWORD_MAP[\"%s\"]` e tools em "
            "`get_tool_map()`.\n3. Implemente a lógica em `run()`.\n"
            % (name, len(tools_norm), cls, reg, name))

    # ── BaseAgent ─────────────────────────────────────────────────────────────
    def run(self, query: str, context: dict[str, Any] = {}) -> str:
        ctx = context or {}
        name = ctx.get("name", "")
        description = ctx.get("description") or sanitize_query(query)
        keywords = ctx.get("keywords")
        tools = ctx.get("tools")
        # Sem nome explícito: o LLM infere os metadados da descrição.
        if not name:
            spec = self._propose(description)
            name = spec.get("name", "")
            keywords = keywords or spec.get("keywords")
            tools = tools or spec.get("tools")
        if not name:
            return ("[skillsmith] informe 'name' no contexto ou descreva melhor "
                    "o agente (o LLM nao inferiu um nome).")
        return self._scaffold(name, description, keywords, tools)

    def get_tools(self) -> list[dict]:
        return [
            {"name": "propose_agent",
             "description": "LLM infere specs (nome/keywords/tools) de uma descricao.",
             "inputSchema": {"type": "object", "properties": {
                 "query": {"type": "string", "description": "Descricao do agente"}},
                 "required": ["query"]}},
            {"name": "create_agent_scaffold",
             "description": ("Cria o scaffold de um novo subagente LILO (compila) "
                             "e retorna as instrucoes de registro."),
             "inputSchema": {"type": "object", "properties": {
                 "name": {"type": "string", "description": "snake_case"},
                 "description": {"type": "string"},
                 "keywords": {"type": "array", "items": {"type": "string"}},
                 "tools": {"type": "array", "items": {"type": "object"}}},
                 "required": ["name", "description"]}},
        ]

    def capabilities(self) -> dict:
        return {"name": self.name, "keywords": self.KEYWORDS, "model": SMITH_MODEL}

    def health(self) -> dict:
        return {"status": "ok", "model": SMITH_MODEL,
                "agents_dir": str(_ROOT / "agents")}
