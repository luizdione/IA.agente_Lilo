# Relatório — Tarefa agendada `ia_lilo`
**Data:** 2026-06-07 · **Execução:** autônoma (usuário ausente) · **Perfil de teste:** `desktop_dev` (teto de iterações = 3)

Escopo do ciclo: protocolo de teste semântico multi-domínio do LILO/Villa-Lobos; verificar erros em scripts e corrigir; analisar qualidade, bugs e tempo em 1/2/3 iterações; comparar com a corrida anterior; solucionar problemas de roteamento/prompts/circuit breaker/timeouts; gerar versão mais potente do LILO; registrar achados na memória (`project_ia_lilo`) e em `docs/`.

> **Ambiente:** sandbox em **modo degradado (backend `mock`)** — sem Ollama nem rede LLM (`http://localhost:11434` indisponível). Mede *roteamento*, *travamento*, *autocorreção* e *integridade de código*, **não** a qualidade real do conteúdo (exige Ollama quente no FS nativo).

---

## 1. Verificação de scripts — sintaxe

Checagem de sintaxe (`ast.parse`) em **todos os 267 arquivos `.py`** do projeto (excluídos `_ARCHIVE_v10`, `obsoletos`, caches): **0 erros**. Base de código íntegra; nenhuma quebra herdada de ciclos anteriores.

> Nota metodológica: `py_compile` falsamente acusou erros porque o sandbox tentou gravar `.pyc` em `__pycache__` copiado como somente-leitura (`Permission denied`) — não são erros de sintaxe. Trocado para `ast.parse` (não grava `.pyc`): 267/267 limpos.

---

## 2. Desenvolvimento contínuo deste ciclo — P1 RESOLVIDO: write-atômico em `fs_write` (V10.8)

O item **P1** (write-atômico abrangente) vinha sendo sinalizado há 3 ciclos (relatórios 06-04/05/06) como causa-raiz do truncamento recorrente que corrompeu `agent.py`. Este ciclo **atacou a origem**.

**Causa-raiz localizada.** O primitivo de persistência de arquivos é `fs_write` em `agents/desktop/agent.py` (exposto via `lilo_mcp.fs_write`). No caminho de **sobrescrita** ele fazia gravação **direta no arquivo-alvo**:

```python
mode = "a" if append else "w"
with open(p, mode, encoding="utf-8") as f:
    f.write(content)
```

Se a escrita é interrompida no meio (limite de créditos, crash, kill), o `open(p, "w")` **já truncou** o arquivo original mas o `f.write` não terminou → arquivo meio-escrito/corrompido. É exatamente o modo de falha responsabilizado pela corrupção de `agent.py` nos ciclos anteriores.

**Correção (V10.8).** Sobrescrita agora é **atômica** (tmp + `fsync` + `os.replace`); append mantém semântica O_APPEND:

```python
if append:
    with open(p, "a", encoding="utf-8") as f:
        f.write(content)
else:
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, p)                       # rename atômico
```

Com `os.replace` (rename atômico no mesmo FS), o arquivo-alvo **nunca** fica num estado intermediário: ou ele tem o conteúdo antigo completo, ou o novo conteúdo completo. Em falha, limpa o `.tmp` órfão.

**Validação funcional (FS nativo, 4 casos):**

| Caso | Resultado |
|---|---|
| 1. write inicial | conteúdo gravado OK |
| 2. sobrescrita | atômica, **sem resíduo `.tmp`** |
| 3. append | preserva conteúdo anterior |
| 4. **interrupção simulada** (`os.replace` lança no meio) | **arquivo original intacto** + **`.tmp` órfão removido** |

Sintaxe do arquivo reconstruído (445 linhas) confirmada (`ast.parse` OK). Esta correção fecha o vetor de corrupção na **origem** — todo agente/skill que persiste via `fs_write` herda a garantia atômica. Soma-se à proteção já existente no `bench_semantic_domains.py` (que adotou tmp+`os.replace` em 06-04).

---

## 3. Bench semântico multi-domínio (2026-06-07)

`scripts/bench_semantic_domains.py --iters 1,2,3`, perfil `desktop_dev`, 9 domínios × 3 = **27 corridas**. JSON: `docs/relatorios/bench_semantic_2026-06-07.json`.

| Data | Corridas | Travou | Bugs reais | Degradado | Qual. média (mock) | Tempo 1/2/3 (s) | Roteamento |
|---|---|---|---|---|---|---|---|
| 2026-06-04 | 27 | 0 | 0 | 27 | 5,0 | 0,017 / 0,016 / 0,020 | pipeline |
| 2026-06-05 | 27 | 0 | 0 | 27 | 5,0 | 0,014 / 0,015 / 0,018 | pipeline |
| 2026-06-06 (V10.7) | 27 | 0 | 0 | 27 | 5,0 | 0,057 / 0,042 / 0,045 | pipeline (uniforme) |
| **2026-06-07 (V10.8)** | **27** | **0** | **0** | **27** | **5,0** | **0,004 / 0,002 / 0,002** | **pipeline (uniforme nos 9)** |

**Leitura:** roteamento **uniforme e estável** — `path = pipeline`, `route_domain = geral` para todos os 27. **0 travamento, 0 bug real** em todas as corridas. O fix V10.7 (honestidade de telemetria, `effective_retries`) **confirmou-se em produção dos logs**: cada estágio reportou `falhou apos 1 tentativa(s)` (antes da correção: enganoso "2 tentativas"). Tempos em mock são ruído sub-ms (circuito sem LLM real); a curva 1→2→3 permanece plana — esperado em mock. O fix V10.6 (química não desviando para `desktop` via substring) segue **sem regressão**.

---

## 4. Observação de telemetria (recorrente, não-fatal) — P4

Durante o bench, o `CostTracker` emitiu repetidamente `attempt to write a readonly database` (SQLite em FS restrito do sandbox). É **não-fatal** (a telemetria degrada graciosamente, o pipeline não trava), mas reforça o item **P4**: bufferizar o `CostTracker` em memória e fazer *flush* retentável, evitando ruído de log e perda de telemetria quando o DB está bloqueado/somente-leitura.

---

## 5. Limitação de ambiente (recorrente, contornada)

O mount do OneDrive serviu **leituras truncadas** de arquivos cloud-only ao runtime do sandbox: `agents/villa_lobos/agent.py` cortado na linha 1062 (real = 1067) e `agents/desktop/agent.py` cortado na linha 418 (real = 445). As ferramentas **Read/Edit** (autoritativas) acessam os arquivos íntegros — as correções foram gravadas e **confirmadas por leitura**. Validações de execução feitas em cópias no **FS nativo**, reconstituindo a cauda truncada a partir do conteúdo autoritativo. 4ª ocorrência no mês; a correção V10.8 ataca a causa do truncamento **de escrita** (a de leitura é artefato do mount OneDrive, fora do código).

---

## 6. Desenvolvimento contínuo — fila priorizada

1. **Ollama quente, FS nativo:** rodar o bench medindo **qualidade real** do conteúdo e o **delta de tempo** 1 vs 2 vs 3 iterações (em produção ≈ +1 chamada do Worker por iteração extra). Único passo capaz de validar o objetivo central do protocolo.
2. **~~P1 — write-atômico~~ ✅ RESOLVIDO (V10.8):** `fs_write` agora atômico (tmp+fsync+os.replace). Follow-up: estender o mesmo padrão a quaisquer persistências de config remanescentes que ainda usem `open(...,"w")` direto.
3. **P2 — plataforma híbrida (API ~ Claude Desktop):** paridade de tool-calling entre `lilo_api.py` (SSE stage-a-stage) e `lilo_mcp.py`; seleção de perfil por header/JWT reusando `get_profile_policy()`.
4. **P3 — Villa como "LLM chamando agentes":** fan-out (delegar a >1 especialista + Reporter sintetiza) e *early-stop* quando Worker N ≈ N-1 (similaridade).
5. **P4 — telemetria resiliente:** `CostTracker` com buffer em memória + flush retentável (SQLite em FS restrito loga `disk I/O error`/`readonly database` — visto de novo neste ciclo).
6. **Testes de regressão:** travar (a) formato da msg de erro em modo degradado (`[role ERRO apos 1 tentativas: ...]`, V10.7) e (b) atomicidade de `fs_write` (original intacto + sem `.tmp` órfão sob falha, V10.8), assim que `pytest` rodar no FS nativo.

---

## 7. Resumo executivo

Base íntegra (**267/267 `.py` com sintaxe válida**). **P1 resolvido (V10.8):** identificada a causa-raiz do truncamento recorrente — `fs_write` (em `agents/desktop/agent.py`) sobrescrevia o arquivo-alvo diretamente, deixando-o corrompido se a escrita fosse interrompida; trocado por **sobrescrita atômica** (tmp + `fsync` + `os.replace`) com limpeza de órfão. Validado em 4 casos no FS nativo, incluindo interrupção simulada (original intacto, sem `.tmp` órfão). Bench semântico **27/27 em pipeline, roteamento uniforme nos 9 domínios, 0 travamento, 0 bug real**; o fix V10.7 (telemetria honesta) confirmou-se nos logs (`falhou apos 1 tentativa(s)`). `CostTracker` voltou a logar `readonly database` no sandbox (não-fatal, reforça P4). Recorreu o truncamento de leitura do mount OneDrive (`villa_lobos/agent.py` e `desktop/agent.py`), contornado via Read autoritativo + cópia em FS nativo. Achados gravados na memória `project_ia_lilo` (`bench_semantico_2026-06-07_achados`). **Próximo ciclo:** Ollama quente para medir ganho real de conteúdo; atacar P2 (paridade API↔MCP) e P4 (telemetria bufferizada).
