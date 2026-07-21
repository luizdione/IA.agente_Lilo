# Roadmap — aproximar o LILO do Claude Code / Cowork (V15)

Origem: workflow multiagente (2026-06-20) sobre 3 specs de referência (Claude
Code, UserStyle Modes, Claude Fable 5) + mapa da raiz do LILO + análise de
lacunas por dimensão + crítica adversarial. Diagnóstico central: **o LILO já
tinha o esqueleto** (exec-modes, pipeline agêntico, memória, `quality_judge`),
mas **desconectado** — vários canais mortos. A V15 **liga a fiação**.

> Princípio: **tudo aditivo e default-safe.** Kill-switch único
> `LILO_PROMPT_BLOCKS=0` desliga os blocos de prompt; estilo/judge/verify vêm
> desligados por padrão. Zero regressão no comportamento atual.

## Status por fase

| Fase | Item | Status | Como ativar |
|---|---|---|---|
| **0** | `prompt_blocks.py` (honestidade + kill-switch + compose_system) | ✅ | sempre on (kill-switch `LILO_PROMPT_BLOCKS=0` desliga) |
| 0 | gateway consome `system_hint` (era morto) | ✅ | automático |
| 0 | memória de turno no chat do dashboard | ✅ | automático |
| **1** | gate de git (`git_write`, grant escopado) | ✅ | automático (sensível até em `auto`) |
| 1 | `SECURITY_BLOCK` (recusa proporcional) nas saídas | ✅ | on (kill-switch) |
| **2** | eixo de estilo (`config/styles.yaml` + `response_style.py`) | ✅ | seletor no dashboard ou `LILO_RESPONSE_STYLE` |
| 2 | `cot_suffix` não empurra mais verbosidade na saída | ✅ | automático |
| **3** | `quality_judge` opt-in pós-Reporter | ✅ | `LILO_QUALITY_CHECK=1` (só `complex`) |
| 3 | revival do `owner_verified` (memória do dono) | ✅ | automático quando a voz/sessão é verificada |
| 3 | destilação de fatos (`chat_memory.distill_facts`) | ✅ (função) | chamar a função (usa Ollama → GPU) |
| **4** | gate CENTRAL no orquestrador | ✅ | automático (default `auto` = no-op) |
| 4 | contrato do CLI (ask+stdin / auto scriptado) | ✅ | automático |
| 4 | estágio VERIFY (sandbox isolado) | ✅ (default-off) | `LILO_VERIFY_STAGE=1` |
| 4 | **exec_mode por-sessão + plano-aprovável** | ⏸️ **ADIADO** | — (ver abaixo) |
| **5** | scheduler do Cowork (executor de tarefas agendadas) | ✅ (default-off) | `LILO_ENABLE_SCHEDULER=1` + `scripts/run_scheduler.py --execute` |
| medição | `scripts/bench_prompts.py` (A/B) | ✅ | `python scripts/bench_prompts.py` (GPU) |

## Flags (.env)
```
LILO_PROMPT_BLOCKS=1        # kill-switch dos blocos de prompt (0 desliga tudo)
LILO_RESPONSE_STYLE=default # default|concise|explanatory|formal
LILO_QUALITY_CHECK=0        # juiz opt-in pos-Reporter (so complexity=complex)
LILO_QUALITY_MIN=60         # escore minimo; abaixo -> 1 refinada extra
LILO_VERIFY_STAGE=0         # roda codigo auto-contido do worker em sandbox
LILO_DISTILL_MODEL=         # modelo da destilacao de fatos (default 'fast')
LILO_ENABLE_SCHEDULER=0     # FASE 5: =1 permite execucao real do scheduler
LILO_SCHEDULED_DIRS=        # dirs com */SKILL.md (ha defaults do Cowork)
```

**Scheduler (FASE 5):** `python scripts/run_scheduler.py --list` (lista), sem
flag = dry-run, `--execute` (exige `LILO_ENABLE_SCHEDULER=1`) roda as tarefas
'due' sob perfil `cowork` (local-only, sem shell/python) + exec_mode `ask`,
gravando saidas em KVMemory `ns=lilo_tasks`. NAO ha loop sempre-ligado: ligue
via Windows Task Scheduler/cron chamando o script. Tarefas com `schedule:
manual` (default) nunca rodam sozinhas.

## Correções da crítica adversarial já incorporadas
1. **Medição** — `bench_prompts.py` (over-refusal / verbosidade / confabulação).
2. **Kill-switch + orçamento de tokens** — `LILO_PROMPT_BLOCKS`; blocos completos
   só nas saídas, honestidade "mini" nos estágios de raciocínio.
3. **Inversão de risco no git** — gate de git usa grant **escopado ao hash do
   cmd** (não o global), antes do refator de estado por-sessão.
4. **Prompt-injection** — memória do dono e fontes externas marcadas como DADO,
   não instrução; VERIFY nunca executa código de origem externa.
5. **Semântica do VERIFY** — só roda bloco **auto-contido** (stdlib, sem IO);
   **não** auto-corrige (código científico falha por ambiente, não por bug).
6. **Contrato do CLI** — `ask`+stdin no interativo; `auto` exigido p/ scriptado;
   erro acionável quando não há terminal.

## Item adiado da FASE 4 — RESOLVIDO (em parte) + decisão

- ✅ **"plan" como plano aprovável** — ENTREGUE: no modo `plan`, `gate()` acumula
  as ações bloqueadas; o dashboard mostra o plano e um botão **"Aprovar plano e
  executar"** (`pending_plan`/`approve_plan`/`clear_plan` em `shared/exec_mode.py`).
- ❌ **Refator `exec_mode` global → por-sessão (ContextVar)** — DESCARTADO por
  decisão de engenharia: risco de quebrar o modelo de *rerun* do Streamlit
  (estado por-thread pode não persistir entre reruns) **sem benefício real** num
  app pessoal single-user. O vazamento de grant multi-repo do git — a única
  preocupação concreta — já é evitado pelos **grants escopados** (FASE 1). Só
  valeria a pena se um dia houver execução concorrente multi-usuário/paralela.

## Não copiar do Claude (decisões)
- Não importar a maquinaria de recusa do chat público (wellbeing/menores/
  sócio-político) — app pessoal local; valor está na recusa **proporcional**.
- Não forçar `concise` global — o `report_prompt` do Villa é load-bearing p/
  deliverables; conciso só encurta a prosa.
- Não rodar o juiz em todo turno (satura a RTX 3060) — opt-in + gated.
- Cuidado com over-refusal em farmacologia/toxicologia (usuário é PhD em bio).
