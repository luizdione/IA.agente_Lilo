# Relatório IA LILO — 2026-06-11 (ciclo do protocolo semântico multi-domínio)

**Perfil:** `desktop_dev` | **Backend:** Ollama | **Harness:** `scripts/bench_semantic_domains.py --iters 1,2,3 --timeout 240`

---

## 1. Bug crítico encontrado e corrigido: `keep_alive` rejeitado pelo Ollama (400)

A primeira corrida do dia falhou em **27/27 execuções** (qualidade média 5.0, tempos de 6–9s
— falha rápida). Evidência preservada em
`docs/relatorios/bench_semantic_2026-06-11_bug_keepalive400.json`.

**Causa raiz:** a variável de ambiente do Windows `OLLAMA_KEEP_ALIVE=-1`
(escopo usuário **e** máquina) sobrepõe o `.env` (`2h`). O `shared/llm_client.py`
enviava o valor como **string** `"-1"` no payload de `/api/chat`, e a versão
atual do Ollama rejeita duração sem unidade:

```json
{"error": "time: missing unit in duration \"-1\""}
```

**Correção:** `LLMClient._normalize_keep_alive()` — strings numéricas ("−1", "300")
são convertidas para `int` (aceito pelo Ollama; −1 = manter na VRAM para sempre);
durações com unidade ("2h", "30m") passam intactas. O fallback de planner/worker
também falhava pelo mesmo motivo (o payload é compartilhado), por isso nenhuma
retentativa salvava a corrida.

**Lição de protocolo:** o circuit-breaker de retry/fallback do Villa não protege
contra erro *de payload* (4xx) — todas as rotas morrem igual. Vale distinguir
4xx (não adianta retry com outro modelo) de 5xx/timeout (adianta).

## 2. Resultado do ciclo (pós-correção) vs corrida anterior (2026-06-10)

| Métrica | 06-10 | 06-11 | Leitura |
|---|---|---|---|
| Corridas | 27 | 27 | — |
| Bugs | 0 | **0** | recuperado do estado 27/27 |
| Travamentos (froze) | 0 | 0 | guarda portável OK |
| Qualidade média | 72.4 | 71.1 | estável (ruído) |
| Wall iter 1 | 55.4s | 57.6s | estável |
| Wall iter 2 | 76.2s | 72.2s | levemente melhor |
| Wall iter 3 | 82.5s | **113.1s** | pior — ver observação |

**Observação iter 3:** a média foi puxada por `matematica` (204s) e
`conhecimentos_gerais` (175s). A corrida ocorreu em paralelo com o dashboard
Streamlit + ferramentas de desenvolvimento ativas (contenção de CPU/VRAM);
repetir o ciclo em máquina ociosa antes de concluir regressão.

**Piores qualidades (64–66):** física it1 (fast-path), veterinária it1,
história it1, geografia it1/it3 (fast-path), agropecuária it2.

## 3. Achado de roteamento (alvo do próximo ciclo)

**As 27 corridas roteiam para `route_domain=geral`** — os especialistas dos
9 domínios de `agents/villa_lobos/domains.yaml` nunca são selecionados, nem
para consultas claramente especializadas (química, veterinária, matemática).
Próximo ciclo: revisar o classificador de domínio do orquestrador
(keywords/threshold) e medir se a delegação a especialista melhora a qualidade
dos domínios com pior score (física/geografia caíram em fast-path com q=64–65).

## 4. Demais entregas do dia (contexto do ciclo)

- **Limpeza v10**: `lilo_server.py`, `obsoletos/`, `memory/Dockerfile` e scripts
  one-shot arquivados em `_ARCHIVE_v10/`; relatórios da raiz de `docs/` movidos
  para `docs/historico/`; caches (`__pycache__`, pytest) removidos; pasta-lixo
  `C:` (notas Obsidian de 20–23/05, anteriores ao guard `is_absolute`) resgatada
  para o vault real e removida.
- **Dashboard v10.10**: tema "Claude Desktop" (marfim `#FAF9F5`, sidebar creme
  ghost, acento coral `#D97757`, headings serifados, composer arredondado);
  estados ativos corrigidos via seletor `.st-key-*` (os wrappers `<div>` nunca
  envolviam os botões no DOM do Streamlit).

## 5. Próximas ações

1. Corrigir classificador de domínio do Villa (nenhuma delegação a especialista).
2. Repetir bench em máquina ociosa p/ baseline limpa de iter 3.
3. Distinguir 4xx de 5xx no retry/fallback do pipeline (fail-fast em 4xx com
   mensagem acionável).
4. Avaliar elevar o score de fast-path (físíca/geografia ficaram em 64–65 sem
   pipeline completo).
