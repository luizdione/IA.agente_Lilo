# LILO — Changelog

> **Numeração:** `vXX.Y` = versão do produto (esta série); `arch-vNN` = geração de
> branch/arquitetura (atual: `arch-v12`).

## v13.7.0 — 2026-08-26 (o chat no NAVEGADOR de volta: `lilo web`)

- **`lilo web`** (`lilo/web.py`): chat no navegador em `http://localhost:8100`
  — decisão do dono ("Web primeiro"), revertendo parcialmente o "sem
  dashboard" do reset, MAS sem repetir o v12: é um **subcomando do mesmo
  binário** (precedente do mcp-serve), **stdlib pura** (http.server, zero
  dependência nova), servindo o MESMO loop/choke-point/portão do terminal.
- **Portão com botões**: a confirmação pausa-no-ponto vira um cartão na
  página — [Sim] [Não] [Sempre nesta sessão] — com a thread da tarefa
  BLOQUEADA num Event até o clique (15 min sem resposta = não). Grants
  escopados idênticos aos do terminal; modo trocável no cabeçalho.
- **Continuidade real**: a conversa do navegador persiste no MESMO SQLite
  das sessões — retome no terminal com `lilo -c <id>` (e vice-versa).
- Escopo seguro: escuta SÓ em 127.0.0.1, uma tarefa por vez (409), eventos
  de tool ao vivo por polling (1s), erros com dica de Ollama offline.
- **Ícone → navegador**: `criar_atalho.py` agora grava o LILO.lnk abrindo
  `lilo.ps1 web` (servidor + navegador sozinho); `--terminal` volta ao REPL
  puro da v13.5. Porta via `LILO_WEB_PORT` ou `lilo web <porta>`.
- Testes: 111 herméticos (+8) — servidor real em porta efêmera com
  FakeOllama, incluindo o fluxo de confirmação bloqueante de ponta a ponta
  e a persistência compartilhada.

## v13.6.0 — 2026-08-26 (primeira tool científica: ler_pdf)

- **`ler_pdf`** (11ª tool): extrai texto de PDFs (artigos, manuais) com
  paginação — cabeçalho `[PDF nome — N paginas; exibindo A-B]`, marcadores
  `--- pagina N ---`, argumentos `pagina_inicial`/`paginas` (teto 40) e corte
  interno em 24k chars que **preserva a dica de continuação** (`use
  pagina_inicial=X`) em vez de deixar o truncador global comê-la. Abre o
  gate científico com caso de uso nomeado pelo dono (leitura de artigos).
- Leitura **livre** (kind None) atrás do MESMO choke-point/portão; PyMuPDF é
  dependência **opcional** (sem ele, a tool instrui `pip install PyMuPDF` —
  o núcleo continua requests+dotenv).
- Exposta também no **`lilo mcp-serve`** (10 wrappers) — Claude Desktop lê
  PDFs da máquina via LILO.
- Prompt do agente: regra 10 (PDFs → `ler_pdf`, navegar com `pagina_inicial`).
- **Ponte inversa documentada**: `scripts\claude_ollama.ps1` abre o Claude
  Code CLI rodando nos SEUS modelos Ollama locais (endpoint
  Anthropic-compatível do Ollama; nada sai da máquina).
- Testes: 103 herméticos (+11; os de PDF real geram o PDF com o próprio
  fitz e pulam limpo sem PyMuPDF). Validação viva dupla: choke-point com
  paginação correta E o LOOP completo (qwen3:4b real chamou `ler_pdf`
  nativamente num artigo de 3 páginas e respondeu "DESeq2" citando o trecho).

## v13.5.0 — 2026-08-26 (blindagem offline + ergonomia de manutenção)

- 🔴 **Blindagem 100% local**: modelos Ollama Cloud (`*-cloud`) — que MANDAM
  DADOS PRA FORA — são **excluídos da auto-descoberta** do smoke (o dono tem
  gpt-oss/mistral-cloud instalados e a fila poderia escolhê-los); se
  `LILO_MODEL` apontar para um, o smoke recusa com aviso. Lógica extraída em
  `montar_candidatos()` pura e testada.
- **Ícone → PowerShell**: `lilo.ps1` (UTF-8, venv, `-NoExit`) e o
  `criar_atalho.py` agora apontam o atalho para `powershell.exe` rodando o
  REPL — clicar no ícone abre o agente NO TERMINAL (não existe dashboard de
  navegador no v13, por decisão do reset). Rode `python scripts\criar_atalho.py`
  para regravar o atalho.
- **`LILO_DEBUG=1`**: payloads e respostas do modelo no log
  (`<dados>/logs/lilo.log`) para diagnosticar respostas ruins.
- **REPL**: `\atualizar` (git pull + `pip install -e .` num comando),
  `\esquecer <chave>` direto, `\memoria exportar|importar <arquivo>` (backup
  JSON da memória; import recalcula embeddings).
- Testes: 92 herméticos (+8).

## v13.4.0 — 2026-08-26 (ecossistema: LILO como SERVIDOR MCP)

- **`lilo mcp-serve`** (`lilo/mcp_servidor.py`): o LILO serve suas 9 tools a
  clientes MCP (Claude Desktop) — repondo a ponte do legado SEM violar o
  anti-inchaço: subcomando do MESMO binário e TODA execução pelo MESMO
  `executar_tool` (choke-point + portão). A tool `mcp` não é reexposta
  (proxy-de-proxy). Suporta mcp 1.x (FastMCP) e 2.x (MCPServer).
- Permissões sem stdin: modo por `LILO_MCP_SERVE_MODE` (default
  `accept_edits` — leitura/escrita na allow-list passam; shell vira
  `[NEGADO]` instrutivo; `auto` libera shell, **git nunca**).
- **Validação viva (round-trip)**: a tool `mcp` do LILO conectou no PRÓPRIO
  `lilo mcp-serve` (processo separado, stdio), listou as tools, memorizou e
  lembrou via MCP — cliente E servidor provados juntos (fecha também o
  "teste vivo de MCP" da v13.2).
- Gated (sem caso de uso nomeado, conforme decisão): provider cloud
  plugável e científicos como tools.
- Testes: 84 herméticos (+4: wrappers passam pelo choke-point, defaults de
  modo, git nunca, roteamento do subcomando).

## v13.3.0 — 2026-08-26 (ergonomia: esquecer, \memoria, sessões nomeadas, cores)

- **Tool `esquecer(chave)`**: apaga um fato da memória persistente (par do
  memorizar/lembrar; idempotente).
- **`\memoria [busca]`** no REPL: lista/busca a memória sem gastar o modelo;
  **`\sessoes`** lista as conversas salvas (id, título, quando, marca a
  atual); **`lilo -c <id>`** retoma uma sessão ESPECÍFICA (id de 12 chars do
  `\sessoes`) — `lilo -c` sozinho segue retomando a última.
- **Cores ANSI** (`lilo/cores.py`): preview de confirmação com diff
  verde/vermelho e kind em amarelo; linhas de tool em cinza; erros em
  vermelho. Auto-desligadas sem TTY (pipe/CI) e por `LILO_CORES=0`; no
  Windows o truque `os.system('')` ativa o VT do cmd.
- Testes: 80 herméticos (+6: esquecer idempotente, listagens, retomada por
  id com verificação do histórico enviado, cores tty/kill-switch).

## v13.2.0 — 2026-08-26 (qualidade: janela com resumo LLM + memória semântica)

- **Sumarização de janela por LLM**: quando o histórico estoura `num_ctx`,
  antes da poda determinística o miolo da conversa é condensado em um bloco
  `[RESUMO DA CONVERSA ANTERIOR]` pelo modelo FAST (uma chamada, sem tools).
  A poda continua como fallback que nunca falha (e preserva o bloco de
  resumo). `LILO_RESUMO=0` volta ao comportamento v13.1.
- **Busca semântica na memória**: `gravar` calcula embedding via `/api/embed`
  (best-effort, timeout 3s, embedder fora do ar degrada silencioso);
  `lembrar` usa cosseno em Python puro (sem numpy no runtime) com fallback e
  mescla LIKE. **Validado ao vivo**: consulta "placa de video" achou a chave
  `gpu_dono` (RTX 3060) onde o LIKE não achava nada. Migração de schema
  automática (coluna `embedding`). Envs: `LILO_MEMORIA_EMBED`,
  `LILO_MODEL_EMBED` (default mxbai-embed-large, que o dono já tem).
- Testes: 74 herméticos (+7: cosseno ranqueia, mescla, fallback, migração,
  resumo substitui miolo, desligado/falho caem na poda).

## v13.1.0 — 2026-08-26 (streaming + memória persistente + MCP como tool)

As três evoluções do backlog, todas como TOOLS atrás do loop/choke-point
(regra anti-inchaço respeitada) e validadas ao vivo contra Ollama real:

- **Streaming**: a resposta aparece token a token no terminal. `stream:true`
  no `/api/chat` com acumulador NDJSON que reduz os chunks ao MESMO formato
  não-stream — o loop não muda; transporte de stream injetável (suíte segue
  hermética). Só a UI de terminal liga (`suporta_stream`); `LILO_STREAM=0`
  desliga. Impressão única (sem eco duplicado da resposta final).
- **Memória persistente** (`lilo/memoria.py` + tools `memorizar`/`lembrar`):
  KV mínimo em SQLite (WAL, `%LOCALAPPDATA%\LILO\memoria.db`), busca LIKE por
  chave/valor/tags, upsert. Validado ao vivo ENTRE PROCESSOS: gravou numa
  execução, lembrou em outra. Sem embeddings por ora (anti-inchaço).
- **MCP como tool** (`lilo/mcp_cliente.py` + tool `mcp`): o LILO consome
  servidores MCP externos com allow-list explícita (`LILO_MCP=nome=comando
  args;...`), dependência OPCIONAL (`pip install mcp` — ausência vira [ERRO]
  instrutivo). Sem `tool` lista as tools do servidor; kind `mcp` no portão
  (confirma em ask/accept_edits; grant por kind com `t`).
- Extra: `scripts/limpar_mcp_claude.py` remove do Claude Desktop os MCP do
  LILO legado (backup + idempotente).
- Testes: 67 herméticos (streaming acumulação/tool_calls/desligado, memória
  roundtrip, parse/gate/execução do mcp). `check.py` verde.

## v13.0.0 — 2026-08-25 (LANÇAMENTO: validado na máquina do dono)

Smoke **PASSOU na RTX 3060** com `qwen3:14b` (candidato nº 1 da
auto-descoberta, já instalado): o LILO criou um script, executou via shell e,
no aceite canônico, **leu o erro de um script quebrado, consertou com `editar`
e provou com `exit=0`** — na máquina real do dono. `LILO_MODEL` gravado no
`.env` automaticamente. Versão sai de `-dev`: **13.0.0**.

## v13.0.2 — 2026-08-25 (modelo default: qwen3 + smoke auto-descoberta)

Primeiro smoke real (máquina do dono + reprodução ao vivo em container com o
MESMO Ollama 0.32.15) fechou o diagnóstico do risco nº 1: **o template do
`qwen2.5-coder` está quebrado para tool-calling nativo no Ollama 0.32.x** —
até o exemplo canônico do `/api/chat` devolve a chamada como texto
(`tool_calls: null`), em 3b e 14b. **`qwen3` no mesmo servidor emite
`tool_calls` nativos perfeitos.** O cliente do LILO estava correto.

- Default trocado: `LILO_MODEL=qwen3:14b` (fast: `qwen3:4b`); .env.example e
  README explicam o porquê.
- `smoke_lilo.py` virou **auto-descoberta**: inventaria os modelos instalados
  (`/api/show` → capability `tools`), testa candidatos em ordem de família
  (qwen3 → qwen2.5-coder → llama3.1 → …) nos 2 aceites, e **grava o vencedor
  no `.env`** — um comando, zero decisões manuais.
- v13.0.1: loop detecta "tool escrita como TEXTO" e corrige o modelo (até 2
  nudges, sem executar nada parseado de texto).

## v13.0 — 2026-08-24 (RENASCIMENTO: agente de terminal 100% local sobre Ollama)

**Reset radical aprovado pelo dono.** A plataforma v12.x (42k LOC: dashboard
Streamlit, MCP server, API HTTP, 10 subagentes, skills auto-geradas) virou uma
colcha de retalhos **sem a capacidade central** — não havia tool-calling nativo
em lugar nenhum (tudo prompt+regex), o cliente LLM não suportava conversa
multi-turno e 5 entry points duplicavam a mesma superfície. Demolida em
`arch-v12`; **tudo recuperável** no branch `v12.15-legado`
(`git show v12.15-legado:<caminho>`).

O v13 nasce como **"Claude Code local"** (~1,6k linhas, deps: requests+dotenv):

- **`lilo/cliente.py`** — Ollama `/api/chat` **multi-turno** com **tools
  nativas**; `num_ctx` sempre explícito; retry/backoff, keep_alive normalizado
  e parse defensivo (thinking-fallback) herdados do legado; transporte
  injetável (suíte 100% hermética via FakeOllama).
- **`lilo/agente.py`** — o loop: chat → tool_calls → executa → `role:"tool"` →
  repete; casamento por ordem; `[ERRO]` volta ao modelo (aborta em 3
  consecutivos); teto `LILO_MAX_ITERS`; janela podada deterministicamente;
  system prompt PT-BR + contexto do projeto (`LILO.md`/`CLAUDE.md`/
  `CONTEXT.md` do cwd) injetado como bloco rotulado DADOS.
- **`lilo/tools.py`** — `ler`, `escrever` (atômica), **`editar`** (trecho
  exato e único), `listar`, `buscar` (rg ou puro-Python com ignore-list),
  `shell` (deny-list destrutiva; timeout mata a **árvore** de processos).
  **`executar_tool` = choke-point único** — implementações privadas, nenhum
  caminho fora do portão.
- **`lilo/portao.py`** — plan/ask/accept_edits/auto **sem estado global**;
  *never-commit-unless-asked* (git_write confirma até em auto); grants
  **escopados** (write por kind; shell/git por hash do comando). Confirmação
  **no ponto da tool** — `n` vira `[NEGADO]` e a MESMA conversa continua
  (zero replay). Default de fábrica: `ask`.
- **`lilo/sessoes.py`** — transcript SQLite (WAL, `%LOCALAPPDATA%\LILO`),
  persistência a cada iteração; `lilo -c` retoma a última sessão fielmente
  (tool_calls inclusos).
- **`lilo/cli.py`** — one-shot + REPL (`\modo \modelo \plano \nova \ajuda`);
  aprovar plano segue na mesma conversa em accept_edits.
- **Windows**: `lilo.bat` (UTF-8, duplo clique = REPL) +
  `scripts/criar_atalho.py` (**ícone LILO na Área de Trabalho** via
  PowerShell, respeitando Desktop no OneDrive).
- **Verificação**: `scripts/check.py` verde (55 testes herméticos);
  `scripts/smoke_lilo.py` = teste VIVO na máquina do dono (Ollama real,
  aceite canônico: criar script → rodar → ver o erro → consertar sozinho).
- Regra anti-inchaço gravada no CLAUDE.md: **funcionalidade nova = tool atrás
  do loop/choke-point; nunca novo entry point. Um binário: `lilo`.**

Adiado p/ v13.x (como tools): memória semântica KV, cloud opcional, RAG/
Scholar/PDF, MCP.

## v12.15 — 2026-08-20 (V18.11: guarda de versão do dashboard + scrubber pré-cloud)

Rodada de correção a partir de um relato do dono: "o layout do dashboard não
mudou nada". Diagnóstico (dashboard subido de verdade via `AppTest`, não só
sintaxe): o redesign estilo Claude é **real e correto no Streamlit ≥ 1.39**,
mas **degrada em silêncio em versão anterior** — o composer-cartão, o realce
de navegação, a barra superior e o botão PARAR são estilizados por classes
`st-key-*`, que só existem a partir do 1.39. O pin `streamlit>=1.30.0`
permitia justamente uma versão onde metade do "look" não aplica.

- **Guarda de versão no boot** (`dashboard.py`): se o Streamlit for < 1.39, um
  `st.error` explícito instrui a atualizar (`pip install -U "streamlit>=1.39"`)
  — a quebra deixa de ser silenciosa. O próprio aviso usa só APIs universais,
  então nunca quebra.
- **Selo de versão na sidebar**: `v12.15.0 · Streamlit X.Y` sob o título —
  confirma na hora que o build em execução é este (não uma cópia antiga, ex.:
  do OneDrive) e qual Streamlit está em uso.
- **Pin endurecido**: `requirements.txt` → `streamlit>=1.39`.
- **E5b — scrubber de segredos pré-cloud** (`shared/scrubber.py`): complementa
  o gate E5 (que *decide* se envia) redigindo credenciais do `prompt`+`system`
  **antes** de saírem para a nuvem. Padrões de alta confiança (chaves
  Anthropic/OpenAI/Google/AWS, tokens GitHub/Slack, JWT, Bearer, blocos PEM,
  `key=value` com valor secreto) — ancorados por prefixo para **não** mutilar
  sequências/IDs científicos. E-mails são opt-in (`LILO_SCRUB_EMAILS`); tudo
  desligável por `LILO_SCRUB=0`. Integrado em `llm_client._maybe_cloud_prepare`
  (gate + scrub num ponto só, só no destino cloud). Log expõe rótulo+contagem,
  nunca o valor.
- Testes: `tests/shared/test_scrubber.py` (offline; padrões, opt-in de e-mail,
  kill-switch, ausência de falso-positivo em texto científico, integração com
  `_maybe_cloud_prepare`). `scripts/check.py` verde.

## v12.14 — 2026-08-19 (V18.10: gerente de memória do projeto)

- **`CONTEXT.md` (raiz)** vira a memória viva do projeto — o LILO já o lê
  automaticamente (dir_synthesis, E4) e o Claude Code o vê em toda sessão.
  Seções AUTO (estado, entregas) + MANUAL (pendências, decisões, retomada).
- **`scripts/memoria_projeto.py`**: regenera as seções AUTO com 0 tokens —
  versão (badge do README), branch/commit (git), contagem de funções de
  teste, resumo do `/diagnostico_lilo` (`--no-diag` pula) e últimas 3
  entradas do CHANGELOG. Seções MANUAL preservadas byte a byte
  (marcadores `<!-- AUTO:x -->`); cria do template se ausente.
- **Skill `/gerente_memoria`** (`.claude/skills/`): protocolo de 1 comando +
  curadoria das seções MANUAL com limites rígidos (≤80 linhas — o arquivo
  entra em contexto de sessão).
- `CLAUDE.md` aponta o `CONTEXT.md` como primeira leitura de retomada.
- Testes: `tests/scripts/test_memoria_projeto.py` (4, offline/herméticos).

## v12.13 — 2026-08-19 (V18.9: dashboard minimalista — layout Claude completo)

A pedido do dono: "quero minimalista já abrindo no chat, com adição de
arquivos, pastas e módulo de LLM na tela, igual ao Claude". Só camada
visual/UX + 1 fio novo (seletor de modelo); nenhuma página ou função
removida. Auditoria (`/diagnostico_lilo`): P0=0; P1/P2 restantes têm a
mesma causa (`agents/paper/` só existe na máquina do dono).

**Composer-cartão estilo Claude (página Chat):**
- Um único cartão (`st.container(border=True)`) com o `text_area` "nu" em
  cima e a linha de controles embaixo, NA MESMA caixa: `+` anexos
  (arquivos E pastas c/ síntese de diretório — popover já existente),
  microfone (agora popover 🎤), **seletor de MODELO** e modo de execução.
- **Seletor de modelo na tela** (novo): Auto (Policy decide) | Local
  padrão/rápido/pesado | Claude Sonnet | Claude Opus. Vira override
  `\lilo <tier>` na chamada do `route()` — mesmo mecanismo do comando
  digitado; nuvem continua sujeita a budget diário e `LILO_ALLOW_CLOUD`.
  O texto exibido/salvo no histórico permanece limpo (sem o prefixo).
- Coluna central estreita e centralizada (~52rem) só na página Chat.

**Sidebar minimalista (estilo Claude):**
- Expostos apenas: logo, status, `+ Novo chat`, botão Chat e a lista de
  **Chats** (busca + lista flat, movida do painel direito). Agentes,
  Cowork, Ferramentas/docs, Preferências (Modo IA + Estilo) e Progresso
  do projeto viraram expanders recolhidos.
- **Painel direito removido** — Histórico e Progresso agora moram na
  sidebar; todas as páginas usam a largura inteira.

**Higiene da auditoria:** 3 imports mortos removidos (`lilo_api.Request`,
`chat_memory.Path`, `mcp_client.Path`); avisos restantes do pyflakes são
probes de disponibilidade intencionais (try/import).

## v12.12 — 2026-08-09 (V18.8: E8 — redesign visual do dashboard, estilo Claude)

Fecha o ÚLTIMO item H2 do roadmap da análise Open Agent Studio (E1–E8
completos). Só camada visual/UX — nenhuma função removida; fluxo de chat
(slash skills, `_resend_text`, confirmações, PARAR) idêntico.

**Tema claro/escuro com botão no topo:**
- A paleta clara já vivia em variáveis CSS (`:root`, `--lilo-*`) no
  `dashboard_styles.py`; o novo `THEME_DARK_CSS` só REDEFINE as mesmas
  variáveis (fundos #1F1E1D/#262624/#30302E, texto claro quente, coral
  mantido) e é injetado DEPOIS do `GLOBAL_CSS` quando
  `st.session_state.theme == "dark"` — vence por cascata, tema inteiro troca
  de uma vez. Botão lua/sol na barra superior alterna e faz `st.rerun()`.
- `WELCOME_CSS`/`HISTORICO_CSS` tinham cores fixas da paleta clara; foram
  convertidas para `var(--lilo-*, fallback)` — o escuro vale também na tela
  de boas-vindas e no histórico. Blocos de código (`.main pre`) escurecidos
  no override.

**Sidebar recolhível com botão «/»:**
- `initial_sidebar_state` deixou de ser fixo: vem de
  `st.session_state.sidebar_state`, alternado pelo botão «/» da barra
  superior (+ `st.rerun()`). O chevron nativo do Streamlit segue funcionando;
  o botão é um atalho sempre visível.

**Caixa de mensagem ACIMA das demais caixas (estilo Claude):**
- O `st.chat_input` nativo é sempre ancorado no rodapé pelo Streamlit e não
  pode subir. Substituído por composer no TOPO da página Chat: `st.form`
  (`clear_on_submit`) + `st.text_area` estilizado como cartão + botão
  Enviar (Ctrl+Enter também envia). Modo de execução, anexos (+) e microfone
  ficam ABAIXO do composer.
- Barra superior com botões ghost (só ícone) via seletores `.st-key-*`.
- Sem testes novos (dashboard não tem suíte própria; Streamlit fora do CI) —
  validação por sintaxe/pyflakes + smoke visual na máquina do dono.

## v12.11 — 2026-08-04 (V18.6/18.7: E6 cliente MCP + E7 workflow dev + git tools)

Fecha os itens H2 restantes do roadmap (menos E8, refactor visual). Aditivo
e default-safe; 171/171 testes.

**E6 — cliente MCP (LILO deixa de ser só servidor):**
- `shared/mcp_client.py`: consome servidores MCP EXTERNOS via stdio.
  Allow-list DUPLA em `config/mcp/clients.yaml` (só servidores habilitados +
  tools permitidas por servidor). Import de `mcp` LAZY e offline-safe (pacote
  ausente/servidor offline → mensagem de erro, nunca crash); `_run_async` em
  thread dedicada (sync-callable até de dentro do FastAPI); timeout por
  chamada. **Sem injeção dinâmica** das tools externas no servidor do LILO —
  acesso só pela ponte `mcp_call(server, tool, args)`.
- Tools MCP `mcp_list_servers`/`mcp_list_tools`/`mcp_call` nos perfis
  `pycharm`, `claude_code` e `desktop`. `config/mcp/clients.yaml` com
  exemplos (filesystem/fetch/github) desligados.

**E7 — tools git dedicadas + workflow dev opt-in:**
- `shared/git_tools.py`: `git_status`/`git_diff` (somente leitura) e
  `git_commit` (gate `git_write`; a chamada explícita da tool autoriza —
  padrão git_dione — exceto no modo `plan`, onde defere).
- `shared/dev_workflow.py`: `run_dev_workflow()` encadeia
  testa→commita→documenta→memoriza, OPT-IN por `LILO_DEV_WORKFLOW=1`; aborta
  se os testes falham (não commita vermelho), atualiza `notes.md` e registra
  no KV (`ns=lilo_dev_workflow`). Runner de teste injetável.
- Tools MCP `git_status`/`git_diff`/`git_commit`/`dev_workflow` nos perfis
  `pycharm` e `claude_code`.

**Bugfix incluído (v12.10):** métodos `fs_*` do `DesktopAgent` (crash do
Explorer). **Dogfooding:** o `/diagnostico_lilo` acusou 2 falsos-positivos de
`B-REG` (handlers `if tool in ("a","b","c")` casavam o padrão de registro de
agente) — o check foi escopado ao bloco `_AGENT_REGISTRY` com âncoras
(módulo com ponto + classe `*Agent`).
- Testes: `test_mcp_client.py` (7), `test_git_dev_workflow.py` (7). Estado:
  171/171, `scripts/check.py` == TUDO OK ==, diagnóstico P0=0 | P1=1 (paper).
- H2 restante: só **E8** (split do dashboard — refactor visual, melhor com o
  usuário acompanhando).

## v12.10 — 2026-08-04 (V18.5: bugfix — crash do Explorer de projeto do Villa)

- **`DesktopAgent` sem métodos `fs_*`** (P0 de runtime, reportado pela UI):
  `dashboard._render_villa_project_explorer` chama `_desktop.fs_list(...)`,
  `.fs_read(...)`, `.fs_write(...)` como MÉTODOS, mas eram só funções de
  módulo → `AttributeError: 'DesktopAgent' object has no attribute 'fs_list'`
  a cada abertura da página Desktop/Explorer. Adicionados delegadores finos
  (`fs_read/fs_write/fs_list/fs_stat/fs_search/fs_move/run_shell/run_python`)
  com assinaturas idênticas — a allow-list e os gates continuam nas funções
  de módulo, zero lógica duplicada. `tests/test_desktop_methods.py` cobre a
  regressão (a chamada exata do Explorer). 150/150.

## v12.9 — 2026-08-04 (V18.4: E3 — memory_facade + lilo_recall + smart context)

ROADMAP itens A + C entregues sobre o E2 (a fachada nasce semântica).
Aditivo e default-safe; 149/149 testes.

- **`shared/memory_facade.py`** (item A): ponto único de consulta de memória.
  `get_relevant_context(query, project_id, k, owner_verified)` monta bloco
  compacto combinando KV semântico (user gated por voz + project_<id>) e
  notes.md, marcado como DADO (anti prompt-injection, política V15 intacta);
  `recall()` gera o relatório unificado (KV com score + notes.md + chats que
  batem via `search_chats`).
- **Inject de `lilo.route` migrado p/ a fachada**: o bloco manual de memória
  do dono (LIKE) vira chamada única — agora SEMÂNTICO com fallback textual,
  mesma política de gate por voz.
- **Tool MCP `lilo_recall`** (query, project_id, limit) nos 6 perfis com
  memória + handler em `lilo.py` — "o que o LILO já sabe sobre X?" em uma
  chamada.
- **Smart context do Reader do Villa** (item C): antes de varrer arquivos, o
  Reader recebe "MEMORIA JA CONHECIDA (não redescubra)" via fachada (k=3,
  600 chars, dados-não-instruções). Kill-switch `LILO_SMART_CONTEXT=0`.
- Testes: `tests/shared/test_memory_facade.py` (4, offline: gate de voz,
  notes por projeto, recall combinado, handler MCP).
- H2 restante: E6 (cliente MCP), E7 (workflow dev), E8 (split dashboard).

## v12.8 — 2026-08-04 (V18.3: E2 — busca semântica na memória KV)

ROADMAP item D entregue (validado pela análise Open Agent Studio como o
degrau de memória de maior impacto). Aditivo e default-safe; 145/145 testes.

- **Schema v3**: coluna `kv.embedding BLOB` via migração incremental
  (`_ensure_column`, retrocompatível com bancos v2 existentes).
- **Embedding na escrita**: `set()` embeda `key: value` via Ollama
  `/api/embed` com `OLLAMA_MODEL_EMBED` (mxbai, já default). Offline/falha
  NUNCA quebra a escrita (linha fica sem vetor). `LILO_KV_EMBED=0` desliga;
  timeout `LILO_KV_EMBED_TIMEOUT` (4s). Embedder injetável p/ testes.
- **`search_semantic(query, ns, limit, min_score)`**: cosseno em numpy sobre
  SQLite (sem ChromaDB aqui, de propósito — Chroma fica no scholaragent);
  fallback TRANSPARENTE p/ busca textual quando não há embeddings (itens
  marcados `match: semantic|like_fallback`); dimensões divergentes (troca de
  modelo de embed) são puladas com segurança.
- **`backfill_embeddings(ns, limit)`**: embeda entradas antigas em lote,
  abortando no primeiro sinal de offline (não paga N timeouts).
- **Tool MCP `lilo_memory_semantic_search`** exposta nos 6 perfis que têm
  memória (pycharm, bio, cowork, claude_desktop, claude_code, desktop);
  handler em `lilo.py` com score por item. `stats()` ganha `with_embedding`.
- Testes: `tests/shared/test_kv_semantic.py` (6, offline com embedder fake:
  ranking, fallback, backfill, migração v2→v3, stats, handler MCP).
- Próximo degrau: E3 (`memory_facade` + `lilo_recall` + smart context do
  Reader), que nasce já semântico sobre este E2.

## v12.7 — 2026-08-04 (V18.2: skill /diagnostico_lilo — auditoria com 0 tokens)

Skill de diagnóstico para desenvolvimento/correções gastando o mínimo de tokens:
a varredura pesada é um script determinístico (sem LLM); o Claude só interpreta
o relatório compacto e devolve o plano.

- **`scripts/diagnostico_lilo.py`** — auditoria em 5 níveis, offline-safe:
  (A) código: sintaxe + pytest (`--fast` pula); (B) fiação: registro de agentes
  importa? keyword-map órfão? tools dos profiles existem no `lilo_mcp`? (a
  classe de bug "paper fantasma" vira check permanente); (C) envs: `.env.example`
  vs leituras reais (canais mortos, com wrapper `_env_flag` e allowlist p/ envs
  dinâmicas `VILLA_TIER_*`); (D) runtime best-effort (Ollama+`missing_models`
  do catálogo E1, LiteLLM, Anthropic, custo gravável, KV) — offline vira INFO;
  (E) docs: drift de versão README×CHANGELOG. Saída compacta com IDs
  (`[P1][B-REG-AUSENTE] ...`), `--json` completo, exit 2/1/0 por severidade.
- **`.claude/skills/diagnostico_lilo/SKILL.md`** — a skill `/diagnostico_lilo`
  (Claude Code): protocolo de economia de tokens (rodar o script PRIMEIRO, não
  re-explorar o que ele já checou, citar achados por ID, só plano — sem aplicar)
  + **rubrica padrão-ouro Claude Code** (10 dimensões → equivalente LILO →
  próximo degrau, amarrada ao roadmap E1..E8/S1..S5).
- Estreia do próprio diagnóstico pegou e corrigiu: drift do badge do README
  (12.4.0 → 12.6.0) e `LILO_CLOUD_GATE` fora do `.env.example`.
- `tests/test_diagnostico.py` (smoke offline). Estado: 139/139,
  `scripts/check.py` == TUDO OK ==.
- **Primeiro plano executado (dogfooding):** P2 de envs 20 → 1 — 17 vars
  documentadas no `.env.example` em blocos temáticos (serviços/paths,
  Scholar RAG, Villa retries/worker/fallback), `LILO_VERSION` morta removida,
  `LILO_PAPER_MODEL` anotada (acoplada ao B-REG-AUSENTE do paper, que exige
  commit na máquina de origem) e filtro de envs dinâmicas aplicado aos dois
  lados do check C. Restam: P1=1 (paper) + P2=1 (var do paper), ambos
  destraváveis só na máquina de origem.

## v12.6 — 2026-08-04 (V18.1: H2 parcial — E1 catálogo, E4 memória, E5 gate cloud)

Primeiro lote estrutural (H2) do roadmap de `docs/tecnico/analise_open_agent_studio.md`.
Tudo aditivo e default-safe; 138/138 testes.

- **E1 — catálogo central de modelos.** Novo `shared/model_catalog.py`: fonte
  única de metadados por modelo (provedor, contexto em tokens, capacidades,
  latência, custo USD/MTok), com heurísticas p/ modelos fora do catálogo
  (`*-cloud` → Ollama Cloud; `claude-*` → família Anthropic, desconhecida
  assume preço Opus — fail-safe). `ExecutionTier.OLLAMA_CLOUD` passa a existir
  (só rótulo/telemetria nesta fase: não entra em `decide()` nem no fallback).
  Telemetria do Villa rotula estágios em Ollama Cloud como `ollama_cloud`
  (antes apareciam como `ollama` — o único provedor cloud em uso era invisível
  na página Custos). Preços Anthropic do QW4 migrados p/ o catálogo.
  `missing_models()` pronto p/ validação de boot (fiação no health fica p/ E1b).
- **E4 — memória de projeto na síntese de diretório.** `_KEY_FILES` ganha
  `CLAUDE.md, TASKS.md, CONTEXT.md, DECISIONS.md, NOTES.md, ARCHITECTURE.md,
  AGENTS.md` (exatamente os arquivos que a spec pede como memória e que
  faltavam), e a síntese ganha a seção "Memória do projeto" com snippets
  curtos dos `.md` de `docs/` e `prompts/` (1 nível, máx. 8 arquivos ×
  600 chars — bounded). Refresh automático por mtime fica p/ E4b.
- **E5 — gate de privacidade pré-cloud.** Novo kind `cloud_send` no
  `exec_mode` + `_cloud_gate` no `llm_client`, aplicado em TODOS os caminhos
  de despacho quando o destino é cloud (Anthropic ou `*-cloud`): `auto`
  (default) → passa e **loga** destino+tamanho; `ask`/`accept_edits` → pede
  confirmação (mesmo fluxo do shell); `plan` → acumula no plano e bloqueia.
  Fecha o requisito "nunca enviar sem autorização explícita" da spec sem
  mudar o comportamento default. Kill-switch: `LILO_CLOUD_GATE=0`.
- Testes: `tests/shared/test_model_catalog.py` (E1+E4+E5, 11 testes).
  Estado: 138/138, `scripts/check.py` == TUDO OK ==.

## v12.5 — 2026-08-04 (V18: quick wins QW1–QW7 da análise "Open Agent Studio")

Aplicação do horizonte H1 do roadmap de `docs/tecnico/analise_open_agent_studio.md`
(gap analysis vs spec externa). Tudo aditivo e default-safe; 127/127 testes.

- **QW1 — `agents/paper` fantasma neutralizado.** O diretório nunca foi commitado
  (existe só na máquina de origem) mas estava registrado em `lilo.py`/README/testes.
  `tests/test_paper_agent.py` ganha `pytest.importorskip` (pula limpo em checkout
  sem o diretório) e `test_skillsmith::test_scaffold_refuses_existing_agent` deixa
  de depender do fantasma — antes, em máquina limpa, o teste **criava**
  `agents/paper/` de verdade (scaffold real via `_scaffold("paper", ...)`),
  poluindo o repo; agora exercita a guarda com `gateway` (versionado).
  *Pendente na máquina de origem: commitar o `agents/paper/` real.*
- **QW2 — fiação policy→agentes, fase 1 (observabilidade).** Novo
  `BaseAgent.resolve_model()`: loga a divergência entre a decisão do Policy
  Engine (`ctx["_model"]`, escrita em `lilo.route` e até a V17 ignorada por
  TODOS os subagentes) e o modelo que o agente realmente usa. Ligado em
  gateway, docgen, skillsmith, scholar (review) e Villa (`_call_agent`, por
  stage). Comportamento inalterado; enforcement fica para o catálogo de
  modelos (E1).
- **QW3 — limites de custo mortos aplicados.** `LILO_MAX_SINGLE_COST` passa a
  barrar chamada única acima do teto em `_budget_allows`; `LILO_ALLOW_CLOUD`
  volta a ser lida (nuvem = flag ligada **E** chave presente; default preserva
  o comportamento anterior). `PolicyConfig.allow_cloud` vira `default_factory`
  (relê o ambiente a cada instância). + `tests/shared/test_policy_budget.py`.
- **QW4 — custo REAL da Anthropic.** `_chat_anthropic` deixa de descartar o
  `usage` da resposta: grava tokens (input/output/cache write/cache read) e
  custo real no CostTracker (preços por família conferidos em 2026-08-04;
  cache write 1,25×, read 0,10×; modelo desconhecido superestima com preço
  Opus — fail-safe p/ budget). `lilo.route` zera a estimativa p/ tiers
  `claude_*` (evita dupla contagem — e o custo fantasma que era registrado
  mesmo quando o agente nem chamava a Anthropic). O gate diário do Policy
  passa a operar sobre gasto real. + `tests/shared/test_cost_telemetry.py`.
- **QW5 — latência agregada.** `CostTracker.latency_summary()` (p50/p95/média
  por dia, nearest-rank, stdlib) + linha de métricas na página Custos do
  dashboard (`duration_ms` já era gravado por request; faltava agregar).
- **QW6 — CI mínimo.** `.github/workflows/tests.yml` roda
  `python scripts/check.py` (sintaxe + pyflakes + pytest) em push/PR, com
  `requirements-ci.txt` (subconjunto validado, sem chromadb/torch). Um CI
  assim teria pego o paper fantasma meses atrás.
- **QW7 — higiene de config.** `docker-compose.yml`: `scistudio` atrás de
  profile (build context ausente do repo quebrava `docker compose up` em
  checkout limpo); `Dockerfile.api` 3.11→3.13 (alvo do repo);
  `.env.example` documenta `LILO_LLM_RETRIES/BACKOFF`, `LILO_ANTHROPIC_CACHE`,
  `LILO_MAX_SINGLE_COST`, `LILO_COST_DB`, `LILO_SERVER_PROFILE`,
  `LILO_SKILLSMITH_MODEL/DOCGEN/REVIEW`, alinha `LLM_TIMEOUT` (120→300, valor
  real do código) e anota `OPENAI_API_KEY` como reservada ao LiteLLM.
- Estado: 127/127 testes (120 anteriores − 6 do paper que agora pulam limpo
  + 13 novos), `scripts/check.py` == TUDO OK ==.

## v12.4 — 2026-07-20 (V17.2: modularização do CSS do dashboard)

Refatoração de organização — **sem mudança de comportamento** (validada byte-a-byte).

- **`dashboard.py`: 2994 → 2437 linhas (−557).** Os 3 blocos de CSS estático
  (global, histórico, welcome) foram extraídos para `dashboard_styles.py`
  (`GLOBAL_CSS`, `HISTORICO_CSS`, `WELCOME_CSS`), injetados nos mesmos pontos.
- CSS **dinâmico** (f-string dependente de variáveis — `nav_button`, `stop_button`,
  card 3D do Villa) permanece inline.
- Validação: o dashboard reconstruído é idêntico ao original (prova byte-a-byte);
  sobe sem erros e renderiza igual (navegador via `read_page` + console limpo);
  120/120 testes.

## v12.3 — 2026-07-20 (V17.1: polimento de código e tooling de qualidade)

Continuação da auditoria V17. Higiene de código e prevenção de regressões.

- **Limpeza cosmética:** 8 variáveis mortas removidas (efeitos colaterais
  preservados — p. ex. `ax.bar()` mantido, só a atribuição saiu), 11 f-strings
  sem placeholder normalizadas, `global _agents` redundante removido.
- **SyntaxWarnings zerados:** 31 skills auto-geradas tinham docstrings com LaTeX
  (`\log`, `\ln`) em strings não-raw → convertidas para r-strings; o gerador
  `generate_skills.py` passa a emitir r-docstring (previne a regressão).
- **Tooling de qualidade:** `[tool.ruff]` no `pyproject.toml`, `.editorconfig`,
  `scripts/check.py` (saúde num comando: sintaxe → pyflakes → pytest) e
  `requirements-dev.txt` (deps de lint/teste).
- Estado: 338 `.py` sem erro de sintaxe, 0 escape warnings, 0 nomes indefinidos,
  120/120 testes.

## v12.2 — 2026-07-19 (V17: auditoria completa, reconciliação de versionamento e limpeza)

Sessão de auditoria e reorganização (branch `arch-v11`). Motivada por uma migração
de `.git` quebrada (junctions mortas) que fez o código do OneDrive divergir como
fonte de verdade enquanto o GitHub ficou com snapshots antigos (ver
`C:\GitHub\_reorg\RELATORIO_FINAL.md`). Auditoria detalhada em
`docs/versoes/AUDITORIA_2026-07-19.md`.

**Reconciliação de versionamento**
- Novo branch `arch-v11` a partir do V16 (`origin/arch-v10`), preservando o
  histórico. Trabalho pós-V16 do OneDrive incorporado (só 6 arquivos diferiam de
  conteúdo real; ~253 eram apenas CRLF).
- `.gitattributes` normaliza EOL (fim do ruído CRLF↔LF no diff).
- Segredos confirmados fora do git (`.env`, `config.yaml`, `config/litellm_config*.yaml`).

**Limpeza (auditoria estática: pyflakes + AST)**
- Código saudável: 0 erros de sintaxe (337 `.py`), 0 nomes indefinidos, 120/120 testes.
- Removidos 43 imports de nível de módulo não usados (probes `try/except` preservados).
- Sem código morto real: os candidatos eram falsos positivos (`test_*`, rotas FastAPI);
  keyword-router e `SECURITY_BLOCK` são fallback/kill-switch **intencionais** (mantidos).

**Reorganização**
- `_ARCHIVE_v10/` (157 arq. legado) e a plataforma híbrida `backend/frontend/llm-gateway`
  retirados do branch ativo (preservados em `origin/arch-v10`).
- `data/projects/`, `data/syntheses/` desrastreados (runtime → `.gitignore`).
- `HYBRID_PLATFORM_V10_1.md` → `docs/historico/`.

## v12.1 — 2026-06-22 (V15.1: corrige over-refusal + latencia + roteamento leve)

Ajustes após uso real (feedback do autor: recusa absurda + lentidão).

- **SECURITY_BLOCK DESLIGADO** (`security=False` no gateway e Villa): causava
  over-refusal grave em modelos locais — recusou "descreva uma dinâmica
  molecular" como "substância perigosa". App pessoal de PhD em bio não deve
  filtrar trabalho científico legítimo; never-commit fica no GATE de git (código).
- **CoT opcional** (`chat(cot=False)`): o gateway (Q&A de turno único) pula o
  bloco `<thinking>` → resposta direta, ~2.4× mais rápida (96s→40s na query do
  bug). O pipeline Villa mantém o CoT para qualidade.
- **Roteamento conceitual → modelo leve**: perguntas definicionais/descritivas
  ("o que é", "descreva", "explique"…) em modo bioinfo/code passam a usar o
  `llama3.1:8b` (leve) em vez do `phi3:14b`/coder — sem perder qualidade em
  definições, bem mais rápido. Geração de código/análise profunda mantém o
  modelo do domínio; modelo explícito sempre tem prioridade.

## v12.0 — 2026-06-20 (V15: aproximacao ao Claude Code/Cowork, FASES 0-4)

Plano gerado por workflow multiagente (3 specs de referencia + mapa da raiz do
LILO + gap analysis + critica adversarial). Diagnostico: o LILO ja tinha o
ESQUELETO (exec-modes, pipeline agentico, memoria, quality_judge) mas
DESCONECTADO. A V15 LIGA a fiacao. **Tudo aditivo e default-safe** (kill-switch
`LILO_PROMPT_BLOCKS`; estilo/judge/verify default desligados). Detalhes e status
em `docs/ROADMAP_claude_alignment.md`.

- **FASE 0** -- religa canais mortos: `shared/prompt_blocks.py` (HONESTY_CORE/MINI
  + kill-switch + compose_system com orcamento de tokens por estagio); gateway
  consome `system_hint` (era ignorado); memoria de turno no chat do dashboard.
- **FASE 1** -- seguranca: gate de git (`git_write`, sensivel ate em 'auto', grant
  ESCOPADO ao cmd -> never-commit-unless-asked); SECURITY_BLOCK (recusa
  proporcional) nas saidas.
- **FASE 2** -- eixo de ESTILO: `config/styles.yaml` (default/conciso/didatico/
  formal, com nao-degradacao + escape) + `shared/response_style.py` (hot-reload);
  ligado so nas saidas (gateway/reporter); seletor no dashboard; cot_suffix
  deixou de empurrar verbosidade na resposta final.
- **FASE 3** -- verificacao + memoria: `quality_judge` opt-in pos-Reporter
  (gated, nunca bloqueia); revival do `owner_verified` (injeta memoria do dono
  como DADO, anti prompt-injection); `chat_memory.distill_facts` (destila fatos
  do historico p/ kv ns=user).
- **FASE 4** (partes seguras) -- gate CENTRAL no orquestrador (plan/ask valem p/
  todas as tools write/exec, nao so o desktop); contrato do CLI (ask+stdin
  interativo / auto scriptado); estagio VERIFY default-OFF (sandbox isolado,
  so codigo auto-contido, sem auto-correcao).
- **FASE 5** -- scheduler do Cowork: `shared/scheduler.py` + `scripts/
  run_scheduler.py` executam as tarefas agendadas (SKILL.md) que antes so eram
  exibidas. DEFAULT-OFF (LILO_ENABLE_SCHEDULER), dry-run, perfil 'cowork'
  (local-only, sem shell/python), exec_mode 'ask', saidas em KVMemory ns
  'lilo_tasks'; SEM loop sempre-ligado (cron/Task Scheduler externo).
  'schedule: manual' (default) nunca roda sozinho.
- **Medicao:** `scripts/bench_prompts.py` (A/B over-refusal/verbosidade/
  confabulacao) + tuning (conciso diretivo, blocos enxutos).
- **Item adiado da FASE 4 -- resolvido em parte:** PLANO APROVAVEL entregue
  (modo plan acumula acoes -> botao "Aprovar plano e executar"; pending_plan/
  approve_plan/clear_plan). O refator global->por-sessao (ContextVar) foi
  DESCARTADO por decisao (risco no rerun do Streamlit, sem beneficio single-user;
  grant multi-repo do git ja coberto por grants escopados).

## v11.6 — 2026-06-19 (2ª auditoria investigativa + corretiva)

Segunda passada de auditoria (estática + manual) sobre o código do projeto.

**Conclusão: nenhum bug de runtime novo.** O único bug de wiring real (tools de
`paper` ausentes do `get_tool_map` → "Tool desconhecida") já fora corrigido na
v11.3. Confirmado limpo via `pyflakes` + sondagens manuais:
- **sem** nomes indefinidos / erros de sintaxe no código do projeto;
- **sem** `except:` nu (todos tipados); **sem** mutação de default mutável
  (o padrão `context or {}` protege os `run(...)`);
- reconstrução do abstract invertido do OpenAlex (`_openalex_abstract`) correta;
- `villa_route` é auto-contido no `lilo_mcp.py` (não passa por `handle_tool_call`)
  → sem gap; cache de `_load_agents` persiste (o `global` é redundante, não bug).

**Correções (cosméticas, seguras):**
- `agents/prism_ai/writing_agent.py`: remove `f` redundante em 2 strings literais
  (marcadores de significância) — eliminava warning de "f-string sem placeholder".
- `agents/prism_ai/main.py`: remove import `json` não-usado.

**Lacuna conhecida (NÃO alterada — requer certeza do schema):**
`agents/prism_ai/export_agent.py` computa `table_type` (via
`_get_prism_table_type`) mas não o aplica ao `<Table>` do `.pzfx`. Os rótulos
retornados (`Column`/`GroupedColumn`) **não** correspondem ao enum `TableType`
do GraphPad (`OneWay`/`TwoWay`/`XY`…); aplicá-los às cegas poderia quebrar a
importação. Deixado para validação do autor (que conhece o formato GraphPad).
Demais achados do pyflakes (imports não-usados, dead vars `n_total`/`bars`/
`exp_type`) são inócuos e foram mantidos para evitar churn.

## v11.5 — 2026-06-19 (V14.6: endurecimento do reconhecimento de voz)

Resposta ao achado de segurança da auditoria (v11.4): o voice-ID era permissivo
(tom sintético diferente passava com score 0.95). Endurecido em `shared/speaker_id.py`:

- **Score por centroide:** `score = cosseno(voz, centroide do dono)`. Removido o
  `max`-sobre-amostras (bastava colar em UMA amostra para passar).
- **Limiar adaptativo/auto-calibrado:** `eff_thr = clamp(self_sim − margem, piso, 0.99)`,
  onde `self_sim` é a auto-similaridade média do enrollment. Adapta-se à
  consistência da voz do dono em vez de um limiar fixo.
- **Piso 0.75 → 0.80** + nova env `LILO_VOICE_MARGIN` (def 0.08).
- **Embedding mais discriminativo:** MFCC + delta + **delta²** (120-d, era 80-d) e
  **trim de silêncio** nas pontas.
- **Voiceprint versionado** (`version=2`): o formato antigo (80-d) é detectado e
  **descartado** → força re-enroll sem crash de dimensão. `needs_reenroll()` novo;
  o dashboard exibe aviso e pede regravação.

Validação (sintético): dono ✓ aceito (limiar adaptativo 0.92); voz diferente
(330 Hz) ✓ **rejeitada** (0.905 < 0.92, antes passava a 0.95); ruído ✓ rejeitado
(−0.92); migração v1→v2 ✓ sem crash. `.env.example` ganhou as seções de voz/STT
(antes não documentadas). **Segue sendo conveniência, não segurança forte.**

## v11.4 — 2026-06-19 (auditoria de código dos módulos V13/V14)

Auditoria investigativa linha-a-linha dos módulos novos (paper, docgen,
skillsmith, exec_mode, speaker_id, transcribe, prism `_eda`, scholar `_review`).
Bugs corrigidos e validados:

- **`shared/speaker_id.py`** [Windows, médio]: `np.load()` devolve um `NpzFile`
  que mantém o arquivo aberto; `enroll()` escrevia o **mesmo** `owner.npz` com
  `np.savez()` enquanto o handle de leitura podia estar aberto → risco de
  `PermissionError` no Windows (e vazamento de handle em `verify`/`n_samples`).
  Agora usa `with np.load(...) as data:`. Validado: round-trip enroll×3/verify/
  reset sem erro.
- **`agents/prism_ai/main.py`** (`_eda`) [baixo]: nome de coluna com `/`, `:`
  etc. quebrava o `savefig` e **abortava todos** os gráficos no Windows. Nome do
  arquivo agora é sanitizado. Validado: colunas `a/b`/`c:d` geram os PNGs.
- **`agents/docgen/agent.py`** (`_to_pptx`) [trivial]: removida variável morta
  `blank` (layout não usado).

**Observação de segurança (não alterada — decisão do usuário):** a verificação
de locutor usa `max` sobre as amostras + limiar 0.75; no teste, um tom sintético
diferente passou com score 0.95. O embedding MFCC leve é **pouco discriminativo**
— adequado como *conveniência* (carregar memórias do dono) num PC pessoal, mas
**não** como fronteira de segurança forte. Endurecer (centroide-only, limiar
maior) afeta o voiceprint já cadastrado → deixado a critério do autor.

## v11.3 — 2026-06-19 (V14.5: expor recursos V13/V14 no MCP)

Correção de integração: os 9 recursos das levas V13/V14 (`scholar_review`,
`prism_eda`, `paper_draft`/`paper_section`/`paper_references`,
`make_report_docx`/`make_xlsx`/`make_pptx`, `create_agent_scaffold`) tinham
agente + tool MCP definidos, mas **não eram expostos** aos clientes — não
apareciam no Claude Code/Desktop/PyCharm.

- **`config/profiles.yaml`** (fonte da verdade do filtro `mcp_tools`): os 9 tools
  adicionados aos 5 perfis de lista explícita (`claude_code`, `bio`, `cowork`,
  `claude_desktop`, `pycharm_assistant`). `desktop_dev`/`openclaw` (=`null`) já
  os expunham por registro. `claude_code` passou de 23 → 32 tools.
- **`lilo_mcp.py`** (`_PROFILE_TOOLS`, fallback usado se o YAML sumir): mesmos 9
  tools nos 4 perfis embarcados, mantendo paridade com o YAML.
- **`lilo.py`** (`get_tool_map`): **bug** — os tools de `paper` não estavam no
  mapa central, então `paper_*` retornava "Tool desconhecida" em runtime. Agora
  roteados (outline/section/references/draft/build); `paper_build` preserva o
  diretório default do agente quando `root` vem vazio.
- **`scripts/test_mcp_stdio.py`**: `--profile` agora deriva os perfis válidos de
  `config/profiles.yaml` (+aliases), com fallback embarcado — antes a lista
  hardcoded não tinha `claude_code` (o comando documentado no CLAUDE.md falhava).
  Default mudou para `claude_code`.

Validação e2e (stdio real): handshake OK, `claude_code` lista 32 tools com os 9
novos presentes; `get_tool_map()` roteia os 13 nomes; YAML e sintaxe OK.

## v11.2 — 2026-06-12 (V14: modos de execução estilo Claude)

Feature pedida: os modos de interação do Claude no LILO. Política escolhida:
**confirmar só ações de risco**.

- **`shared/exec_mode.py`**: 4 modos — **plan** (só planeja), **ask** (confirma
  todo risco), **accept_edits** (edita direto, confirma shell), **auto**
  (executa tudo; DEFAULT). `gate(kind, preview)` + confirmação one-shot
  (`grant_once`). Risco = shell, python, escrita fora da allow-list.
- **`agents/desktop/agent.py`**: gating em `run_shell`/`run_python`/`fs_write`.
  Default auto → zero mudança de comportamento.
- **`dashboard.py`**: seletor visual dos 4 modos (substitui Agir/Perguntar);
  quando uma ação precisa de confirmação, mostra a prévia + botão **✅ Confirmar
  e executar** (concede o grant e reenvia). Modo planejamento exibe aviso e não
  executa nada. Configurável também por `LILO_EXEC_MODE`.

- **V14.1 — Microfone (voz→texto):** `shared/transcribe.py` (faster-whisper
  local, CPU/int8, nenhum áudio sai da máquina) + `st.audio_input` no dashboard.
  Você fala, o LILO transcreve e injeta como prompt. Config por `LILO_WHISPER_*`.
- **V14.2 — Reconhecimento de locutor:** `shared/speaker_id.py` (MFCC+cosseno,
  leve, SEM torch). Enrollment da voz do dono no dashboard (3+ amostras) +
  verificação no microfone (🔓/🔒) → marca `owner_verified` no contexto.
  Voiceprint local e gitignored. Config `LILO_VOICE_THRESHOLD`.

Testes: +16 (108 passam).

## v11.1 — 2026-06-12 (V13.1–13.4: leva de importação de skills do Claude)

Proposta de importação aprovada pelo Dione — 4 capacidades novas, todas
testadas e com escritor cloud (gpt-oss:120b, sem GPU local) onde redigem:

- **V13.1 — Revisão de literatura** (`scholar_review`): busca ampla nas 10
  fontes + dedup (DOI/título) + revisão estruturada (estado da arte/consensos/
  lacunas/direções) com referências reais. Validado e2e.
- **V13.2 — Geração de documentos** (`docgen`, 9º subagente): relatórios `.docx`
  (LLM→pandoc), planilhas `.xlsx` (openpyxl) e apresentações `.pptx`
  (python-pptx). Validado offline nos 3 formatos.
- **V13.3 — EDA** (`prism_eda`): perfil exploratório rápido (dimensões, tipos/
  nulos, describe, histogramas, heatmap de correlação) — determinístico,
  complementa o pipeline estatístico do `prism_analyze`.
- **V13.4 — Criador de skills** (`skillsmith`, 10º subagente): gera o scaffold
  de um novo subagente LILO (BaseAgent que compila), valida, e devolve as
  instruções de registro — não auto-modifica o roteamento. Validado: o scaffold
  carrega de fato.

Todos integrados ao roteamento (porta única + keywords + tool_map).
**LILO agora tem 10 subagentes.** Testes: +18 (87 passam).

## v11.0 — 2026-06-12 (V13: subagente `paper` — redação científica)

Porta a skill `build_paper` (antes só no Claude) para o LILO como **8º
subagente**, tornando o LILO autossuficiente em redação científica.

- **`agents/paper/`** (`PaperAgent`): outline IMRaD, redige seções, monta a
  fonte Markdown e builda DOCX/TEX/PDF (pandoc + tectonic). Escritor forte via
  Ollama Cloud (`LILO_PAPER_MODEL`=gpt-oss:120b-cloud — **não usa GPU local**).
- **Referências REAIS** (anti-invenção): via `research_sources` (OpenAlex/
  PubMed/Europe PMC/Crossref); o modelo nunca fabrica citações — sinaliza lacuna.
- **Perfil de revista** inferido das fontes reais (calibre do periódico-alvo).
- Tools: `paper_outline`, `paper_section`, `paper_references`, `paper_draft`,
  `paper_build`. Integrado ao roteamento (porta única + keywords específicas que
  não capturam leitura de PDF).
- Infraestrutura da skill portada para `lilo_skills/skills/build_paper/`
  (autossuficiência); **tectonic** instalado (PDF).
- Validado e2e: refs reais com DOI + outline técnico p/ *Acta Tropica* (cloud, 30s).

Testes: +6 (70 passam).

## v10.7 — 2026-06-12 (V12.3: alavancas de qualidade do Worker, configuráveis)

Ataca o gargalo real apontado pelo juiz LLM (variância factual do Worker local,
não o roteamento). Tudo **configurável por env** e medível com o juiz; **nenhum
default muda** o comportamento vigente. Implementado e testado **sem GPU** (mock).

- **Temperatura configurável** (`LILO_WORKER_TEMP`=0.25 conhecimento /
  `LILO_WORKER_TEMP_CODE`=0.4 código) — antes a V11.3 era hardcoded.
- **Self-consistency** (`LILO_WORKER_SC`=k, default 1=off): o Worker gera k
  respostas independentes e **consolida só o corroborado por ≥2** (descarta o
  que aparece em uma só → menos invenção factual). Custo ~k+1 chamadas.
- **Worker na nuvem** (`VILLA_WORKER_GENERAL_MODEL=gpt-oss:120b-cloud`): roda no
  Ollama Cloud, **sem usar a GPU local**.
- `.env.example`: documenta as alavancas + chaves de pesquisa opcionais
  (`GOOGLE_BOOKS_API_KEY`, `NCBI_API_KEY`, `LILO_WIKI_LANG`) com onde obtê-las.

Testes: +3 (64 passam). **Medição com juiz (N≥5) pendente** — requer GPU livre.

## v10.6 — 2026-06-11 (V12: orquestração unificada — porta única + delegação por etapa)

Villa Lobos vira a **porta única** de roteamento; os subagentes continuam
módulos independentes, mas agora um só orquestrador semântico decide quem
assume — e pode **dividir as etapas** entre especialistas.

1. **Roteador semântico como porta única.** `lilo.route()` em modo auto delega
   a decisão a `VillaLobosAgent.route_target()` (LLM router → heurística →
   capabilities) em vez do keyword-router raso (`_detect_tab`, agora fallback).
   Domínio claro → especialista; ambíguo/complexo → pipeline. Desligável via
   `LILO_SEMANTIC_ROUTER=0`. Validado (Ollama): capital→gateway, ANOVA→prism,
   pubmed→scholar, arquivos→desktop, SQL→sql, incerteza→villa.
2. **Modo IA → "Auto" (default) + override.** O seletor manual
   chat/code/bioinfo/sql vira "Auto" (o roteador decide); os modos antigos
   permanecem como override opcional (`sql` força o agente SQL; chat/code/
   bioinfo forçam o gateway no modo).
3. **Delegação por etapa.** O Orchestrator pode indicar `worker_agent` no JSON
   (validado contra [scholar, sql, prism, pdf, desktop]); a etapa Worker do
   pipeline é então executada por esse especialista e o Reporter sintetiza.
   Validado e2e (Ollama): "busque artigos no pubmed e resuma" → Worker via
   ScholarAgent. Desligável via `LILO_STAGE_DELEGATION=0`.
4. **Decomposição em CADEIA (V12.1).** `_decompose_chain()` quebra uma tarefa
   multi-ação em até 4 sub-tarefas SEQUENCIAIS, cada uma para um especialista,
   encadeando as saídas (contexto acumulado) no lugar do loop do Worker. Gatilho
   leve (`_looks_multi_step`: ≥2 verbos de ação + conjunção). Validado e2e
   (Ollama): "busque no pubmed … e depois analise" → cadeia `scholar → prism`
   → Reporter sintetiza. Desligável via `LILO_CHAIN_DELEGATION=0`.

5. **Busca na internet ampliada (V12.2).** `shared/research_sources.py` ganhou
   4 fontes gratuitas: **OpenAlex** (substituto do Google Scholar — sem API/
   anti-scraping), **Europe PMC**, **Google Books** (`GOOGLE_BOOKS_API_KEY`
   opcional — quota anônima satura), **Wikipedia** (`LILO_WIKI_LANG`). Total: 10
   fontes acadêmicas/conteúdo + web geral (DuckDuckGo). ScholarAgent: `source`
   aceita as novas; `source="all"` agrega as acadêmicas.

Testes: +14 (61 passam).

## v10.5 — 2026-06-11 (plataforma híbrida, dashboard Claude Desktop, Villa V11.2)

### Arquitetura híbrida (v10)
- Subprojetos antigos consolidados em `agents/`; legado movido para `_ARCHIVE_v10/`.
- **API HTTP** (`lilo_api.py`, FastAPI :8088) e **multiplexer** `lilo_serve.py`
  (`--transport stdio/http/sse`). `lilo_server.py` e `lilo_pycharm_mcp.py`
  **arquivados** (o MCP do PyCharm hoje é `lilo_mcp.py --profile pycharm`).
- Profiles MCP `claude_code` e `cowork` adicionados a `_PROFILE_TOOLS`.

### Dashboard
- Reformulação visual estilo **Claude Desktop** (marfim/coral, headings
  serifados, composer arredondado) — `dashboard.py` + `dashboard_cowork.py`.

### Villa Lobos — V11.2 (roteamento e robustez)
- **Guarda anti-fast-path unificada** (`_block_fast_path`): explicação/profundidade
  deixam de cair em fast-path raso (antes só demonstração/prova era protegida).
- **Retry/fallback**: HTTP 400 (payload) agora é fail-fast; demais 4xx pulam
  retry mas permitem fallback de modelo; 5xx/timeout seguem com retry.
- **`keep_alive`** normalizado (corrige 400 do Ollama com `OLLAMA_KEEP_ALIVE=-1`).
- **De-viés de domínio** no `EXPERT_SYSTEM`/worker prompt (não impõe mais
  "mecanismos moleculares" a história/geografia/matemática).

### Avaliação de qualidade
- **`shared/quality_judge.py`**: juiz LLM por domínio (rubrica 4×0-25),
  modelo distinto do avaliado para mitigar auto-viés.
- `scripts/bench_semantic_domains.py`: flags `--judge` e `--repeat N`.

## v10.4 — 2026-05-08 (profile MCP `opus` + descriptions reescritas)

### Profile `opus` em `lilo_mcp.py`

**Problema resolvido:** Claude Opus 4.x no Claude Desktop carregava 35 tools
mas usava só 2 (`lilo_web_search`, `lilo_web_fetch`). Análise mostrou que 17
tools eram redundantes com o próprio Opus (lilo_chat, lilo_pdf, villa_*,
prism_audit, etc.) — Opus prefere responder direto a delegar para outro LLM.

**Mudanças:**

- **Novo profile `opus`** em `_PROFILE_TOOLS` com **18 tools curadas** que
  AGREGAM capacidade ao Opus: internet (`lilo_web_search`, `lilo_web_fetch`),
  filesystem (`fs_read/write/list/stat/search`), execução local (`run_python`,
  `run_shell`), memória persistente (`lilo_memory_set/get/list/search`),
  literatura (`lilo_scholar`), estatística (`prism_analyze`, `prism_classify`),
  Ollama (`lilo_list_local_models`, `lilo_pull_model`).
- **Descriptions reescritas** com template `USE WHEN ... DO NOT USE WHEN ...
  Exemplo:` em todas as 18 tools, dando ao Opus triggers inequívocos.
- **`config/mcp/claude_desktop.json`** agora aponta `--profile opus` por default.
- **17 tools "ocultas"** continuam acessíveis no dashboard via slash command
  (`/lilo_chat`, `/villa_pipeline`, `/lilo_pdf`, etc.).
- **`opus` adicionado ao argparse** de `lilo_mcp.py` e `scripts/test_mcp_stdio.py`.
- **Smoke test corrigido** — antes tentava chamar `lilo_health` (não existe no
  profile `opus`); agora escolhe a primeira tool disponível.

### Robustez do servidor MCP

- **`_install_excepthook()`** captura crashes silenciosos do servidor e escreve
  stack trace em stderr (visível em `%LOCALAPPDATA%\Claude\logs\mcp-server-lilo.log`).
- **`_ensure_lilo()` resiliente** — falhas de `load_env` não derrubam o servidor.
- **Logging com timestamp** em transições (`[LILO MCP HH:MM:SS] ...`).

### Documentação

- **`docs/uso/PROFILE_OPUS.md`** — guia completo de ativação/reversão.
- **README** atualizado com tabela de profiles + saída esperada do smoke test.

### Refactor da UI (dashboard.py)

- Sidebar direita simplificada — só Histórico (lista flat estilo Claude Desktop)
  + nova seção **Progresso** com checkboxes de tasks por projeto.
- "Projetos" movida para a aba Villa Lobos (área central) com explorador de
  arquivos CRUD (Ler / Escrever / Renomear / Remover).
- "Anexos" virou popover (+) na caixa de mensagem em todas as views.
- Botões **✋ Agir** / **⚠️ Perguntar** na caixa LILO (estilo Claude Desktop):
  controla `intent`, `allow_tools`, `system_hint` no contexto enviado ao agente.

### Schema (chat_memory)

Nova tabela `project_tasks` (id, project_id, title, done, created_at, updated_at)
com 6 métodos: `add_task`, `list_tasks`, `set_task_done`, `delete_task`,
`rename_task`, `task_progress`.

### Erros de sintaxe corrigidos

3 arquivos haviam sido truncados em sessão anterior por limite de créditos:
`lilo.py:672`, `lilo_mcp.py:594`, `lilo_skills/__init__.py:348`.

## v10.3 — 2026-05-07 (memória robusta + 4 tools novas)

### `shared/kv_memory.py` reescrito (394 linhas)

**Problema resolvido:** "disk I/O error" e locks em SQLite quando o
banco fica dentro do OneDrive (sync ativo causa contention).

**Mudanças:**

- **DB padrão fora do OneDrive.** Default Windows: `%LOCALAPPDATA%\LILO\memory\kv_memory.db`. Unix: `~/.local/share/lilo/memory/kv_memory.db`. Override via env `LILO_KV_MEMORY_DB`.
- **Migração automática** do `memory/kv_memory.db` legado (no OneDrive). Cópia única na primeira inicialização; o original permanece como backup.
- **TTL/expires_at** opcional em `set(key, value, ttl_seconds=N)`. `get()` retorna `default` se entrada expirou. `cleanup_expired()` faz housekeeping.
- **Busca textual** com `search(query, ns=, limit=)` — substring case-insensitive em key, value e tags.
- **WAL mode** (`PRAGMA journal_mode=WAL`) + `busy_timeout=5000` para mitigar locks em uso concorrente.
- **Schema migrável** via `_ensure_column()` — bancos antigos ganham `expires_at` automaticamente. Tabela `meta` registra `schema_version=2`.
- **Export/import JSON** (`export_json(ns=)`, `import_json(data, overwrite=)`) para backup.
- **Stats** (`stats()`) com total, contagem por namespace, expirados, tamanho do DB, schema_version.

### 4 novas tools MCP de memória (v10.3)

Centralizadas em `lilo.handle_tool_call` + thin wrappers em `lilo_mcp.py` (delegam) + entradas em `lilo_skills/__init__.py` (menu `/`).

| Tool | Args | Função |
|---|---|---|
| `lilo_memory_search` | `query`, `namespace=""`, `limit=50` | Busca textual em key/value/tags |
| `lilo_memory_stats` | — | JSON com total, by_namespace, expired, db_size, schema_version |
| `lilo_memory_export` | `namespace=""` | Backup JSON (filtra por ns opcional) |
| `lilo_memory_cleanup` | — | Remove entradas expiradas |

`lilo_memory_set` ganhou parâmetro opcional `ttl_seconds` (omita para nunca expirar).

### Total de tools v10.3

- **CORE_SKILLS**: 28 (era 24 → +4 memory_search/stats/export/cleanup)
- **list_all_tools**: 236 (era 232)
- **Menu `/` do dashboard**: 28 core + 199 geradas = **227 skills visíveis**

## v10.2.1 — 2026-05-07 (hotfix menu / no dashboard)

**Bug:** após v10.2, `/lilo_memory_set`, `/lilo_cost_today`, etc. **não
apareciam no menu `/` do dashboard 8100** apesar de estarem registradas
em `lilo.list_all_tools()`. Causa: o menu lê de `_CORE_SKILL_META` em
`lilo_skills/__init__.py`, que tinha apenas as 16 tools originais.

**Fix:**

1. `lilo_skills/__init__.py` — adicionadas as 8 tools v10.2 (`lilo_memory_*`, `lilo_cost_*`, `lilo_pull_model`, `lilo_list_local_models`) tanto em `CORE_SKILLS` (mapeamento de roteamento) quanto em `_CORE_SKILL_META` (metadados visíveis no menu). Total subiu de 16 para 24 skills core.
2. `dashboard.py` — parser de slash command refeito:
   - Antes: `/lilo_cost_today` (sem args) **listava** em vez de executar.
   - Agora: nome exato sem args **executa com `{}`** (útil para tools com defaults). Nome parcial continua listando como autocomplete.
   - Mensagens de listagem agora mencionam ambos os formatos: `/<nome>` ou `/<nome> arg=val`.

**Para aplicar:** reiniciar o `dashboard.py` (Ctrl+C e re-rodar `START_LILO_WINDOWS.bat`). O cache `@st.cache_data(ttl=60)` da função `load_skills_list` invalida automaticamente em 60s, mas reiniciar é mais rápido.

## v10.2 — 2026-05-07 (sprint MCP tools + skills)

### 8 novas tools MCP centralizadas em `lilo.py`

Antes elas só existiam em `lilo_mcp.py` (acessíveis via Claude Desktop e
PyCharm). Agora estão em `handle_tool_call` e `list_all_tools`,
expondo-as automaticamente em **todos os clientes**: CLI, dashboard 8100,
API HTTP `/v1/tools/call`, MCP stdio. `lilo_mcp.py` agora apenas delega
(zero duplicação).

**Memória persistente (4 tools)** — KV store SQLite em `data/kv_memory.db`:

- `lilo_memory_set(key, value, namespace="default", tags="")`
- `lilo_memory_get(key, namespace="default")`
- `lilo_memory_list(namespace="", tag="")`
- `lilo_memory_delete(key, namespace="default")`

**Cost tracker (2 tools)** — observabilidade de gastos:

- `lilo_cost_today(target_date="")` — JSON do `daily_summary` (por backend e subagente)
- `lilo_cost_recent(limit=20)` — últimas N requests com modelo, custo, duração

**Ollama model manager (2 tools)** — útil ao trocar de máquina:

- `lilo_pull_model(name, timeout=600)` — `ollama pull <name>` via subprocess. Validação regex no nome para bloquear injection. Timeout configurável.
- `lilo_list_local_models()` — `ollama list`

### Skills — saneamento (`lilo_skills/`)

- **`registry.json` ganha `schema_version`** (v1.1) e `generator_version`. O `_load_registry()` em `lilo_skills/__init__.py` detecta divergência e emite warning sugerindo regenerar — útil ao trocar de máquina ou após `mamba update`.
- **Prefixo `skill_advanced_<nome>`** para skills com `complexity="high"` (em vez de `skill_<nome>`). Reduz poluição no menu `/` do dashboard. `load_skills_as_tools(include_advanced=False)` permite omitir totalmente. Hoje há 0 skills high (193 simple + 6 medium); o esquema é futuro-proof.
- `generate_skills.py` atualizado para emitir `schema_version=1.1` em regenerações. Contagem `by_complexity` agora inclui `high`.
- **`call_skill()`** trata os dois prefixos (`skill_` e `skill_advanced_`) corretamente ao remover.

### Documentação

- `docs/uso/COMANDOS.md` — 3 novas seções (Memória, Cost, Ollama manager) + seção de saneamento periódico das skills.
- `docs/historico/2026-05-07_relatorio_ia_lilo.md` — itens 3.2 e 3.3 marcados como concluídos.
- `docs/tecnico/arquitetura_v10.md` — bumpado para v10.2.

## v10.1 — 2026-05-07 (sprint curto-prazo)

### Aba Desktop no dashboard 8100 (`dashboard.py`)

- Novo botão **Desktop** na sidebar (`SUB-AGENTES`).
- Página com 6 sub-abas (`fs_read`, `fs_write`, `fs_list`, `fs_search`, `run_shell`, `run_python`) — formulário visual para cada tool, reutilizando `lilo.handle_tool_call` (zero duplicação de lógica).
- Mostra a allow-list ativa em um expander para o usuário saber onde pode operar antes de digitar paths.
- `DesktopAgent` carregado automaticamente em `load_agents()` ao lado dos demais.

### Smart routing no Villa-Lobos (`agents/villa_lobos/agent.py`)

- `_orchestrate_decision()` — Orchestrator emite JSON estruturado com `{complexity, needs_planning, needs_reader, needs_worker, iterations, skip_to_reporter, reasoning}`.
- **Fast-path** `skip_to_reporter`: tarefas triviais (definições, conversões, perguntas factuais) pulam Planner+Reader+Worker e vão direto ao Reporter — economiza ~70% de latência (1 chamada Ollama vs 5).
- Cada stage agora é condicional via flags do JSON (`needs_planning`, `needs_reader`, `needs_worker`).
- Fallback duplo: se o LLM falhar/devolver JSON inválido, heurística regex (`_SIMPLE_PATTERNS` + comprimento<80) decide; se nem isso acionar, pipeline completo (default conservador).
- `context` continua aceitando override manual de qualquer flag (compat com chamadas antigas e testes).
- Saída inclui `**Stages:** orchestrator -> ... -> reporter` para rastreabilidade.

### Pre-commit hook AST (`scripts/`)

- `scripts/pre_commit_ast_check.py` — valida com `ast.parse()` todos os `.py` staged. Detecta também truncamento OneDrive via heurística (null bytes, brackets/strings não fechados) **antes** de chegar ao `ast.parse`, dando mensagens diagnósticas mais claras.
- `scripts/install_hooks.py` — instala o hook em `.git/hooks/pre-commit` (cross-platform, com `.bat` de diagnóstico ao lado para Windows nativo). Suporta `--uninstall`.
- Bypass de emergência: `git commit --no-verify` (registrar motivo no commit).
- Testado contra arquivo deliberadamente truncado: `FAIL  /tmp/truncated.py  (truncamento provavel -- brackets nao fechados: ))` — exit 1.

## v10.0 — 2026-05-07 (arch-v10)

### MCP integrado e funcionando

- **Bug crítico corrigido:** `_profile_tool` chamava `mcp.tool()` antes de `mcp = FastMCP(...)` ser definido — causava `NameError` no import e impedia o servidor de subir no Claude Desktop e PyCharm. Reordenado.
- **Smoke test stdio** (`scripts/test_mcp_stdio.py`) — simula handshake MCP do Claude Desktop. Validado com 23 tools detectadas e 7/7 subagentes OK.
- **MCPs unificados** com flag `--profile {desktop|pycharm|http}`. `lilo_pycharm_mcp.py` removido (era 95% duplicado).
- **Perfis MCP prontos** em `config/mcp/{claude_desktop,claude_code,pycharm}.json`.

### Desktop Commander integrado (subagente novo)

- `agents/desktop/agent.py` — 7 tools (`fs_read`, `fs_write`, `fs_list`, `fs_stat`, `fs_search`, `run_shell`, `run_python`).
- Allow-list de paths em `LILO_DESKTOP_ALLOW` (`.env`).
- Bloqueio de comandos perigosos (`rm -rf /`, `format c:`, `mkfs`, fork bomb).
- Acessível via Claude Desktop, PyCharm e dashboard 8100.

### Tools de memória e custo (lilo_mcp.py)

- `lilo_memory_set/get/list/delete` — persistência de variáveis entre sessões.
- `lilo_cost_today/recent` — visualização de gastos com Claude API.

### Refatoração arquitetural (arch-v10)

- **Subagentes não duplicados:** removidas cópias de `Analise_SQL/`, `scholaragent/`, `PDFs_library/` da raiz (eram 1 linha diferentes de `agents/`).
- **`llm-gateway/` desmontado:** `agent.py` virou `agents/gateway/agent.py`, `litellm_config.yaml` foi para `config/`. Restantes (orfãos `agents/lilo_agent.py` 328 linhas, `health_check.py` 68 linhas, dirs vazios) movidos para `_ARCHIVE_v10/to_delete/`.
- **`backend/` + `frontend/` arquivados** em `_ARCHIVE_v10/v6_fastapi/` (FastAPI v6 + React nunca foram iniciados pelo `START_LILO_WINDOWS.bat`).
- **Docker compose arquivado** (idem).

### Portas trocadas (conflitos com outras APIs do usuário)

- Dashboard Streamlit: **8506 → 8100** (travado em `.streamlit/config.toml`).
- PDFs Library: **8503 → 8101**.

### Correções de bugs encontrados na auditoria

- `shared/llm_client.py`: arquivo estava **truncado em produção** (`_client_instance` sem corpo). Restaurado o singleton `get_client()`.
- `shared/policy.py`: `get_status()` também truncado, restaurado.
- `shared/llm_client.py`: ordem de detecção de backend invertida (Ollama era detectado antes do LiteLLM, contrariando o docstring). Corrigido para LiteLLM-first.
- `shared/policy.py`: query OpenMM/DM era classificada como "tarefa simples" e ia pra Ollama leve. Adicionados 26 tokens (`openmm`, `nvt`, `npt`, `equilibration`, `gromacs`, `amber`, `rmsd`, `mmgbsa`, etc.) → agora vai pra Claude Sonnet/Opus quando aplicável.
- `requirements.txt`: declarado `duckduckgo-search`, `beautifulsoup4`, `lxml` (eram opcionais e silenciavam falhas).
- `BUILD_E_ABRIR.bat` e `dashboard.py`: paths antigos de `PDFs_library/` (raiz) atualizados para `agents/PDFs_library/`.

### Skills adicionadas

- `lilo_skills/skills/bio/openmm_nvt_equilibration_safe.py` — gera script OpenMM anti-NaN com minimização + ramp + HMR + checkpoints. Resolve o erro reportado em 2026-05-06.

### Dashboard reformado

- **CSS reescrito do zero** — sidebar verde com texto branco legível, header sem corte, painel direito mais estreito.
- **Aba Ajuda nova** com 6 sub-tabs renderizando dinamicamente os .md de `docs/`.
- **Aba Docs eliminada** (redundante com Ajuda).
- **Card 3D Villa-Lobos** mostrando os LLMs de cada estágio (Orchestrator/Planner/Reader/Worker/Reporter), posicionado no rodapé da página.
- **Botão "Aquecer GPU"** na aba Saúde — força o modelo para a VRAM com `keep_alive=2h`.
- **Diagnóstico GPU diferenciado**: distingue "GPU (driver)" via `nvidia-smi` de "Ollama VRAM" (modelos carregados agora). "Idle" não é mais erro.
- **Default de iterações Villa-Lobos = 2** (era 1) — sweet spot para research-grade.
- **Tooltips** em `iterations`, `use_reader`, `base_path`.

### Configuração

- `OLLAMA_KEEP_ALIVE=2h` adicionado ao `.env` — modelos não descarregam mais da VRAM após 5 min.
- `LILO_DESKTOP_ALLOW` no `.env` — controla pastas acessíveis ao Desktop Commander.

### Documentação

- Todos os .md migrados para `docs/{uso,tecnico,versoes,historico,agentes}/`. Apenas `README.md` restou na raiz.
- Aba Ajuda do dashboard renderiza tudo dinamicamente.
- `_ARCHIVE_v10/README.md` documenta o que foi removido.

---

## v9.0 — 2026-04-25 (não documentada formalmente; reconstituída)

- Adicionado subagente `prism_ai` com 6 sub-agentes internos.
- Adicionado pipeline Villa-Lobos (5 stages).
- Auto-síntese de diretório anexado.
- Notas de projeto auto-mantidas em `notes.md`.
- Slash commands no chat (`/skill_name`).

## v8.0 — 2026-04 (não documentada)

- ChatMemory com SQLite + busca textual.
- CostTracker com SQLite.
- Skills auto-geradas (199) do ambiente Conda.

## v7.0 — 2026-03 (não documentada)

- Primeira versão funcional do MCP server.
- Health check.
- Dashboard Streamlit inicial.

---

Para ver as auditorias e investigações detalhadas, veja `docs/historico/`.
