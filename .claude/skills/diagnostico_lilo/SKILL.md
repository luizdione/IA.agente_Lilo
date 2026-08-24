---
name: diagnostico_lilo
description: Auditoria e diagnóstico do LILO em todos os níveis (código, fiação, envs, runtime, docs) com plano de correção priorizado, espelhado no padrão-ouro Claude Code. Use quando o usuário pedir diagnóstico, auditoria, saúde do LILO, "o que está quebrado/faltando", ou antes de uma rodada de correções e melhorias.
---

# /diagnostico_lilo — auditoria com economia de tokens

## Princípio (leia antes de agir)

A varredura pesada é **determinística e grátis**: `scripts/diagnostico_lilo.py`
audita tudo sem LLM e devolve um relatório compacto com achados identificados
(`[nivel][ID] mensagem`). Seu papel NÃO é re-explorar o repositório — é
**interpretar o relatório** e transformá-lo num plano de correção priorizado.

Regras de economia de tokens (obrigatórias):

1. **UM comando primeiro, nada antes dele:** `python scripts/diagnostico_lilo.py`
   (adicione `--fast` se os testes já rodaram nesta sessão; `--no-runtime` em
   ambiente sem Ollama; `--json diag.json` se precisar da lista completa).
2. **Não re-derive o que o script já checou.** Sintaxe, imports do registro,
   tools dos profiles, envs mortas, drift de versão — o relatório é a fonte.
   Só abra um arquivo se um achado exigir contexto de linha para propor o fix.
3. **Cite achados pelos IDs do relatório** (ex.: `B-REG-AUSENTE`, `E-VERSAO`)
   — não re-descreva o que o ID já diz.
4. **Não aplique correções** — o entregável é o PLANO. Corrija só se o usuário
   pedir em seguida (aí, um achado por commit, revalidando com o script).
5. Gaps já conhecidos do roadmap **não são redescobertas**: confira
   `docs/tecnico/analise_open_agent_studio.md` (seções H1/H2/H3 têm blocos de
   Status) e encaixe achados novos RELATIVOS ao que já está planejado.

## Protocolo

1. Rode o script (regra 1). Exit code: 2=há P0, 1=há P1, 0=limpo.
2. Se `pytest` falhou (A-PYTEST): rode SÓ os testes falhos com
   `python -m pytest <arquivo>::<teste> -q` para obter o traceback — nunca a
   suíte inteira de novo.
3. Monte o **Plano de correção e melhorias** neste formato:

   ```
   ## Diagnóstico LILO — <data>
   Resumo: P0=<n> P1=<n> P2=<n> (script exit=<rc>)

   ### P0 — corrigir agora (quebra real)
   - <ID>: problema → correção proposta (arquivo:linha) → esforço (S/M/L)

   ### P1 — próxima sessão (dívida com risco)
   ...

   ### P2 — higiene (lote único quando conveniente)
   ...

   ### Melhorias vs padrão-ouro (ver rubrica abaixo)
   - <dimensão>: estado atual → passo seguinte (referencie E1..E8/S1..S5 do
     roadmap quando o item já existe lá)
   ```

4. Termine com UMA recomendação: o item de maior valor/menor esforço.

## Rubrica padrão-ouro (Claude Code, estado da arte)

Benchmark permanente para a seção de melhorias — compare o estado do LILO em
cada dimensão com o equivalente do Claude Code e aponte o próximo degrau:

| Dimensão (Claude Code)                  | Equivalente LILO                        | Referência de evolução |
|---|---|---|
| Permissões/modos (plan/ask/accept/auto) | `shared/exec_mode.py` + gates (`git_write`, `cloud_send`) | E5 concluiu o gate cloud; falta scrubber de segredos |
| Memória persistente (CLAUDE.md, auto-memory) | `kv_memory` + `notes.md` + `dir_synthesis` (E4) | E2 (busca semântica no KV) → E3 (`memory_facade`/`lilo_recall`) |
| Skills (SKILL.md, carga automática)     | `lilo_skills/` (registry 199 + CORE)    | lifecycle por skill (S3 manifest loader) |
| Subagentes/orquestração                 | `agents/` + Villa (orchestrator→reporter, chain) | handoff tipado entre steps (E7) |
| Telemetria custo/latência real          | `cost_tracker` (usage real QW4, p50/p95 QW5) | alerta 80% budget; custo por conversa |
| Roteamento por modelo/custo/contexto    | Policy Engine + `model_catalog` (E1)    | enforcement de `ctx["_model"]` + validação de boot (E1b) |
| Testes/CI                               | `scripts/check.py` + workflow tests.yml | cobertura dos fluxos MCP (test_mcp_stdio no CI) |
| MCP (cliente + servidor)                | servidor maduro (53 tools, perfis); **cliente não existe** | E6 (`shared/mcp_client.py`) |
| Contexto de projeto (auto-injeção)      | `dir_synthesis` manual (botão)          | E4b: refresh automático por mtime |
| Workflow dev (edita→testa→commita→docs) | peças soltas (verify-stage, git gate, notes.md) | E7 (`LILO_DEV_WORKFLOW=1`) |

## Saída esperada

Só o plano (formato do item 3) — sem despejar o relatório bruto (o usuário
pode rodar o script sozinho). Total alvo: < 60 linhas.
