# Plano — Toolbox compartilhada + roteamento por custo no LILO

**Data:** 2026-08-06 · Branch alvo: `arch-v11` · Autor: Luiz Dione (via auditoria Claude Code)

## Achado central (muda a estratégia)

O LILO **já tem** as duas peças pedidas — e ambas estão **parcialmente desligadas**. O
trabalho não é construir do zero; é **religar, sincronizar e consolidar**. Isso é
coerente com o próprio código, que já admite três consolidações passadas
(`shared/models.py:1-6`, `shared/router.py:1-10`, `config/profiles.yaml:3-7`).

---

## Parte A — Toolbox compartilhada (baixo esforço, valor imediato)

**Estado:** existe `lilo_skills/` (registry + schemas + wrappers finos) + um importador
automático `lilo_skills/import_claude_skill.py`. Motor de execução:
`shared/exec_env.py:run_script()` (roda o `.py` no env conda). Exposto por 3 tools MCP
genéricas — `lilo_list_skills`, `lilo_run_skill`, `lilo_skill_info`. **N scripts = 0
tools MCP novas.** Já portados: `perfil_dados`, `gpp_*` (GraphPad), `bibref`,
`git_check_clean/sync`, `montar_raw_data`, `check_integrity`.

**Problemas concretos (medidos hoje):**
1. `registry.json` é de **2026-04-27** — desatualizado frente aos scripts que mudaram.
2. `PORT_SPEC` (`import_claude_skill.py:54`) aponta `check_integrity` para
   **`derobotizar_artigo`**, que foi **arquivada** em 2026-08-06 (`~/.claude/skills-arquivadas/`).
   **Se rodar hoje, quebra** — a origem correta agora é `build_paper/scripts/check_integrity.py`.
3. Faltam os scripts **novos** criados em 2026-08-06.

**Ações:**
- **A1.** Corrigir o `PORT_SPEC`: `check_integrity` → `build_paper/scripts/check_integrity.py`.
- **A2.** Estender o `PORT_SPEC` com os scripts novos, todos determinísticos:
  | skill origem | script | nome de tool sugerido |
  |---|---|---|
  | build_paper | `scripts/secao.py` | `secao` |
  | build_paper | `scripts/compilar.py` | `compilar_paper` |
  | build_paper | `scripts/figura_check.py` | `figura_check` |
  | auditoria_paper | `scripts/check_stats.py` | `check_stats` |
- **A3.** Re-rodar `python lilo_skills/import_claude_skill.py <slug>` para cada uma →
  regenera wrapper + schema + entrada no `registry.json`, sincronizando com o estado atual.
- **A4.** Conferir que o profile MCP ativo expõe `lilo_list_skills`/`lilo_run_skill`. O
  profile desta máquina é `claude_code` (`.mcp.json`); se não expuser as 3 tools de skill,
  adicioná-las em `config/profiles.yaml` no bloco `claude_code`.
- **A5. Não duplicar** (sobreposições já existentes):
  - Memória de projeto → `shared/project_memory.py` **já lê** `.project-memory/PROJECT_STATE.md`
    do diretório do autor (`DEFAULT_ROOT` = `OneDrive/Data_Science/Projetos`). Não portar `pmm.py`.
  - PDFs → já há **três** caminhos (`scholaragent/` RAG, `agents/PDFs_library/`, skill `bibref`).
    Não criar um quarto; `bibref` já cobre o índice compacto.
  - `prism_*` nativo é o motor **PrismAI** (estatística), sem relação com GraphPad (`gpp_*`).

---

## Parte B — Roteamento por custo (médio esforço, maior impacto)

**Estado:** a lógica que você quer **já existe pronta** em `shared/policy.py`
(`PolicyEngine.decide()`, linhas 187-270): classifica complexidade por keyword/regex e
escolhe um tier na escada `NO_LLM → OLLAMA_FAST → OLLAMA → OLLAMA_HEAVY → CLAUDE_SONNET →
CLAUDE_OPUS`, com `COST_PER_1K` real. **Mas está órfã** — sua saída (`ctx["_tier"]`/
`ctx["_model"]`) não é lida por nenhum agente.

O funil único de toda chamada LLM é `shared/llm_client.py:chat()` → `_dispatch_chat()`
(linhas 117-185), que **já aceita** um `tier` que força `claude_haiku/sonnet/opus` ou
`ollama`. Hoje o Villa só escala para Claude como **fallback de falha** (gated por
`LILO_ALLOW_CLOUD_FALLBACK` + profile), **nunca por dificuldade da tarefa**.

**Modelos disponíveis** (`shared/models.py:31-58`, `.env`): chat `gemma3:12b`, code
`qwen2.5-coder:14b`, plan `qwen3:14b`, fast `qwen2.5-coder:7b-instruct`, embed
`mxbai-embed-large`; worker cloud `gpt-oss:120b-cloud` (Ollama Cloud); Claude via tier.

**Ações:**
- **B1. Religar a policy ao funil.** Em `_call_agent` do Villa (e em `lilo.py:route()`),
  quando não houver `tier` explícito, chamar `PolicyEngine.decide(query)` e passar o tier
  resultante para `client.chat(..., tier=...)`. É a mudança de 1 ponto que ativa tudo.
- **B2. Regra "skill determinística antes de LLM" (custo zero).** Antes de rotear para um
  modelo, checar se a tarefa casa com uma tool da toolbox (Parte A) — `perfil_dados`,
  `check_stats`, `figura_check`, `secao`, `bibref` → resolver com `NO_LLM`. É o roteamento
  por custo levado ao limite: token zero para o que é mecânico.
- **B3. Escada real por complexidade** (não por intenção): trivial→`ollama_fast`,
  simples→`ollama`, moderada→`ollama_heavy`/`gpt-oss cloud`, complexa/raciocínio
  fino→`claude_sonnet`, e `claude_opus` só para o topo. O classificador barato
  (`qwen 7b`) que o Orchestrator já usa (`villa_lobos/agent.py:1013`) alimenta isso.
- **B4. Consolidar as duas camadas de decisão** que hoje não se falam: `policy.py`
  (complexidade→tier alvo) decide *quanto poder*; `server_profile.py` (por ambiente,
  `get_profile_policy`) decide *se cloud é permitido*. A policy propõe, o profile veta.
- **B5. Medir** com `shared/cost_tracker.py` (já existe): custo por tarefa e fração que
  toca Claude, antes/depois. É o critério de "melhorou".

---

## Parte C — Kimi (só depois de medir)

**Kimi/Moonshot não existe no LILO hoje** (busca no repo: zero ocorrências). Adicionar é
barato — é OpenAI-compatible, entra como um `model_name` no proxy LiteLLM
(`config/litellm_config.yaml.example`) ou como um tier em `_dispatch_chat`. **Mas:**

- **Não** "rodando de fundo" — orquestrador é event-driven; um LLM idle não economiza.
- Só entra **depois** de B rodar e medir **onde** o roteamento local erra. Ollama local
  (qwen/gemma) + `gpt-oss:120b-cloud` já cobrem triagem e worker.
- Justifica-se se: (a) precisar de **contexto longo barato** que o local não dá, ou
  (b) como **verificador adversarial barato** (segundo modelo que confere o do Villa).
  Nesse caso, Kimi como um tier `kimi_verify`, não como roteador paralelo ao Villa.

---

## Ordem, esforço e "não-fazer"

1. **Parte A** primeiro — reversível, valor imediato, não toca no raciocínio. 
2. **Parte B** — religar `policy.py` (B1) é a alavanca; B2 (skill antes de LLM) é o maior
   corte de custo.
3. **Parte C** — só com número na mão.

**Não-fazer** (senão a "colcha de retalhos" cresce): não adicionar Kimi ao lado do Villa
sem medir; não criar 4º indexador de PDF; não portar `pmm.py` (memória já integrada);
aproveitar para **remover** a redundância já existente (`villa_route` vs
`villa_explain_routing` chamam o mesmo `explain_routing()`; `policy.py` órfã).

## Verificação
- **Toolbox:** `lilo_list_skills` lista `secao`/`check_stats`/`figura_check`;
  `lilo_run_skill check_stats --args ...` roda e devolve o artefato compacto.
- **Roteamento:** `lilo_cost_today`/`cost_tracker` mostram queda no custo e que tarefas
  triviais não tocam Claude; uma pergunta difícil escala para `claude_sonnet` por
  complexidade (não por falha).

---

## Execução — 2026-08-06

**Parte A — REVERTIDA (violava a regra de IP de artigo).**
- A tentativa inicial rodou `import_claude_skill.py --all` e portou as skills do Claude
  para o LILO. **Erro:** a maioria (`build_paper`, `auditoria_paper`, `biblioteca_ref`,
  `git_dione`, `montagem_resultados`) é **IP de artigo**, que o autor **purgou de todo o
  histórico do git** (ver `.gitignore:121-130` e a memória do projeto). O `--all`
  reintroduziu `secao`/`figura_check`/`check_stats` + a pasta `auditoria_paper/` (esta
  nem estava no `.gitignore`) como arquivos **trackeáveis** — um vazamento de IP.
- **Revertido:** deletados os novos de artigo; `registry.json`, `import_claude_skill.py`,
  schemas e wrappers voltados ao HEAD. Nada foi commitado; o repo ficou limpo.
- **Conclusão para a toolbox:** só skills **não-artigo** podem ser compartilhadas no LILO
  público (`perfil_dados`, `graphpad_prism` — as "borderline" que o autor manteve). As de
  artigo, se rodarem no LILO, ficam **100% locais e gitignored**, nunca no `registry.json`
  trackeado. A regra de IP tem precedência sobre a economia de token da toolbox.
- `check_stats` chegou a ser testado (rodou via `run_script` no env conda) antes da
  reversão — a integração funciona tecnicamente; é a política de IP que a barra.

**Parte B — FEITA e testada (opt-in, seguro).**
- Religada a `shared/policy.py` (órfã) ao funil `shared/llm_client.py:_dispatch_chat`,
  via novo `_route_by_cost()`. **Gate `LILO_COST_ROUTING`** (default OFF): sem a flag, o
  fluxo antigo fica 100% intacto; com `=1`, chamadas sem tier explícito são roteadas pela
  complexidade (trivial→`ollama_fast` … crítica→`claude_opus`). Falha-segura: erro na
  policy → comportamento padrão.
- Documentada no `.env.example` (bloco Policy Engine). Não se tocou no `.env` real.
- **Teste:** "liste arquivos"/"traduza" → `ollama_fast`; "análise crítica de docking com
  MMGBSA/free energy/metadynamics" → `claude_opus`. Tradução para o dispatch confirmada.

**Como ativar o roteamento por custo:** pôr `LILO_COST_ROUTING=1` no `.env` real e
reiniciar o LILO. Acompanhar com `lilo_cost_today`. **B2 (skill determinística antes de
LLM) e a consolidação B4 ficam para a fase de auditoria** (não implementadas ainda).
