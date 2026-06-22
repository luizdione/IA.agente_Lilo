# ScholarAgent — Gate de Verificação Factual

Implementação do **gate de verificação factual** do ScholarAgent: impede que qualquer
afirmação, número ou citação seja exportado sem estar **ancorado em um chunk-fonte
verificável** da biblioteca, com **revisão humana** antes de toda saída externa.

> Fecha a lacuna do pipeline RAG original: hoje gera-se texto com marcadores `[1][2]`,
> mas nada confere que a afirmação corresponde ao trecho citado.

## Pipeline

```
texto gerado ─► extrai claims ─► ancora em evidência (NLI) ─► confere citações [n]
            ─► confere números (tolerância zero) ─► política PASS/REVIEW/BLOCK
            ─► revisão humana ─► (só se aprovado) export/
```

A **regra de ouro**: o gate nunca auto-publica. `export.guard.can_export()` só libera
com `decision == PASS` **e** `human_approved == True`.

## Design testável

Tudo local e **injetável**: o juiz LLM (`make_ollama_judge`, Lilo 3.0 na porta 11435) e o
reranker (`bge-reranker-v2-m3`) entram por injeção de dependência. O núcleo
(extração de claims, checagem numérica/citação, política, auditoria) é **stdlib puro**,
então os testes rodam sem Ollama, ChromaDB ou reranker.

## Rodar os testes

```bash
python -m pytest -v        # núcleo sem dependências externas
```

## Estrutura

```
scholaragent/
├── verify/
│   ├── contracts.py        # Claim, Evidence, ClaimResult, GateReport, enums
│   ├── claim_extractor.py  # rule-based (determinístico) + modo LLM opcional
│   ├── grounding.py        # reranker (triagem) + juiz NLI (alto risco)
│   ├── citation_checker.py # citação órfã / fonte mal atribuída
│   ├── numeric_checker.py  # números do claim ⊆ números da fonte
│   ├── policy.py           # decisão conservadora PASS/REVIEW/BLOCK
│   ├── gate.py             # orquestrador
│   ├── ollama_judge.py     # juiz NLI local (httpx lazy)
│   └── audit.py            # trilha JSON (disclosure de IA / reprodutibilidade)
└── export/
    └── guard.py            # can_export / assert_exportable
```

## Uso (com infra completa)

```python
from scholaragent.verify import Grounder, VerificationGate, make_ollama_judge

judge = make_ollama_judge()                 # Lilo 3.0 / Ollama local
gate = VerificationGate(Grounder(judge=judge, reranker=meu_reranker))
report = gate.verify(content_id, pergunta, texto_gerado, chunks_usados, ref_to_evidence)
if report.decision.value == "block":
    ...  # editar fonte ou texto antes de revisar
```
