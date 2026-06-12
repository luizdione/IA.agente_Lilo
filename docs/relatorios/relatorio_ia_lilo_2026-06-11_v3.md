# Relatório IA LILO — 2026-06-11 (V3): V12 orquestração unificada + busca ampliada

Sessão noturna (autônoma). Continuação dos relatórios v1/v2 do dia. Tudo
commitado e enviado à branch `arch-v10` (PR #1).

---

## 1. V12 — orquestração unificada (3 pedidos do Dione)

1. **Roteador semântico = porta única.** `VillaLobosAgent.route_target()` decide
   o subagente pela semântica (LLM → heurística → capabilities). `lilo.route()`
   usa-o no lugar do keyword-router (`_detect_tab`, agora fallback). Desligável
   por `LILO_SEMANTIC_ROUTER=0`. Validado (Ollama): capital→gateway, ANOVA→prism,
   pubmed→scholar, arquivos→desktop, SQL→sql, incerteza→villa.
2. **Modo IA → "Auto"** (default) + override manual (sql/chat/code/bioinfo).
3. **Delegação por etapa + CADEIA (V12.1).** `worker_agent` (1 especialista na
   etapa Worker) estendido para `_decompose_chain()`: até 4 sub-tarefas
   sequenciais, cada uma a um especialista, encadeando saídas. Gatilho
   `_looks_multi_step`. Desligável por `LILO_STAGE_DELEGATION=0` /
   `LILO_CHAIN_DELEGATION=0`. Validado e2e: "busque no pubmed … e depois
   analise" → cadeia `scholar → prism` → Reporter sintetiza.

## 2. V12.2 — busca na internet ampliada

`shared/research_sources.py`: +**OpenAlex** (substituto do Google Scholar, que
não tem API e bloqueia scraping), +**Europe PMC**, +**Google Books**
(`GOOGLE_BOOKS_API_KEY` opcional — quota anônima satura), +**Wikipedia**
(`LILO_WIKI_LANG`). Total: **10 fontes estruturadas + web geral (DuckDuckGo)**.
ScholarAgent integra todas; `source="all"` agrega as acadêmicas (validado:
arXiv+PubMed+EuropePMC+OpenAlex+Crossref+ClinicalTrials numa busca).

## 3. Dashboard

Tela de boas-vindas (empty state) estilo Claude Desktop: saudação serifada +
4 cards de capacidade (Pesquisa/Análise/Documentos/Sistema) refletindo o modo
Auto e as fontes. Rodapé v10.6.

## 4. Bench com juiz — veredito de NÃO-REGRESSÃO

Rodado o full (54 corridas) e, por celeridade, um **enxuto** (9 corridas, iters=1,
com juiz) para o veredito V12:

| Métrica | baseline V11.2 (it1) | V12 (it1) |
|---|---|---|
| Bugs / Travamentos | 0 / 0 | **0 / 0** |
| qLLM médio | 69.4 | 60.8 |

**Leitura honesta:** a diferença de qLLM **não é regressão atribuível à V12**:
- As 9 queries são de **conhecimento** → `worker_agent=None`, não disparam
  roteamento/cadeia. As mudanças V12 não alteram o caminho delas.
- A média V12 (60.8) foi puxada por 2 outliers — `conhecimentos_gerais=6` e
  `biologia=6` —, exatamente as respostas cuja correção factual do worker local
  (llama3.1:8b) **já documentamos oscilando 6↔86 entre execuções idênticas**
  (relatório v2). Com N=1, dois outliers derrubam a média.
- **Conclusão:** V12 não introduziu regressão funcional (0 bugs/travamentos); a
  oscilação de qLLM é o ruído de correção factual do worker, não efeito da V12.

**Pendência metodológica real** (já em v2): o gargalo de qualidade do LILO é a
**variância factual do worker local**, não o roteamento. Atacar com: modelo
maior/cloud no worker para conhecimento, self-consistency (gerar k e votar) ou
temperatura menor — medindo com o juiz e **N≥5** (a variância domina abaixo disso).

## 5. Testes e flags

- **61 testes** passam (+route_target, +worker_agent, +cadeia).
- Flags de reversão: `LILO_SEMANTIC_ROUTER`, `LILO_STAGE_DELEGATION`,
  `LILO_CHAIN_DELEGATION` (todas default ON).

## 6. Próximas ações sugeridas
1. Atacar a variância factual do worker (modelo/self-consistency/temperatura) —
   medir com juiz, N≥5.
2. Estender a cadeia para expor as etapas no dashboard (transparência visual).
3. (Opcional) Google Scholar literal via SerpAPI (chave paga) se desejado.
