# Relatório IA LILO — 2026-06-11 (V3): juiz LLM por domínio + achado de variância factual

**Setup:** `bench_semantic_domains.py --iters 1,2,3 --repeat 2 --judge` (54 corridas;
juiz = `phi3:14b` @ temp 0). Perfil `desktop_dev`, backend Ollama.

## Totais

| Métrica | Valor |
|---|---|
| Corridas | 54 (9 domínios × 3 iters × 2 reps) |
| Bugs / travamentos | 0 / 0 |
| Qualidade **heurística** (`_quality_score`) | 70.6 |
| Qualidade **juiz LLM** | 62.8 |

**Baseline de tempos (N=2, média ± desvio):** it1 78±26s · it2 94±29s · it3 120±27s.
Desvios ~30% — máquina contendida + variância de pipeline.

## Achado central: variância factual do Worker (não roteamento/estrutura)

O juiz revelou o que o escore heurístico **mascarava por completo**. Por
iteração, a divergência heurístico−juiz foi: it1 = 0.8, **it2 = 20.2**, it3 = 2.1.
Investigando os reps individuais (mesma query, mesma config):

| Domínio×iter | reps (juiz) |
|---|---|
| biologia it1 | **[86, 10]** |
| biologia it3 | [6, 73] |
| química it1/it2/it3 | [63,6] / [5,79] / [6,79] |
| matemática it2 | [96, 6] |
| física it2 | [86, 3] |

**11 de 27 células têm reps divergindo ≥25 pontos.** As justificativas do juiz
oscilam entre "informações precisas" e "informações factualmente incorretas e
invenções". Ou seja: **o Worker (`llama3.1:8b` @ temp 0.4) gera, para a MESMA
pergunta, ora resposta precisa ora resposta com invenções factuais.** Esse é o
problema de qualidade central do LILO hoje — e o `_quality_score` heurístico era
cego a ele (premia tamanho/cabeçalhos/dígitos, ficava ~70 constante).

### O instrumento (juiz) foi validado
Suspeita inicial: a variância seria do juiz. **Refutada.** Repetindo a avaliação
da MESMA resposta 5×, o juiz deu **96 em todas (amplitude 0, desvio 0)** — `phi3:14b`
@ temp 0 é determinístico. (Os `out_len` idênticos entre reps eram artefato do
truncamento de seções do output do Villa em 1500/800 chars, não respostas iguais.)

### O "vale de iter 2" é ruído, não efeito de iterações
A queda aparente em it2 (juiz 50.4 vs ~69 em it1/it3) é **ruído de amostragem**:
com N=2 e variância de ~70 pontos entre execuções idênticas, a média é instável.
**Não se pode concluir nada sobre número de iterações com N=2.**

## Correção aplicada (V11.3) — hipótese a validar

`_call_agent`: o **Worker em queries de conhecimento** (não-código) passou de
`temp=0.4` para **`temp=0.25`** (factualidade > criatividade); código e planner
seguem em 0.4. Fundamento: temperatura alta alimenta invenção factual; reduzi-la
deve cortar a variância observada. **É hipótese** — só o re-bench com juiz e N
maior confirma. 48 testes passam.

## Próximo ciclo (validação e melhoria de confiabilidade)
1. **Re-bench `--repeat 5 --judge`** para validar `temp=0.25` e separar sinal de
   ruído (N=2 é insuficiente — a variância domina).
2. Se a variância persistir: **self-consistency** (gerar 2–3 respostas e o
   Reporter consolidar/votar) ou **modelo maior** para o Worker de conhecimento.
3. Baseline de tempo em **máquina ociosa** (os desvios de ~30% poluem a medição).

## Notas
- `_quality_score` permanece no relatório por comparabilidade histórica, mas o
  **juiz LLM passa a ser a métrica de qualidade de referência** (mede correção e
  adequação de domínio, não estrutura).
- Baseline pré-juiz e dados completos em `docs/relatorios/bench_semantic_2026-06-11.json`.
