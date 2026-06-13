# Experimento — alavancas de qualidade do Worker (juiz LLM) — 2026-06-12

**Pergunta:** qual alavanca reduz a variância factual do Worker local? Comparados
3 braços × 3 domínios (que sofriam) × N=4, avaliados pelo juiz (`quality_judge`).

## Resultado (qLLM 0-100; média das 4 repetições)

| Config | biologia | conhecimentos | química | **média** | tempo/corrida |
|---|---|---|---|---|---|
| baseline (llama3.1:8b) | 6 | 57 | 5.5 | **22.8** | 84s |
| self-consistency (8b ×3) | 6 | 81.7 | 24.2 | **33.3** | 177s |
| **worker cloud (gpt-oss:120b)** | 5.5 | 62.5 | **73.8** | **47.2** | 88s |

## Conclusões

1. **Worker cloud é a melhor alavanca** — média **47.2 vs 22.8** do baseline
   (+107%), e **sem custo de tempo** (88s ≈ baseline 84s, pois o 120b cloud
   responde rápido). O salto em **química (5.5 → 73.8)** é decisivo: o 8b local
   não domina esterificação de Fischer; o 120b sim. **Recomendado como default
   para conhecimento/ciência** (`VILLA_WORKER_GENERAL_MODEL=gpt-oss:120b-cloud`).
2. **Self-consistency ajuda** (33.3 vs 22.8), sobretudo onde o modelo *sabe mas
   varia* (conhecimentos 57 → 81.7), mas **custa 2× o tempo** (177s). Vale como
   alternativa quando o cloud não está disponível; pior custo-benefício que o cloud.
3. **Refuta a hipótese do "reporter local"**: química melhorou muito só trocando
   o *worker* (reporter seguiu local) — logo o **worker é o gargalo**, não o reporter.

## ⚠️ Anomalia a investigar (honestidade)

**Biologia ficou ~6 em TODOS os braços, incluindo o cloud 120b** — o que é
implausível (o 120b certamente sabe replicação de DNA). Como química e
conhecimentos pontuaram alto, o juiz e o pipeline funcionam; é provável um
**artefato do juiz (phi3) nessa query específica** ou um problema na resposta
de biologia (truncamento/formato). No bench anterior (N=2) biologia oscilou
6↔86, reforçando que é instabilidade de avaliação, não de conhecimento.
**Ação:** inspecionar 1 resposta crua de biologia + trocar o juiz por um modelo
mais forte (cloud) antes de qualquer conclusão sobre biologia.

## Recomendação operacional
- Ligar `VILLA_WORKER_GENERAL_MODEL=gpt-oss:120b-cloud` por padrão (melhor
  qualidade, mesmo tempo) — já documentado no `.env.example`.
- Manter `LILO_WORKER_SC` como fallback (sem cloud).
- Próximo ciclo: **juiz cloud** (gpt-oss:120b como `LILO_JUDGE_MODEL`) + N≥5
  para resolver a anomalia da biologia e medir com menos ruído.
