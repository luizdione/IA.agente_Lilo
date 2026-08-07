"""
lilo_api.py -- API HTTP do LILO (plataforma hibrida)
=====================================================
Complementa o lilo_mcp.py (stdio MCP) expondo as MESMAS tools como
endpoints HTTP/JSON. Permite usar LILO de:
  - cliente HTTP proprio / curl
  - automacao via cron / scheduled tasks
  - integracoes com Notion/Slack/IDE remoto
  - frontend custom (Streamlit, React, etc)

Reaproveita 100% da camada `lilo.handle_tool_call`/`lilo.route` --
a logica de roteamento, fallback, policy engine e cost tracking ja
existente fica unica para CLI, MCP e API.

Endpoints:
  GET  /                           -- Portal HTML (chat embarcado, catalogo)
  GET  /api                        -- Mesmo catalogo em JSON
  GET  /docs                       -- Swagger UI (FastAPI nativo)
  GET  /redoc                      -- ReDoc
  GET  /v1/health                  -- status agentes + backends
  GET  /v1/agents                  -- lista subagentes carregados
  GET  /v1/tools                   -- catalogo MCP-style de tools
  GET  /v1/skills                  -- registry completo (core + geradas)
  POST /v1/skills/run              -- {name, args} -> invoca skill (paridade MCP)
  POST /v1/chat                    -- {query, tab?, context?, session_id?} -> resposta
  POST /v1/tools/call              -- {name, arguments} -> resultado
  POST /v1/chat/stream             -- SSE (streaming token-a-token; aceita session_id)
  GET  /v1/sessions?limit=N        -- lista sessoes multi-turno recentes
  GET  /v1/sessions/{id}           -- historico (turnos) de uma sessao
  DELETE /v1/sessions/{id}         -- apaga sessao (reset de memoria)
  GET  /v1/cost/today              -- resumo de custos
  GET  /v1/cost/recent?limit=N     -- ultimas N requests
  GET  /v1/memory?ns=&tag=         -- listar memoria persistente
  POST /v1/memory                  -- {key, value, namespace?, tags?}
  DELETE /v1/memory/{ns}/{key}     -- remove entrada

Uso:
    pip install fastapi uvicorn sse-starlette
    python lilo_api.py
    # ou
    uvicorn lilo_api:app --host 0.0.0.0 --port 8088 --reload

Autenticacao: token simples via env LILO_API_TOKEN (opcional).
Se LILO_API_TOKEN estiver vazio, a API aceita qualquer requisicao
(modo dev). Em producao, configure o token e passe em
'Authorization: Bearer <token>' ou query '?token=...'.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Any, Optional

LILO_ROOT = Path(__file__).parent
sys.path.insert(0, str(LILO_ROOT))
os.environ.setdefault("PYTHONPATH", str(LILO_ROOT))

# Lazy import-fix: o usuario pode rodar lilo_api.py sem fastapi instalado
try:
    from fastapi import FastAPI, HTTPException, Request, Header
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, HTMLResponse
    from pydantic import BaseModel
except ImportError:
    sys.stderr.write(
        "[LILO API] Falta instalar dependencias. Rode:\n"
        "    pip install fastapi uvicorn sse-starlette\n"
    )
    raise

from shared.utils import load_env, get_env
from shared.logger import get_logger

load_env()
log = get_logger("LiloAPI")

# Carrega lazy para nao impactar inicializacao do server
def _lilo():
    from lilo import handle_tool_call, route, list_all_tools, health_check, _load_agents
    return handle_tool_call, route, list_all_tools, health_check, _load_agents


app = FastAPI(
    title="LILO API",
    version="1.0.0",
    description="API HTTP do LILO -- plataforma hibrida (Ollama + LiteLLM + Claude).",
)

# CORS aberto por default; restrinja em producao via LILO_API_CORS
_cors_origins = get_env("LILO_API_CORS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_TOKEN = get_env("LILO_API_TOKEN", "")


def _check_auth(authorization: Optional[str], token: Optional[str]):
    """Valida token (Bearer header ou query param). No-op se token nao configurado."""
    if not API_TOKEN:
        return
    presented = None
    if authorization and authorization.lower().startswith("bearer "):
        presented = authorization.split(" ", 1)[1].strip()
    if not presented and token:
        presented = token
    if presented != API_TOKEN:
        raise HTTPException(status_code=401, detail="Token invalido")


# ---- Sessoes multi-turno ----------------------------------------------------
# A API e stateless por padrao. Quando o cliente passa `session_id`, damos
# memoria de conversa: carregamos os turnos anteriores (ChatMemory/SQLite),
# injetamos em context["conversation_history"] (que route() prefixa), e ao
# final gravamos o par (user, assistant). Isso aproxima a API HTTP do
# comportamento multi-turno do Claude Desktop, reusando a mesma camada de
# persistencia ja usada pelo dashboard.

def _session_load(req: "ChatRequest"):
    """Prepara o contexto da request. Se `session_id` veio, carrega historico.

    Retorna (context_dict, chat_memory_or_None, session_id_or_None).
    Falhas de persistencia sao fail-soft: a conversa segue stateless.
    """
    ctx = dict(req.context or {})
    sid = (req.session_id or "").strip()
    if not sid:
        return ctx, None, None
    try:
        from shared.chat_memory import ChatMemory
        mem = ChatMemory()
        mem.ensure_chat(sid, title=(req.query[:60] or "Sessao API"),
                        subagent=(req.tab or "api"))
        limit = max(1, min(int(req.history_limit or 20), 100))
        history = mem.get_chat_context(sid, max_messages=limit)
        if history:
            ctx["conversation_history"] = history
        return ctx, mem, sid
    except Exception as e:  # fail-soft: nunca derrubar o chat por causa da sessao
        log.warning("Sessao '%s' indisponivel (%s); seguindo stateless", sid, e)
        return ctx, None, None


def _session_store(mem, sid: Optional[str], user_text: str, assistant_text: str):
    """Grava o turno (user, assistant) na sessao. Fail-soft."""
    if not mem or not sid:
        return
    try:
        mem.add_message(sid, "user", user_text)
        mem.add_message(sid, "assistant", assistant_text)
    except Exception as e:
        log.warning("Falha ao gravar turno na sessao '%s': %s", sid, e)


# ---- Schemas ----------------------------------------------------------------

class ChatRequest(BaseModel):
    query: str
    tab: Optional[str] = None
    context: dict = {}
    # 2026-05-25 (plataforma hibrida): se informado, a API carrega os turnos
    # anteriores desta sessao e os injeta no contexto -> memoria multi-turno
    # estilo Claude Desktop. Omitir = comportamento stateless de antes.
    session_id: Optional[str] = None
    # Quantos turnos anteriores no maximo carregar como contexto (default 20).
    history_limit: int = 20


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict = {}


class SkillRunRequest(BaseModel):
    """Request payload para POST /v1/skills/run.

    Permite invocar qualquer skill registrada (core ou auto-gerada) por nome,
    com paridade ao MCP tool `lilo_run_skill`. Args sao kwargs encaminhados
    a funcao subjacente (numpy/pandas/scipy/etc).
    """
    name: str
    args: dict = {}


class MemorySetRequest(BaseModel):
    key: str
    value: Any
    namespace: str = "default"
    tags: str = ""


class VillaRouteRequest(BaseModel):
    """Request payload para POST /v1/villa/route.

    V10 (2026-05-30): roteamento puro -- retorna a decisao do Villa_Lobos
    (dominio detectado, stages planejados, complexidade, cache hit/miss)
    SEM executar Worker/Reporter. Permite que clientes externos (Claude
    Desktop, n8n, scheduled-tasks Cowork) escolham se executam o pipeline
    completo ou apenas usam a recomendacao.
    """
    task: str
    allow_delegate: bool = True
    iterations: int = 1  # V10.3: usado por /v1/villa/run/stream (execucao real)


# ---- Portal HTML ------------------------------------------------------------

_PORTAL_HTML = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LILO API -- Portal</title>
<style>
:root {
  --bg:#0d1117; --bg2:#161b22; --bg3:#1f2933;
  --fg:#c9d1d9; --fg-dim:#8b949e; --acc:#58a6ff; --acc2:#7ee787;
  --warn:#f0883e; --err:#ff7b72; --border:#30363d;
  --mono: ui-monospace, SFMono-Regular, "JetBrains Mono", Consolas, monospace;
}
* { box-sizing:border-box; margin:0; padding:0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background:var(--bg); color:var(--fg); line-height:1.5; min-height:100vh;
}
header {
  border-bottom:1px solid var(--border); padding:18px 24px;
  display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;
  background:linear-gradient(180deg, var(--bg2) 0%, var(--bg) 100%);
}
.logo { font-size:1.5rem; font-weight:700; color:var(--acc); }
.logo .sub { color:var(--fg-dim); font-weight:400; font-size:0.9rem; margin-left:8px; }
.health-pill {
  font-family:var(--mono); font-size:0.8rem; padding:6px 12px; border-radius:999px;
  background:var(--bg3); border:1px solid var(--border); cursor:pointer;
}
.health-pill.ok { color:var(--acc2); border-color:#2ea04359; }
.health-pill.warn { color:var(--warn); border-color:#f0883e59; }
.health-pill.err { color:var(--err); border-color:#ff7b7259; }
main { max-width:1400px; margin:0 auto; padding:24px; }
h2 { color:var(--fg); margin:24px 0 12px; font-size:1.2rem; font-weight:600;
     border-left:3px solid var(--acc); padding-left:10px; }
h3 { color:var(--fg-dim); font-size:0.95rem; margin:8px 0; font-weight:500; }
p { color:var(--fg-dim); }
.intro { background:var(--bg2); border:1px solid var(--border); border-radius:8px;
         padding:16px; margin-bottom:20px; font-size:0.95rem; }
.intro a { color:var(--acc); }
.grid { display:grid; gap:14px; grid-template-columns:repeat(auto-fill, minmax(380px,1fr)); }
.card {
  background:var(--bg2); border:1px solid var(--border); border-radius:8px;
  padding:14px 16px; transition:border-color 0.2s, transform 0.2s;
}
.card:hover { border-color:var(--acc); transform:translateY(-1px); }
.method {
  display:inline-block; font-family:var(--mono); font-size:0.72rem;
  padding:2px 8px; border-radius:4px; font-weight:700; margin-right:6px;
}
.method.GET { background:#1f6feb33; color:#79c0ff; }
.method.POST { background:#2ea04333; color:var(--acc2); }
.method.DELETE { background:#da363333; color:var(--err); }
.path { font-family:var(--mono); font-size:0.95rem; color:var(--fg); }
.desc { color:var(--fg-dim); font-size:0.9rem; margin:8px 0; }
pre {
  background:var(--bg); border:1px solid var(--border); border-radius:4px;
  padding:8px 10px; font-family:var(--mono); font-size:0.78rem; color:var(--fg);
  overflow-x:auto; white-space:pre-wrap; word-break:break-all;
}
.copy-btn {
  background:transparent; border:1px solid var(--border); color:var(--fg-dim);
  padding:3px 8px; border-radius:4px; font-size:0.72rem; cursor:pointer;
  font-family:var(--mono); margin-top:6px;
}
.copy-btn:hover { color:var(--acc); border-color:var(--acc); }
.try-btn {
  background:var(--acc); color:#0d1117; border:0; padding:5px 14px;
  border-radius:4px; font-size:0.78rem; cursor:pointer; font-weight:600;
  margin-top:6px; margin-right:6px;
}
.try-btn:hover { filter:brightness(1.1); }
.chat-section {
  margin-top:32px; background:var(--bg2); border:1px solid var(--border);
  border-radius:8px; padding:18px;
}
.chat-input-row { display:flex; gap:8px; flex-wrap:wrap; align-items:flex-end; }
.chat-input-row .col { flex:1; min-width:200px; }
.chat-input-row label { color:var(--fg-dim); font-size:0.75rem; display:block; margin-bottom:4px; }
.chat-input-row textarea, .chat-input-row select, .chat-input-row input {
  width:100%; background:var(--bg); border:1px solid var(--border); color:var(--fg);
  padding:8px 10px; border-radius:4px; font-family:inherit; font-size:0.9rem;
}
.chat-input-row textarea { min-height:60px; resize:vertical; font-family:var(--mono); }
.chat-input-row textarea:focus, select:focus, input:focus {
  outline:none; border-color:var(--acc);
}
.chat-output {
  margin-top:14px; background:var(--bg); border:1px solid var(--border);
  border-radius:4px; padding:14px; min-height:180px; max-height:500px;
  overflow-y:auto; font-family:var(--mono); font-size:0.85rem; white-space:pre-wrap;
  color:var(--fg);
}
.chat-output .meta { color:var(--fg-dim); font-size:0.75rem; margin-bottom:6px; }
.chat-output .err { color:var(--err); }
.spinner {
  display:inline-block; width:12px; height:12px; border:2px solid var(--bg3);
  border-top-color:var(--acc); border-radius:50%; animation:spin 0.7s linear infinite;
  vertical-align:middle; margin-right:6px;
}
@keyframes spin { to { transform:rotate(360deg); } }
footer {
  border-top:1px solid var(--border); padding:16px 24px; text-align:center;
  color:var(--fg-dim); font-size:0.8rem; margin-top:40px;
}
.nav-links { display:flex; gap:12px; flex-wrap:wrap; }
.nav-links a {
  color:var(--acc); text-decoration:none; padding:6px 12px;
  border:1px solid var(--border); border-radius:4px; font-size:0.85rem;
}
.nav-links a:hover { background:var(--bg3); }

/* Hero: botoes grandes para abrir UI humana e API */
.hero {
  display:grid; gap:14px; grid-template-columns:repeat(auto-fit, minmax(280px,1fr));
  margin:8px 0 24px;
}
.hero-card {
  display:flex; flex-direction:column; padding:22px 20px; border-radius:10px;
  border:1px solid var(--border); background:var(--bg2);
  text-decoration:none; color:var(--fg); transition:all 0.2s;
  position:relative; overflow:hidden;
}
.hero-card:hover { transform:translateY(-2px); border-color:var(--acc); }
.hero-card.primary {
  background:linear-gradient(135deg, #2ea04322 0%, var(--bg2) 60%);
  border-color:#2ea04359;
}
.hero-card.primary:hover { border-color:var(--acc2); box-shadow:0 4px 16px #2ea04340; }
.hero-card.secondary {
  background:linear-gradient(135deg, #1f6feb22 0%, var(--bg2) 60%);
  border-color:#1f6feb59;
}
.hero-card.secondary:hover { border-color:var(--acc); box-shadow:0 4px 16px #1f6feb40; }
.hero-title {
  font-size:1.25rem; font-weight:700; margin-bottom:4px;
  display:flex; align-items:center; gap:10px; flex-wrap:wrap;
}
.hero-emoji { font-size:1.8rem; }
.hero-desc { color:var(--fg-dim); font-size:0.9rem; line-height:1.4; }
.hero-foot {
  margin-top:12px; display:flex; justify-content:space-between; align-items:center;
  font-family:var(--mono); font-size:0.78rem; color:var(--fg-dim);
}
.hero-status {
  padding:3px 8px; border-radius:999px; background:var(--bg3); border:1px solid var(--border);
}
.hero-status.online { color:var(--acc2); border-color:#2ea04359; background:#2ea04322; }
.hero-status.offline { color:var(--err); border-color:#ff7b7259; background:#ff7b7222; }
.hero-status.checking { color:var(--fg-dim); }
@media (max-width: 700px) {
  .chat-input-row { flex-direction:column; }
  .grid { grid-template-columns:1fr; }
}
</style>
</head>
<body>
<header>
  <div class="logo">LILO API <span class="sub">v__VERSION__</span></div>
  <div class="nav-links">
    <a href="/docs">Swagger UI</a>
    <a href="/redoc">ReDoc</a>
    <span id="health" class="health-pill">checando...</span>
  </div>
</header>

<main>
  <div class="intro">
    <strong>Plataforma hibrida do LILO.</strong>
    Esta API expoe os mesmos subagentes (PRISM, SQL, PDF, Scholar, Villa Lobos, Desktop)
    e as 199+ skills disponiveis via MCP &mdash; mas por HTTP/JSON, para automacao,
    integracao com IDE remoto, scheduled tasks e clientes proprios.
    <br><br>
    Backends LLM: <strong>Ollama local</strong> (gratuito) &rarr; <strong>LiteLLM proxy</strong>
    (porta 4000) &rarr; <strong>Anthropic Claude</strong> (4.5 sonnet/opus/haiku).
    Roteamento e fallback automaticos pelo Policy Engine.
  </div>

  <div class="hero">
    <a href="http://localhost:8100" target="_blank" rel="noopener"
       class="hero-card primary" id="hero-streamlit">
      <div class="hero-title">
        <span class="hero-emoji">&#129302;</span>
        <span>Abrir LILO modo AGENTE IA</span>
      </div>
      <div class="hero-desc">
        Interface humana completa em Streamlit: chat com sub-agentes, slash commands
        (<code>/lilo_chat</code>, <code>/prism_analyze</code>...), upload de arquivos,
        historico de conversas, painel de skills, busca web. <strong>Use isto para
        trabalho do dia a dia.</strong>
      </div>
      <div class="hero-foot">
        <span>http://localhost:8100</span>
        <span class="hero-status checking" id="streamlit-status">checando...</span>
      </div>
    </a>

    <a href="/docs" class="hero-card secondary">
      <div class="hero-title">
        <span class="hero-emoji">&#128296;</span>
        <span>API tecnica (Swagger)</span>
      </div>
      <div class="hero-desc">
        Para automacao, scripts, integracao com clientes externos. Swagger UI permite
        testar cada endpoint pelo navegador. Endpoints listados abaixo aceitam
        <code>curl</code>, <code>requests</code>, <code>fetch</code>, etc.
      </div>
      <div class="hero-foot">
        <span>/docs (Swagger) &middot; /redoc</span>
        <span class="hero-status online">esta API</span>
      </div>
    </a>
  </div>

  <h2>Endpoints disponiveis</h2>
  <div class="grid" id="endpoints"></div>

  <div class="chat-section">
    <h2 style="border:0; padding:0; margin:0 0 12px;">Chat -- testar agora</h2>
    <p style="margin-bottom:12px; font-size:0.9rem;">
      Envia diretamente para <code style="font-family:var(--mono); color:var(--acc2);">POST /v1/chat</code>.
      Use o seletor de subagente para forcar roteamento; deixe em "auto" para deteccao por keywords.
      Atalho: <kbd>Ctrl</kbd>+<kbd>Enter</kbd> envia.
    </p>
    <div class="chat-input-row">
      <div class="col" style="flex:3;">
        <label>Pergunta / comando</label>
        <textarea id="chat-query"
          placeholder="Ex: liste as tabelas disponiveis no banco de exemplo"></textarea>
      </div>
      <div class="col" style="flex:0 0 160px;">
        <label>Subagente</label>
        <select id="chat-tab">
          <option value="">auto (detecta)</option>
          <option value="villa">villa (orquestrador)</option>
          <option value="prism">prism (estatistica)</option>
          <option value="sql">sql</option>
          <option value="pdf">pdf</option>
          <option value="scholar">scholar</option>
          <option value="gateway">gateway (chat livre)</option>
          <option value="desktop">desktop (fs/shell)</option>
        </select>
      </div>
      <div class="col" style="flex:0 0 100px;">
        <label>Modo</label>
        <select id="chat-mode">
          <option value="json">/v1/chat</option>
          <option value="stream">/v1/chat/stream (SSE)</option>
        </select>
      </div>
      <div class="col" style="flex:0 0 auto;">
        <label>&nbsp;</label>
        <button class="try-btn" id="chat-send">Enviar</button>
        <button class="copy-btn" id="chat-clear">limpar</button>
      </div>
    </div>
    <div class="chat-output" id="chat-out">
<span class="meta">// Resposta aparecera aqui. Streaming SSE mostra tokens conforme chegam.</span>
    </div>
  </div>
</main>

<footer>
  LILO API &middot; servidor local &middot; configurar token via <code style="font-family:var(--mono);">LILO_API_TOKEN</code>
  &middot; CORS via <code style="font-family:var(--mono);">LILO_API_CORS</code>
</footer>

<script>
const ENDPOINTS = [
  {m:"GET",  p:"/v1/health", desc:"Status dos subagentes carregados e backend LLM ativo (ollama / litellm / anthropic / mock).",
    curl:`curl http://localhost:8088/v1/health`},
  {m:"GET",  p:"/v1/agents", desc:"Lista subagentes carregados com nome e descricao curta.",
    curl:`curl http://localhost:8088/v1/agents`},
  {m:"GET",  p:"/v1/tools", desc:"Catalogo MCP-style de todas as tools (subagentes + skills geradas + memoria + cost).",
    curl:`curl http://localhost:8088/v1/tools`},
  {m:"GET",  p:"/v1/skills", desc:"Registry completo: 16 skills CORE + 199 funcoes geradas (scipy, numpy, pandas, etc).",
    curl:`curl http://localhost:8088/v1/skills`},
  {m:"POST", p:"/v1/skills/run", desc:"Invoca skill por nome (paridade com MCP lilo_run_skill). Body: {name, args}.",
    curl:`curl -X POST http://localhost:8088/v1/skills/run \\
  -H "Content-Type: application/json" \\
  -d '{"name":"numpy.mean","args":{"a":[1,2,3,4]}}'`},
  {m:"POST", p:"/v1/chat", desc:"Endpoint principal. Body: {query, tab?, context?, session_id?}. Com session_id a API mantem memoria multi-turno (estilo Claude Desktop); sem ele e stateless.",
    curl:`curl -X POST http://localhost:8088/v1/chat \\
  -H "Content-Type: application/json" \\
  -d '{"query":"e o trypanothione?","tab":"scholar","session_id":"sessao-bio-1"}'`},
  {m:"POST", p:"/v1/chat/stream", desc:"Streaming SSE: emite event=token a cada chunk + event=done.",
    curl:`curl -N -X POST http://localhost:8088/v1/chat/stream \\
  -H "Content-Type: application/json" \\
  -d '{"query":"resumir artigo X.pdf","tab":"pdf"}'`},
  {m:"POST", p:"/v1/tools/call", desc:"Invoca tool MCP por nome. Body: {name, arguments}. Atalho para skills especificas.",
    curl:`curl -X POST http://localhost:8088/v1/tools/call \\
  -H "Content-Type: application/json" \\
  -d '{"name":"prism_classify","arguments":{"file_path":"data/exp1.xlsx"}}'`},
  {m:"GET",  p:"/v1/sessions?limit=20", desc:"Lista sessoes multi-turno recentes (id, titulo, subagente, timestamps).",
    curl:`curl "http://localhost:8088/v1/sessions?limit=20"`},
  {m:"GET",  p:"/v1/sessions/{id}", desc:"Historico (turnos user/assistant) de uma sessao multi-turno.",
    curl:`curl http://localhost:8088/v1/sessions/sessao-bio-1`},
  {m:"DELETE", p:"/v1/sessions/{id}", desc:"Apaga uma sessao e suas mensagens (reset de memoria multi-turno).",
    curl:`curl -X DELETE http://localhost:8088/v1/sessions/sessao-bio-1`},
  {m:"GET",  p:"/v1/cost/today", desc:"Resumo de uso do dia (requests, tokens, cost USD por backend e por subagente).",
    curl:`curl http://localhost:8088/v1/cost/today`},
  {m:"GET",  p:"/v1/cost/recent?limit=20", desc:"Ultimas N requests com modelo, custo, duracao e preview da query.",
    curl:`curl "http://localhost:8088/v1/cost/recent?limit=20"`},
  {m:"GET",  p:"/v1/memory?ns=&tag=", desc:"Lista memoria persistente (KV SQLite). Filtros opcionais por namespace e tag.",
    curl:`curl "http://localhost:8088/v1/memory?ns=user"`},
  {m:"POST", p:"/v1/memory", desc:"Salva entrada KV. Body: {key, value, namespace?, tags?}. value pode ser string ou objeto JSON.",
    curl:`curl -X POST http://localhost:8088/v1/memory \\
  -H "Content-Type: application/json" \\
  -d '{"key":"preferred_model","value":"claude-sonnet-4-5","namespace":"user"}'`},
  {m:"GET",  p:"/v1/memory/{ns}/{key}", desc:"Le entrada especifica. 404 se nao existir.",
    curl:`curl http://localhost:8088/v1/memory/user/preferred_model`},
  {m:"DELETE", p:"/v1/memory/{ns}/{key}", desc:"Remove entrada da memoria persistente.",
    curl:`curl -X DELETE http://localhost:8088/v1/memory/user/preferred_model`},
];

// Sessao do portal: id estavel por aba -> o chat embutido tem memoria
// multi-turno (estilo Claude Desktop). "limpar" tambem gera nova sessao.
let SESSION_ID = "portal-" + Math.random().toString(36).slice(2, 10);

function escapeHTML(s) {
  return String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
}

function renderEndpoints() {
  const grid = document.getElementById("endpoints");
  grid.innerHTML = ENDPOINTS.map(e => `
    <div class="card">
      <div><span class="method ${e.m}">${e.m}</span><span class="path">${escapeHTML(e.p)}</span></div>
      <div class="desc">${escapeHTML(e.desc)}</div>
      <pre>${escapeHTML(e.curl)}</pre>
      <button class="copy-btn" data-curl="${escapeHTML(e.curl).replace(/"/g,'&quot;')}">Copiar curl</button>
      ${e.m==="GET" && !e.p.includes("{") ? `<button class="try-btn" data-get="${e.p}">Testar GET</button>` : ""}
    </div>
  `).join("");

  document.querySelectorAll(".copy-btn[data-curl]").forEach(b => {
    b.onclick = () => {
      const txt = b.dataset.curl.replace(/&quot;/g,'"');
      navigator.clipboard.writeText(txt);
      const orig = b.textContent;
      b.textContent = "OK!"; setTimeout(()=>b.textContent=orig, 1200);
    };
  });
  document.querySelectorAll(".try-btn[data-get]").forEach(b => {
    b.onclick = async () => {
      const path = b.dataset.get;
      const out = document.getElementById("chat-out");
      out.innerHTML = `<span class="meta">// GET ${escapeHTML(path)}</span>\n<span class="spinner"></span> aguardando...`;
      try {
        const r = await fetch(path);
        const txt = await r.text();
        let pretty = txt;
        try { pretty = JSON.stringify(JSON.parse(txt), null, 2); } catch {}
        out.innerHTML = `<span class="meta">// GET ${escapeHTML(path)} -- HTTP ${r.status}</span>\n${escapeHTML(pretty)}`;
      } catch (e) {
        out.innerHTML = `<span class="err">erro: ${escapeHTML(String(e))}</span>`;
      }
    };
  });
}

async function checkHealth() {
  const pill = document.getElementById("health");
  pill.textContent = "checando...";
  pill.className = "health-pill";
  try {
    const r = await fetch("/v1/health");
    if (!r.ok) throw new Error("HTTP " + r.status);
    const j = await r.json();
    const detailStr = (typeof j.detail === "string") ? j.detail : JSON.stringify(j.detail || "");
    const m = detailStr.match(/backend[\"\s:]+([\w]+)/i);
    const backend = m ? m[1] : "ok";
    pill.textContent = "backend: " + backend;
    pill.className = "health-pill " + (backend === "mock" ? "warn" : "ok");
  } catch (e) {
    pill.textContent = "offline";
    pill.className = "health-pill err";
  }
}

async function checkStreamlit() {
  // O Streamlit em :8100 nao expoe CORS, entao um fetch normal sempre falha
  // por CORS independente do servidor estar UP. Truque: usar mode:"no-cors"
  // -- a request e disparada e a Promise resolve mesmo sem ler o body.
  // Se houver TypeError "Failed to fetch" -> servidor offline.
  // Se resolver (mesmo com response opaque) -> servidor ON.
  const status = document.getElementById("streamlit-status");
  if (!status) return;
  status.textContent = "checando...";
  status.className = "hero-status checking";
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 1500);
    await fetch("http://localhost:8100/_stcore/health", {
      mode: "no-cors", cache: "no-store", signal: ctrl.signal,
    });
    clearTimeout(timer);
    status.textContent = "ONLINE";
    status.className = "hero-status online";
  } catch (e) {
    status.textContent = "offline -- rode START_LILO_WINDOWS.bat";
    status.className = "hero-status offline";
  }
}

async function sendChat() {
  const q = document.getElementById("chat-query").value.trim();
  const tab = document.getElementById("chat-tab").value;
  const mode = document.getElementById("chat-mode").value;
  const out = document.getElementById("chat-out");
  if (!q) { out.innerHTML = `<span class="err">// digite uma pergunta primeiro</span>`; return; }

  const body = {query: q, session_id: SESSION_ID};
  if (tab) body.tab = tab;
  out.innerHTML = `<span class="meta">// POST ${mode==="stream"?"/v1/chat/stream":"/v1/chat"}  tab=${tab||"auto"}  session=${SESSION_ID}</span>\n<span class="spinner"></span> processando...`;

  if (mode === "stream") {
    try {
      const r = await fetch("/v1/chat/stream", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify(body),
      });
      if (!r.ok) { out.innerHTML += `\n<span class="err">HTTP ${r.status}</span>`; return; }
      out.innerHTML = `<span class="meta">// streaming...</span>\n`;
      const reader = r.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        buf += dec.decode(value, {stream:true});
        const blocks = buf.split("\n\n");
        buf = blocks.pop();
        for (const block of blocks) {
          let event = "message", data = "";
          for (const line of block.split("\n")) {
            if (line.startsWith("event:")) event = line.slice(6).trim();
            else if (line.startsWith("data:")) data += line.slice(5).trim() + "\n";
          }
          data = data.replace(/\n$/, "");
          if (event === "token") out.textContent += data;
          else if (event === "done") out.innerHTML += `\n<span class="meta">// done</span>`;
          else if (event === "error") out.innerHTML += `\n<span class="err">// erro: ${escapeHTML(data)}</span>`;
        }
        out.scrollTop = out.scrollHeight;
      }
    } catch (e) {
      out.innerHTML = `<span class="err">erro: ${escapeHTML(String(e))}</span>`;
    }
  } else {
    try {
      const r = await fetch("/v1/chat", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify(body),
      });
      const j = await r.json().catch(() => null);
      if (!r.ok) {
        out.innerHTML = `<span class="err">// HTTP ${r.status}</span>\n${escapeHTML(j?.detail || "")}`;
        return;
      }
      out.innerHTML = `<span class="meta">// HTTP 200 -- /v1/chat</span>\n${escapeHTML(j.response || JSON.stringify(j, null, 2))}`;
    } catch (e) {
      out.innerHTML = `<span class="err">erro: ${escapeHTML(String(e))}</span>`;
    }
  }
}

document.getElementById("chat-send").onclick = sendChat;
document.getElementById("chat-clear").onclick = () => {
  SESSION_ID = "portal-" + Math.random().toString(36).slice(2, 10);
  document.getElementById("chat-out").innerHTML = `<span class="meta">// limpo -- nova sessao ${SESSION_ID}</span>`;
  document.getElementById("chat-query").value = "";
};
document.getElementById("chat-query").addEventListener("keydown", e => {
  if (e.ctrlKey && e.key === "Enter") { e.preventDefault(); sendChat(); }
});
document.getElementById("health").onclick = checkHealth;

renderEndpoints();
checkHealth();
checkStreamlit();
setInterval(checkHealth, 30000);
setInterval(checkStreamlit, 30000);
</script>
</body>
</html>
"""


# ---- Endpoints --------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def root():
    """Portal HTML com chat embarcado, catalogo de endpoints e health pill."""
    return _PORTAL_HTML.replace("__VERSION__", app.version)


@app.get("/api", response_class=JSONResponse)
def api_root():
    """Catalogo JSON dos endpoints (versao programatica do portal). Util para
    clientes que esperam JSON na raiz, mantendo o portal HTML em /."""
    return {
        "service": "LILO API",
        "version": app.version,
        "endpoints": [
            "/v1/health", "/v1/agents", "/v1/tools", "/v1/skills",
            "/v1/chat", "/v1/tools/call", "/v1/chat/stream",
            "/v1/cost/today", "/v1/cost/recent",
            "/v1/memory (GET POST)", "/v1/memory/{ns}/{key} (DELETE GET)",
        ],
        "portal_html": "/",
        "swagger_ui": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
def health_public():
    """Semaforo verde/vermelho sem auth -- para load balancers e Streamlit.

    Fase A (2026-05-14): /health publico minimo. Detalhe completo continua
    em /v1/health (autenticado).
    """
    try:
        _, _, _, health_check, _ = _lilo()
        _ = health_check()  # exercise subagent loading
        return {"status": "ok", "service": "lilo"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "service": "lilo", "error": str(e)},
        )


@app.get("/v1/health")
def health(authorization: Optional[str] = Header(None), token: Optional[str] = None):
    _check_auth(authorization, token)
    _, _, _, health_check, _ = _lilo()
    return {"status": "ok", "detail": health_check()}


@app.get("/v1/agents")
def agents(authorization: Optional[str] = Header(None), token: Optional[str] = None):
    _check_auth(authorization, token)
    _, _, _, _, _load_agents = _lilo()
    loaded = _load_agents()
    return {"agents": [
        {"name": n, "description": getattr(a, "description", "")}
        for n, a in loaded.items()
    ]}


@app.get("/v1/tools")
def tools(authorization: Optional[str] = Header(None), token: Optional[str] = None):
    _check_auth(authorization, token)
    _, _, list_all_tools, _, _ = _lilo()
    return {"tools": list_all_tools()}


@app.get("/v1/skills")
def skills(authorization: Optional[str] = Header(None), token: Optional[str] = None):
    _check_auth(authorization, token)
    try:
        from lilo_skills import get_full_registry
        return get_full_registry()
    except Exception as e:
        raise HTTPException(500, f"Erro ao carregar skills: {e}")


@app.post("/v1/skills/run")
def skills_run(req: SkillRunRequest,
               authorization: Optional[str] = Header(None),
               token: Optional[str] = None):
    """Invoca uma skill por nome (paridade com MCP `lilo_run_skill`).

    Body: {"name": "<skill>", "args": {...}}
    Retorna: {"ok": bool, "skill": str, "result": Any, "duration_ms": int}.
    """
    _check_auth(authorization, token)
    handle_tool_call, _, _, _, _ = _lilo()
    import time as _time
    t0 = _time.time()
    try:
        # Reusa o handler MCP para garantir paridade.
        result = handle_tool_call("lilo_run_skill",
                                  {"name": req.name, "args": req.args or {}})
        return {
            "ok": True,
            "skill": req.name,
            "result": result,
            "duration_ms": int((_time.time() - t0) * 1000),
        }
    except Exception as e:
        log.exception("Erro em /v1/skills/run skill=%s", req.name)
        raise HTTPException(500, f"Skill '{req.name}' falhou: {e}")


@app.post("/v1/chat")
def chat(req: ChatRequest, authorization: Optional[str] = Header(None), token: Optional[str] = None):
    _check_auth(authorization, token)
    _, route, _, _, _ = _lilo()
    ctx, mem, sid = _session_load(req)
    try:
        result = route(req.query, tab=req.tab, context=ctx)
        _session_store(mem, sid, req.query, result)
        out = {"response": result}
        if sid:
            out["session_id"] = sid
        return out
    except Exception as e:
        log.exception("Erro em /v1/chat")
        raise HTTPException(500, str(e))


@app.post("/v1/tools/call")
def call_tool(req: ToolCallRequest, authorization: Optional[str] = Header(None), token: Optional[str] = None):
    _check_auth(authorization, token)
    handle_tool_call, _, _, _, _ = _lilo()
    try:
        result = handle_tool_call(req.name, req.arguments or {})
        return {"result": result}
    except Exception as e:
        log.exception("Erro em /v1/tools/call")
        raise HTTPException(500, str(e))


@app.post("/v1/villa/route")
def villa_route(req: VillaRouteRequest, authorization: Optional[str] = Header(None), token: Optional[str] = None):
    """V10 (2026-05-30): retorna decisao de roteamento do Villa_Lobos
    SEM executar o pipeline. Espelha a tool MCP `villa_route`.

    Resposta:
        {
          "decision": {"complexity","needs_planning","needs_reader","needs_worker",
                       "iterations","skip_to_reporter","reasoning","_source"},
          "domain_heuristic": "<dominio>|null",
          "stages_planned": ["orchestrator","planner",...,"reporter"],
          "cache": {"hits","misses","size","max","hit_ratio"},
          "delegate": {"agent","route_method"} | null
        }
    """
    _check_auth(authorization, token)
    try:
        from agents.villa_lobos.agent import VillaLobosAgent
        v = VillaLobosAgent()
        info = v.explain_routing(req.task, allow_delegate=req.allow_delegate)
        return info
    except Exception as e:
        log.exception("Erro em /v1/villa/route")
        raise HTTPException(500, str(e))


@app.get("/v1/villa/route")
def villa_route_get(task: str, allow_delegate: bool = True,
                    authorization: Optional[str] = Header(None),
                    token: Optional[str] = None):
    """Variante GET de /v1/villa/route -- comoda para curl/testes:
        curl 'http://localhost:8000/v1/villa/route?task=compare+groups+anova'
    """
    _check_auth(authorization, token)
    try:
        from agents.villa_lobos.agent import VillaLobosAgent
        v = VillaLobosAgent()
        return v.explain_routing(task, allow_delegate=allow_delegate)
    except Exception as e:
        log.exception("Erro em /v1/villa/route (GET)")
        raise HTTPException(500, str(e))


@app.get("/v1/villa/capabilities")
def villa_capabilities(authorization: Optional[str] = Header(None), token: Optional[str] = None):
    """V10.3 (2026-05-31): manifesto unificado de capacidades de todos os
    subagentes (proposta secao 6). Consumido pela UI do dashboard e por
    roteadores externos. Cada entrada traz domain/keywords/tools/cost_hint/
    latency_hint/inputs/outputs.

    Resposta: {"agents": {<name>: <capabilities>}, "count": N}
    """
    _check_auth(authorization, token)
    try:
        from agents.villa_lobos.agent import VillaLobosAgent
        reg = VillaLobosAgent().capability_registry()
        return {"agents": reg, "count": len(reg)}
    except Exception as e:
        log.exception("Erro em /v1/villa/capabilities")
        raise HTTPException(500, str(e))


@app.post("/v1/villa/run/stream")
async def villa_run_stream(req: VillaRouteRequest, authorization: Optional[str] = Header(None), token: Optional[str] = None):
    """V10.3 (2026-05-31): executa o pipeline Villa_Lobos emitindo eventos
    SSE por stage (streaming entre stages, proposta secao 6). Diferente de
    /v1/chat/stream (que faz chunking artificial do texto final), aqui cada
    stage do pipeline emite um evento assim que conclui -- reduz o wall-clock
    percebido em iterations>=2 e da observabilidade ao cliente.

    Eventos: event=stage (data=JSON {stage,status,ms,preview}) e event=done
    (data=resultado final) | event=error.
    """
    _check_auth(authorization, token)
    try:
        from sse_starlette.sse import EventSourceResponse
    except ImportError:
        raise HTTPException(500, "sse-starlette nao instalado. pip install sse-starlette")
    import queue as _queue
    from agents.villa_lobos.agent import VillaLobosAgent
    loop = asyncio.get_event_loop()
    q: "_queue.Queue" = _queue.Queue()

    def _emit(stage, status, ms=None, preview=None):
        q.put({"stage": stage, "status": status, "ms": ms, "preview": preview})

    def _work():
        agent = VillaLobosAgent()
        ctx = {"iterations": int(getattr(req, "iterations", 1) or 1),
               "allow_delegate": req.allow_delegate, "stream_callback": _emit}
        try:
            result = agent.run(req.task, context=ctx)
            q.put({"__final__": result})
        except Exception as e:  # noqa: BLE001
            q.put({"__error__": str(e)})

    async def gen():
        fut = loop.run_in_executor(None, _work)
        while True:
            try:
                item = await loop.run_in_executor(None, lambda: q.get(timeout=0.25))
            except Exception:
                if fut.done() and q.empty():
                    break
                continue
            if "__final__" in item:
                yield {"event": "done", "data": item["__final__"]}
                break
            if "__error__" in item:
                yield {"event": "error", "data": item["__error__"]}
                break
            yield {"event": "stage", "data": json.dumps(item, ensure_ascii=False)}

    return EventSourceResponse(gen())


@app.post("/v1/chat/stream")
async def chat_stream(req: ChatRequest, authorization: Optional[str] = Header(None), token: Optional[str] = None):
    """SSE streaming: emite chunks de texto com event=token + done.
    Implementacao atual: chama route() em thread e emite o resultado em
    pedacos de ~100 chars. Quando o LLMClient suportar streaming nativo,
    refazer este endpoint sem chunking artificial."""
    _check_auth(authorization, token)
    try:
        from sse_starlette.sse import EventSourceResponse
    except ImportError:
        raise HTTPException(500, "sse-starlette nao instalado. pip install sse-starlette")

    _, route, _, _, _ = _lilo()
    loop = asyncio.get_event_loop()
    ctx, mem, sid = _session_load(req)

    async def gen():
        try:
            text = await loop.run_in_executor(
                None, lambda: route(req.query, tab=req.tab, context=ctx)
            )
            _session_store(mem, sid, req.query, text)
            for i in range(0, len(text), 100):
                yield {"event": "token", "data": text[i:i+100]}
                await asyncio.sleep(0.005)
            yield {"event": "done", "data": sid or ""}
        except Exception as e:
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(gen())


# ---- Cost tracking ----------------------------------------------------------

@app.get("/v1/cost/today")
def cost_today(date: str = "", authorization: Optional[str] = Header(None), token: Optional[str] = None):
    _check_auth(authorization, token)
    from shared.cost_tracker import get_tracker
    return get_tracker().daily_summary(target_date=date or None)


@app.get("/v1/cost/recent")
def cost_recent(limit: int = 20, authorization: Optional[str] = Header(None), token: Optional[str] = None):
    _check_auth(authorization, token)
    from shared.cost_tracker import get_tracker
    limit = max(1, min(int(limit), 200))
    return {"requests": get_tracker().recent_requests(limit=limit)}


# ---- Memoria persistente ----------------------------------------------------

@app.get("/v1/memory")
def memory_list(ns: str = "", tag: str = "",
                authorization: Optional[str] = Header(None), token: Optional[str] = None):
    _check_auth(authorization, token)
    from shared.kv_memory import get_memory
    return {"entries": get_memory().list(ns=ns or None, tag=tag or None)}


@app.post("/v1/memory")
def memory_set(req: MemorySetRequest,
               authorization: Optional[str] = Header(None), token: Optional[str] = None):
    _check_auth(authorization, token)
    from shared.kv_memory import get_memory
    val = req.value if isinstance(req.value, str) else json.dumps(req.value, ensure_ascii=False, default=str)
    get_memory().set(req.key, val, ns=req.namespace, tags=req.tags)
    return {"ok": True, "namespace": req.namespace, "key": req.key}


@app.get("/v1/memory/{ns}/{key}")
def memory_get(ns: str, key: str,
               authorization: Optional[str] = Header(None), token: Optional[str] = None):
    _check_auth(authorization, token)
    from shared.kv_memory import get_memory
    val = get_memory().get(key, ns=ns, default=None)
    if val is None:
        raise HTTPException(404, f"{ns}/{key} nao encontrado")
    return {"namespace": ns, "key": key, "value": val}


@app.delete("/v1/memory/{ns}/{key}")
def memory_delete(ns: str, key: str,
                  authorization: Optional[str] = Header(None), token: Optional[str] = None):
    _check_auth(authorization, token)
    from shared.kv_memory import get_memory
    ok = get_memory().delete(key, ns=ns)
    if not ok:
        raise HTTPException(404, f"{ns}/{key} nao encontrado")
    return {"ok": True}


# ---- Sessoes multi-turno (chat memory) --------------------------------------

@app.get("/v1/sessions")
def list_sessions(limit: int = 20, project_id: Optional[str] = None,
                  authorization: Optional[str] = Header(None), token: Optional[str] = None):
    """Lista sessoes de chat multi-turno (titulo, subagente, timestamps)."""
    _check_auth(authorization, token)
    try:
        from shared.chat_memory import get_memory
        cm = get_memory()
    except Exception:
        from shared.chat_memory import ChatMemory
        cm = ChatMemory()
    try:
        items = cm.list_chats(project_id=project_id, limit=int(limit))
        return {"sessions": items}
    except Exception as e:
        log.exception("Erro em /v1/sessions")
        raise HTTPException(500, str(e))


@app.get("/v1/sessions/{session_id}")
def get_session(session_id: str,
                authorization: Optional[str] = Header(None), token: Optional[str] = None):
    """Retorna historico (turnos user/assistant) de uma sessao."""
    _check_auth(authorization, token)
    try:
        from shared.chat_memory import get_memory
        cm = get_memory()
    except Exception:
        from shared.chat_memory import ChatMemory
        cm = ChatMemory()
    try:
        msgs = cm.get_messages(session_id)
        return {"session_id": session_id, "messages": msgs}
    except Exception as e:
        log.exception("Erro em /v1/sessions/{id}")
        raise HTTPException(500, str(e))


@app.delete("/v1/sessions/{session_id}")
def delete_session(session_id: str,
                   authorization: Optional[str] = Header(None), token: Optional[str] = None):
    """Apaga uma sessao e suas mensagens (reset de memoria multi-turno)."""
    _check_auth(authorization, token)
    try:
        from shared.chat_memory import get_memory
        cm = get_memory()
    except Exception:
        from shared.chat_memory import ChatMemory
        cm = ChatMemory()
    try:
        ok = cm.delete_chat(session_id)
        return {"ok": bool(ok), "session_id": session_id}
    except Exception as e:
        log.exception("Erro em DELETE /v1/sessions/{id}")
        raise HTTPException(500, str(e))


# ---- Entrypoint -------------------------------------------------------------

if __name__ == "__main__":
    try:
        import uvicorn
    except ImportError:
        sys.stderr.write("Falta uvicorn. Rode: pip install uvicorn\n")
        sys.exit(1)
    host = get_env("LILO_API_HOST", "127.0.0.1")
    port = int(get_env("LILO_API_PORT", "8088"))
    log.info("Subindo LILO API em %s:%d (token=%s)",
             host, port, "configurado" if API_TOKEN else "DEV (sem auth)")
    uvicorn.run(app, host=host, port=port, log_level="info")
