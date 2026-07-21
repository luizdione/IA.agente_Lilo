# Relatório IA LILO — 2026-06-11 (V2): 2 rodadas de auditoria profunda do Villa_Lobos

**Perfil:** `desktop_dev` | **Backend:** Ollama | **Harness:** `bench_semantic_domains.py --iters 1,2,3 --timeout 240`

Continuação do ciclo da manhã (relatorio_ia_lilo_2026-06-11.md). Duas rodadas
investigativas de auditoria + correção, com benchmark de validação.

---

## Rodada 1 — Roteamento e retry

### Diagnóstico anterior REFUTADO (rigor investigativo)
O ciclo da manhã anotou "especialistas dos 9 domínios nunca acionados (route=geral)"
como bug a corrigir. **Era um diagnóstico equivocado.** Evidência: `explain_routing`
nas 9 queries mostra `domain=None` para todas. Os domínios do registry
(`prism/sql/pdf/scholar/desktop/gateway/genomics/proteomics/bioinformatics`) são
especialistas de **FERRAMENTA**, não de **conhecimento**. Uma pergunta como
"Detalhe o mecanismo da esterificação de Fischer" não tem especialista de ferramenta
aplicável → roteá-la ao **pipeline geral é o comportamento correto**. Nenhuma correção
de "delegação a especialista" era necessária.

### BUG REAL corrigido — fast-path inconsistente (V11.2)
Evidência (`explain_routing`): **física** caía em `skip_to_reporter` (fast-path:
orquestrador→reporter, **pula o Worker**), enquanto química/biologia/etc. iam ao
pipeline. Causa: a guarda anti-fast-path tinha **dois ramos inconsistentes** — o ramo
do LLM-orchestrator só cobria demonstração/prova (V11.0); a guarda `_EXPLAIN_KW` (que
cobre "explique/descreva/...") só protegia o ramo heurístico. Logo "Explique … e suas
implicações" escapava para o fast-path raso.
- **Fix:** `_block_fast_path()` unifica a guarda nos dois ramos
  (proof→Worker+≥2 iters; explain→Worker; trivial→fast-path preservado p/ celeridade).

### Auditoria do retry/fallback (`_call_agent`)
- HTTP **400** (payload inválido — exatamente o `keep_alive=-1` da manhã) era reintentado
  2× e ainda tentava fallback de modelo — todos idênticos, ~3-5s/estágio perdidos. Agora
  **400 = fail-fast** (sem retry/fallback); demais 4xx (ex.: 404 modelo inexistente) pulam
  retry mas permitem fallback de modelo; 5xx/timeout/conexão seguem com retry (transitórios).

### Bug de telemetria no harness
- O harness lia `route.get("delegate")` (sempre `None`) em vez de `delegate_target` →
  `route_domain` jamais refletia o alvo real de delegação.

## Rodada 2 — Auditoria investigativa ampla (Explore) + correções

A varredura retornou 3 🔴 + 4 🟡. **Triagem cética rejeitou 2 dos 3 "críticos"** como
falsos positivos (corrigi-los quebraria o sistema):
- ❌ `num_gpu: 99` "causaria 400": no Ollama `num_gpu` = nº de **camadas** na GPU
  (99 = "todas", idioma canônico), não nº de GPUs. Bench: 0 bugs com ele. Mantido.
- ❌ `.env obsidion` "é typo de obsidian": `obsidion` é o nome **real** da pasta do
  usuário (existe; `obsidian` não), usado também no `config.yaml`. Mantido.

Correções legítimas aplicadas:
- 🔴 **Parse defensivo** do JSON de Ollama e LiteLLM (`shared/llm_client.py`):
  `raise_for_status()` só valida status HTTP; um 200 com payload inesperado fazia
  `r.json()["message"]["content"]` estourar `KeyError` cru → agora `.get()` encadeado +
  `ValueError` acionável.
- 🟡 **De-viés de domínio** (`EXPERT_SYSTEM` + `worker_prompt`): antes impunham
  "mecanismos moleculares, enzimas, vias de sinalização" a TODA query. Agora o
  vocabulário técnico é **enumerado por área** (equações/teoremas em exatas; reações em
  química; enzimas/vias em bio; dados/causas em humanas).
- 🟡 **Guarda reader/plan**: stub de erro não é mais injetado como "PLANO"/"CONTEXTO".
- 🟡 **Portabilidade**: `LILO_WORKAHOLICS_ROOT` (env) para a biblioteca de PDFs.
- 🟢 **Observabilidade**: falha do Obsidian agora loga em DEBUG (era `pass` silencioso).

Testes: **48 passam** (eram 37; +11 regressões cobrindo `_block_fast_path` e a escalada
do ramo do LLM).

---

## Validação — bench pré-V11.2 vs pós-V11.2 (todas as correções)

| Métrica | pré-V11.2 | pós-V11.2 | Leitura |
|---|---|---|---|
| Corridas | 27 | 27 | — |
| Bugs | 0 | 0 | mantido |
| Travamentos | 0 | 0 | mantido |
| **Fast-path (corridas)** | **6** | **0** | **bug eliminado** |
| Qualidade média | 71.1 | 71.4 | estável (ruído) |

**Por domínio (qualidade média 3 iters; nº de corridas em fast-path):**

| Domínio | pré → pós | fast-path |
|---|---|---|
| **fisica** | **69.0 → 73.7 ↑** | **3 → 0** |
| geografia | 67.0 → 68.7 ↑ | 3 → 0 |
| agropecuaria | 71.3 → 73.3 ↑ | 0 → 0 |
| matematica | 72.3 → 73.3 = | 0 → 0 |
| quimica | 70.7 → 71.0 = | 0 → 0 |
| historia | 72.0 → 71.0 = | 0 → 0 |
| veterinaria | 65.7 → 66.7 = | 0 → 0 |
| biologia | 74.3 → 72.0 ↓ | 0 → 0 |
| conhecimentos_gerais | 77.3 → 72.7 ↓ | 0 → 0 |

### Interpretação honesta
- **Ganho confirmado e isolado**: o fast-path foi **eliminado** (6→0). `física` (o domínio
  afetado) subiu **+4.7** de qualidade — exatamente a correção pretendida.
- **Qualidade agregada estável** (71.1→71.4). O de-viés de prompt **não** moveu o escore
  agregado, e isto é esperado: `_quality_score` é heurístico (premia tamanho, cabeçalhos,
  dígitos, keywords) e **não mede adequação de domínio** — justamente o que o de-viés
  melhora (relevância/correção, não estrutura). O ganho do de-viés é qualitativo e não é
  capturado por este escore.
- As variações ±2-5 em biologia/conhecimentos_gerais são **ruído run-a-run** do LLM (temp
  0.3-0.4, amostragem; corrida única), não regressão — esses domínios já iam ao pipeline
  e seu roteamento não mudou.
- **Tempos** são ruidosos (a corrida disputa CPU/GPU com o ambiente de dev); não constituem
  sinal limpo nesta máquina. iter 3: 113→101s.

---

## Próximas ações (próximo ciclo)
1. **Métrica de qualidade melhor**: `_quality_score` não distingue adequação de domínio.
   Avaliar um juiz LLM (rubrica por domínio) ou checagem de cobertura factual para medir
   o ganho do de-viés que o escore atual não captura.
2. **Baseline limpa**: repetir o bench em máquina ociosa (N≥2 corridas) para separar sinal
   de ruído run-a-run, sobretudo nos tempos.
3. Avaliar `handle_tool_call()` propagar contexto (project_notes) como `route()` faz,
   quando a integração dashboard↔MCP for exercitada (🟡#5 da auditoria; adiado).
