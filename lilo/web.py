"""`lilo web` (v13.7) — o chat no NAVEGADOR, sem repetir o erro do v12.

O v12 tinha Streamlit + API + 5 entry points e zero tool-calling. Aqui e um
SUBCOMANDO do mesmo binario (precedente do mcp-serve), stdlib pura
(http.server), servindo o MESMO loop (`agente.executar_tarefa`) atras do
MESMO choke-point/portao — inclusive a confirmacao pausa-no-ponto, que vira
botoes [Sim] [Nao] [Sempre] na pagina (a thread da tarefa BLOQUEIA num
threading.Event ate o clique; sem resposta em 15 min, vale "n").

Seguranca do escopo: escuta SO em 127.0.0.1, sem auth (maquina do dono),
UMA tarefa por vez. A conversa persiste no MESMO SQLite das sessoes do
terminal — o que comecou no navegador retoma com `lilo -c <id>`.
"""
from __future__ import annotations

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from lilo import __version__, agente, config
from lilo.cliente import ClienteOllama
from lilo.log import get_logger
from lilo.portao import MODOS

log = get_logger("web")

CONFIRM_TIMEOUT_S = 900  # navegador fechado no meio: 15 min e vale "n"


class UIWeb(agente.UI):
    """Callbacks do loop para o navegador: eventos numa lista (o JS faz
    polling) e confirmacao que BLOQUEIA a thread da tarefa ate o botao."""

    def __init__(self, estado: "EstadoWeb"):
        self.estado = estado

    def tool_inicio(self, nome: str, preview: str) -> None:
        self.estado.historico.append(
            {"t": "tool", "texto": preview.splitlines()[0][:160]})

    def tool_fim(self, nome: str, resultado: str) -> None:
        primeira = (resultado.splitlines() or [""])[0]
        if resultado.startswith(("[ERRO]", "[NEGADO]", "[BLOQUEADO]")):
            self.estado.historico.append({"t": "erro", "texto": primeira[:200]})

    def apos_iteracao(self, msgs: list[dict]) -> None:
        self.estado.sessao.persistir(msgs)

    def confirmar(self, kind: str, preview: str) -> str:
        e = self.estado
        e.evento_confirm.clear()
        e.resposta_confirm = ""
        e.pendente = {"kind": kind, "preview": preview[:1200]}
        ok = e.evento_confirm.wait(CONFIRM_TIMEOUT_S)
        e.pendente = None
        resp = (e.resposta_confirm or "n") if ok else "n"
        e.historico.append({"t": "confirm", "texto": "%s -> %s" % (
            kind, {"s": "sim", "t": "sempre nesta sessao"}.get(resp, "nao"))})
        return resp


class EstadoWeb:
    """Estado do servidor: UMA sessao (a mesma classe do terminal), uma
    tarefa por vez, historico renderizavel e a pendencia de confirmacao."""

    def __init__(self, cliente: ClienteOllama | None = None):
        from lilo.cli import Sessao  # mesma sessao/persistencia do terminal
        self.cliente = cliente or ClienteOllama()
        self.sessao = Sessao()
        self.historico: list[dict] = []
        self.rodando = False
        self.pendente: dict | None = None
        self.evento_confirm = threading.Event()
        self.resposta_confirm = ""
        self._lock = threading.Lock()

    def iniciar_tarefa(self, tarefa: str) -> bool:
        with self._lock:
            if self.rodando:
                return False
            self.rodando = True
        self.historico.append({"t": "user", "texto": tarefa})
        threading.Thread(target=self._rodar, args=(tarefa,), daemon=True).start()
        return True

    def _rodar(self, tarefa: str) -> None:
        try:
            resposta = self.sessao.rodar(tarefa, UIWeb(self), self.cliente)
            self.historico.append({"t": "lilo", "texto": resposta})
            if self.sessao.perms.modo == "plan" and self.sessao.perms.plano:
                self.historico.append(
                    {"t": "erro", "texto": "(%d acoes anotadas no plano — "
                     "aprove trocando o modo p/ accept_edits e pedindo "
                     '"execute o plano")' % len(self.sessao.perms.plano)})
        except Exception as e:  # noqa: BLE001 — erro de turno vira mensagem
            log.warning("tarefa web falhou: %s", e)
            msg = "[ERRO] %s: %s" % (type(e).__name__, e)
            if not self.cliente.ping():
                msg += " — o Ollama parece OFFLINE em %s" % config.ollama_host()
            self.historico.append({"t": "erro", "texto": msg})
        finally:
            self.rodando = False

    def status(self) -> dict:
        return {"historico": self.historico, "rodando": self.rodando,
                "pendente": self.pendente}

    def info(self) -> dict:
        return {"versao": __version__,
                "modelo": self.sessao.modelo or config.modelo(),
                "modo": self.sessao.perms.modo,
                "ollama": self.cliente.ping(),
                "sessao": self.sessao.chat_id or ""}


class _Handler(BaseHTTPRequestHandler):
    estado: EstadoWeb  # injetado pela subclasse criada em criar_servidor

    def log_message(self, fmt, *args):  # polling de 1s: sem spam no console
        if config.debug():
            log.info("http %s", fmt % args)

    def _json(self, obj: dict, code: int = 200) -> None:
        corpo = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _corpo(self) -> dict:
        try:
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}")
        except (ValueError, OSError):
            return {}

    def do_GET(self):  # noqa: N802 — nome exigido pelo http.server
        if self.path in ("/", "/index.html"):
            corpo = PAGINA.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
        elif self.path == "/api/status":
            self._json(self.estado.status())
        elif self.path == "/api/info":
            self._json(self.estado.info())
        else:
            self._json({"erro": "rota desconhecida"}, 404)

    def do_POST(self):  # noqa: N802
        e, corpo = self.estado, self._corpo()
        if self.path == "/api/tarefa":
            tarefa = str(corpo.get("tarefa") or "").strip()
            if not tarefa:
                self._json({"erro": "tarefa vazia"}, 400)
            elif e.iniciar_tarefa(tarefa):
                self._json({"ok": True})
            else:
                self._json({"erro": "ja ha uma tarefa rodando"}, 409)
        elif self.path == "/api/confirmar":
            r = str(corpo.get("resposta") or "").strip().lower()[:1]
            if e.pendente is None:
                self._json({"erro": "nada pendente"}, 409)
            elif r not in ("s", "n", "t"):
                self._json({"erro": "resposta deve ser s, n ou t"}, 400)
            else:
                e.resposta_confirm = r
                e.evento_confirm.set()
                self._json({"ok": True})
        elif self.path == "/api/modo":
            modo = str(corpo.get("modo") or "").strip().lower()
            if e.sessao.perms.trocar_modo(modo):
                self._json({"ok": True, "modo": modo})
            else:
                self._json({"erro": "modos: %s" % ", ".join(MODOS)}, 400)
        elif self.path == "/api/nova":
            if e.rodando:
                self._json({"erro": "aguarde a tarefa atual"}, 409)
            else:
                e.sessao.__init__()
                e.historico = []
                self._json({"ok": True})
        else:
            self._json({"erro": "rota desconhecida"}, 404)


def criar_servidor(porta: int | None = None,
                   cliente: ClienteOllama | None = None) -> ThreadingHTTPServer:
    """Servidor pronto (nao bloqueia). porta=0 = efemera (testes)."""
    estado = EstadoWeb(cliente)

    class Handler(_Handler):
        pass

    Handler.estado = estado
    srv = ThreadingHTTPServer(
        ("127.0.0.1", config.web_port() if porta is None else porta), Handler)
    srv.estado = estado  # visivel p/ testes
    return srv


def main(argv: list[str] | None = None) -> int:
    args = list(argv or [])
    porta = int(args[0]) if args and args[0].isdigit() else None
    try:
        srv = criar_servidor(porta)
    except OSError as e:
        print("[ERRO] nao consegui abrir a porta %s: %s" % (
            porta if porta is not None else config.web_port(), e))
        print("Feche o outro processo ou use: lilo web <porta> "
              "(ou LILO_WEB_PORT no .env)")
        return 1
    url = "http://localhost:%d" % srv.server_address[1]
    est: EstadoWeb = srv.estado
    print("LILO v%s web — %s · modelo %s · modo %s · Ollama %s" % (
        __version__, url, config.modelo(), est.sessao.perms.modo,
        "ON" if est.cliente.ping() else "OFF (inicie o Ollama!)"))
    print("Ctrl+C aqui encerra o servidor. A conversa fica salva "
          "(retome no terminal com: lilo -c).")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[encerrado]")
    finally:
        srv.server_close()
    return 0


# --- a pagina (unica, offline, sem frameworks) ------------------------------
PAGINA = """<!doctype html>
<html lang="pt-BR"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<title>LILO</title>
<style>
:root{--bg:#101418;--painel:#171c22;--borda:#2a323c;--texto:#dbe2ea;
--dim:#8b98a5;--acento:#4f8cff;--lilo:#1d242d;--erro:#e5534b;--ok:#3fb950;
--ambar:#d29922}
*{box-sizing:border-box;margin:0}
body{background:var(--bg);color:var(--texto);height:100vh;display:flex;
flex-direction:column;font:15px/1.5 system-ui,'Segoe UI',sans-serif}
header{display:flex;gap:12px;align-items:center;padding:10px 16px;
background:var(--painel);border-bottom:1px solid var(--borda)}
header b{font-size:17px;letter-spacing:.5px}
header .meta{color:var(--dim);font-size:12.5px;flex:1}
header select,header button{background:var(--lilo);color:var(--texto);
border:1px solid var(--borda);border-radius:8px;padding:5px 10px;
font-size:13px;cursor:pointer}
#dot{width:9px;height:9px;border-radius:50%;background:var(--erro)}
#dot.on{background:var(--ok)}
#chat{flex:1;overflow-y:auto;padding:18px 0}
#chat .miolo{max-width:860px;margin:0 auto;padding:0 16px;display:flex;
flex-direction:column;gap:10px}
.msg{padding:10px 14px;border-radius:12px;white-space:pre-wrap;
overflow-wrap:break-word;max-width:85%}
.user{background:var(--acento);color:#fff;align-self:flex-end;
border-bottom-right-radius:4px}
.lilo{background:var(--lilo);border:1px solid var(--borda);
align-self:flex-start;border-bottom-left-radius:4px}
.tool,.confirm{color:var(--dim);font:12.5px/1.5 ui-monospace,Consolas,
monospace;align-self:flex-start;padding:0 6px}
.erro{color:var(--erro);font:12.5px/1.5 ui-monospace,Consolas,monospace;
align-self:flex-start;padding:0 6px}
#vazio{color:var(--dim);text-align:center;margin-top:14vh}
#vazio h1{font-size:26px;color:var(--texto);margin-bottom:8px}
#pensando{display:none;color:var(--dim);font-size:13px;padding:2px 8px;
align-self:flex-start}
#pensando.on{display:block}
#caixa-confirm{display:none;max-width:860px;margin:0 auto 10px;width:100%;
padding:0 16px}
#caixa-confirm.on{display:block}
#caixa-confirm .cartao{border:1px solid var(--ambar);border-radius:12px;
background:var(--painel);padding:12px 14px}
#caixa-confirm .kind{color:var(--ambar);font-weight:600;font-size:13px;
text-transform:uppercase;letter-spacing:.5px}
#caixa-confirm pre{white-space:pre-wrap;overflow-wrap:break-word;
font:12.5px/1.5 ui-monospace,Consolas,monospace;color:var(--texto);
margin:8px 0;max-height:180px;overflow-y:auto}
#caixa-confirm button{border:0;border-radius:8px;padding:8px 16px;
font-size:14px;cursor:pointer;margin-right:8px}
.b-sim{background:var(--ok);color:#fff}.b-nao{background:var(--erro);
color:#fff}.b-sempre{background:var(--lilo);color:var(--texto);
border:1px solid var(--borda)!important}
footer{padding:12px 16px 16px;background:var(--painel);
border-top:1px solid var(--borda)}
footer .miolo{max-width:860px;margin:0 auto;display:flex;gap:10px}
textarea{flex:1;resize:none;background:var(--bg);color:var(--texto);
border:1px solid var(--borda);border-radius:12px;padding:11px 14px;
font:15px/1.4 inherit;height:52px;outline:none}
textarea:focus{border-color:var(--acento)}
#enviar{background:var(--acento);color:#fff;border:0;border-radius:12px;
padding:0 22px;font-size:15px;cursor:pointer}
#enviar:disabled{opacity:.45;cursor:default}
</style></head><body>
<header>
  <b>LILO</b><span id="dot" title="Ollama"></span>
  <span class="meta" id="meta">conectando...</span>
  <select id="modo" title="modo de permissao">
    <option>plan</option><option>ask</option>
    <option>accept_edits</option><option>auto</option>
  </select>
  <button id="nova" title="zera a conversa">nova conversa</button>
</header>
<div id="chat"><div class="miolo" id="miolo">
  <div id="vazio"><h1>LILO</h1>seu agente local (Ollama) — descreva uma
  tarefa abaixo.<br>Ele le, escreve, edita e roda coisas NA SUA MAQUINA,
  pedindo permissao no ponto.</div>
  <div id="pensando">pensando / executando...</div>
</div></div>
<div id="caixa-confirm"><div class="cartao">
  <span class="kind" id="c-kind"></span>
  <pre id="c-preview"></pre>
  <button class="b-sim" onclick="confirmar('s')">Sim</button>
  <button class="b-nao" onclick="confirmar('n')">Nao</button>
  <button class="b-sempre" onclick="confirmar('t')">Sempre nesta sessao</button>
</div></div>
<footer><div class="miolo">
  <textarea id="tarefa" placeholder="ex.: leia o meu script X, ache o bug e conserte"></textarea>
  <button id="enviar">Enviar</button>
</div></footer>
<script>
const $=id=>document.getElementById(id);
let ultimo="";
async function jfetch(u,opts){const r=await fetch(u,opts);return r.json();}
function render(st){
  const s=JSON.stringify(st);if(s===ultimo)return;ultimo=s;
  const m=$('miolo');const perto=$('chat').scrollTop+$('chat').clientHeight
    >=$('chat').scrollHeight-80;
  m.querySelectorAll('.msg,.tool,.erro,.confirm').forEach(e=>e.remove());
  if(st.historico.length)$('vazio').style.display='none';
  for(const h of st.historico){
    const d=document.createElement('div');
    d.className=h.t==='user'?'msg user':h.t==='lilo'?'msg lilo':h.t;
    d.textContent=(h.t==='tool'?'\\u2192 ':'')+h.texto;
    m.insertBefore(d,$('pensando'));
  }
  $('pensando').className=st.rodando&&!st.pendente?'on':'';
  $('caixa-confirm').className=st.pendente?'on':'';
  if(st.pendente){$('c-kind').textContent='confirmar: '+st.pendente.kind;
    $('c-preview').textContent=st.pendente.preview;}
  $('enviar').disabled=st.rodando;
  if(perto)$('chat').scrollTop=$('chat').scrollHeight;
}
async function poll(){try{render(await jfetch('/api/status'));}catch(e){}}
async function info(){try{const i=await jfetch('/api/info');
  $('meta').textContent='v'+i.versao+' \\u00b7 '+i.modelo+
    (i.sessao?' \\u00b7 sessao '+i.sessao:'');
  $('dot').className=i.ollama?'on':'';$('modo').value=i.modo;}catch(e){}}
async function enviar(){const t=$('tarefa').value.trim();if(!t)return;
  $('tarefa').value='';
  await jfetch('/api/tarefa',{method:'POST',body:JSON.stringify({tarefa:t})});
  poll();info();}
async function confirmar(r){
  await jfetch('/api/confirmar',{method:'POST',
    body:JSON.stringify({resposta:r})});poll();}
$('enviar').onclick=enviar;
$('tarefa').addEventListener('keydown',e=>{
  if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();enviar();}});
$('modo').onchange=async e=>{await jfetch('/api/modo',{method:'POST',
  body:JSON.stringify({modo:e.target.value})});info();};
$('nova').onclick=async()=>{await jfetch('/api/nova',{method:'POST',
  body:'{}'});ultimo='';$('vazio').style.display='';poll();info();};
setInterval(poll,1000);setInterval(info,5000);poll();info();
</script></body></html>
"""
