---
name: graphpad_prism
description: >-
  Analisa e extrai o conteúdo de arquivos do GraphPad Prism (.pzf, .pzfx, .pzt):
  tabelas de dados brutos, resultados estatísticos já calculados (ANOVA, t-test,
  regressão, etc.), figuras/gráficos embutidos, e re-análise/auditoria dos testes.
  Acione em pedidos como "analisar/abrir/ler arquivo do Prism", "extrair os dados
  do .pzf", "recuperar as tabelas/gráficos do GraphPad", "converter Prism em CSV",
  "pegar os resultados do ANOVA do Prism", "/graphpad_prism", ou ao encontrar
  arquivos .pzf/.pzfx/.pzt em um projeto. Trata DOIS formatos: .pzfx/.pzt (XML,
  Prism 5+) com extração FIEL, e .pzf legado (binário "PCFFGRA4", Prism 4) com
  extração best-effort (dados, resultados completos e figuras EMF são recuperáveis
  sem o GraphPad instalado). Converte as figuras EMF em PNG (GDI+ nativo do Windows,
  sem dependências) ou SVG/PDF. Integra-se ao build_paper (dados/figuras para o
  manuscrito) e ao auditoria_paper (recálculo independente para integridade dos dados).
  NÃO é o toolkit `mcp__lilo__prism_*` (que é de EDA/classificação, sem relação com GraphPad).
---

# graphpad_prism — Análise de arquivos do GraphPad Prism

## O que esta skill faz

Abre arquivos do **GraphPad Prism** e recupera o conteúdo científico útil — **sem
precisar do GraphPad instalado** — em quatro eixos:

1. **Dados brutos → tabelas** (`CSV`, prontos para R/Python).
2. **Resultados estatísticos** que o Prism já calculou (ANOVA, t-test, regressão,
   comparações múltiplas, ICs) → texto estruturado.
3. **Figuras/gráficos** embutidos → `PNG` (e opcionalmente `SVG`/`PDF`).
4. **Re-análise / auditoria** — recalcula descritivas e testes de forma
   independente para comparar com o que o Prism reportou (reprodutibilidade /
   integridade dos dados).

## Realidade dos formatos (LER PRIMEIRO — determina a fidelidade)

| Extensão | Assinatura | Motor | Fidelidade |
|---|---|---|---|
| `.pzfx`, `.pzt` | XML (`<?xml`) | XML (ElementTree) | **Alta** — tabelas, réplicas, rótulos de linha, pontos excluídos e metadados saem exatos |
| `.pzf` (Prism 5+) | XML | XML | Alta (mesmo motor) |
| `.pzf` (Prism 4 legado) | binário `PCFFGRA4` | binário (best-effort) | **Parcial** — valores, resultados completos e figuras são recuperados; a estrutura exata célula-a-célula das tabelas de dados é aproximada |

**Regra de ouro:** se o arquivo for `.pzf` binário legado e você precisar de
fidelidade célula-a-célula das tabelas de entrada, o caminho-ouro é **reabrir no
GraphPad Prism e reexportar como `.pzfx`** (File ▸ Save As ▸ formato .pzfx) **ou
exportar as tabelas em CSV**. A extração binária desta skill é excelente para
**salvar os resultados estatísticos (que saem completos) e as figuras**, e para
**resgatar dados** quando o Prism não está disponível — mas sempre marque a saída
binária como "best-effort" e confira valores críticos.

> Os `.pzf` legado guardam os textos (rótulos e números) em UTF-16/ASCII em claro
> e as figuras como *Enhanced Metafile* (EMF) vetorial — por isso a recuperação
> funciona mesmo sem o GraphPad.

## Ambiente / dependências

- **Extração** (`prism_extract.py`): só stdlib do Python. `pandas` é usado se houver.
- **Figuras** (`emf_convert.py`): no **Windows** usa GDI+ nativo (`System.Drawing`
  via PowerShell) → PNG sem instalar nada. Para SVG/PDF vetorial, Inkscape (melhor)
  ou LibreOffice. Fora do Windows: Inkscape/LibreOffice/ImageMagick.
- **Re-análise** (`prism_reanalyze.py`): `numpy`, `scipy`, `pandas`.

## Fluxo de trabalho

### Passo 0 — Localizar e identificar
Encontre os arquivos e confirme o formato. Rodar o extrator já reporta o formato
detectado no `inventario.json` e no `RELATORIO.md`.

```bash
python scripts/prism_extract.py "CAMINHO/arquivo.pzf"
```

Isso cria `arquivo_extração/` com:
```
inventario.json     # índice estruturado (formato, tabelas, análises, figuras, avisos)
RELATORIO.md        # resumo legível
resultados.txt      # resultados estatísticos (ANOVA/t-test/...) — SÓ no caminho binário .pzf
tabelas/*.csv       # uma tabela por CSV (no .pzfx, tabelas de RESULTADO também saem aqui)
figuras/*.emf       # figuras vetoriais (só no caminho binário)
```

### Passo 1 — Dados → tabelas (entregável 1)
As tabelas saem em `tabelas/*.csv`.
- **`.pzfx`:** matriz fiel (rótulos de linha + colunas Y com réplicas em `_rep1/2/3`,
  pontos excluídos marcados `[EXCLUÍDO]`).
- **`.pzf` binário:** CSV `rotulo_ou_contexto,valor` (best-effort) — os números
  estão certos; os rótulos são aproximados. Reagrupe conforme o desenho real.

### Passo 2 — Resultados estatísticos (entregável 2)
No `.pzf` **binário**, `resultados.txt` traz o que o Prism calculou: tipo de teste,
tabela de ANOVA (SS, MS, DF, F), P-valores, comparações múltiplas (Bonferroni/Tukey),
ICs 95% e o texto narrativo. Esses blocos saem **completos** — são o material mais
confiável da extração binária. No `.pzfx` (**XML**) **não há** `resultados.txt`: as
tabelas de resultado de análise saem como CSV em `tabelas/` (junto com os dados).

### Passo 3 — Figuras (entregável 3)
Converta os `.emf` extraídos:
```bash
python scripts/emf_convert.py "arquivo_extração/figuras" --format png --dpi 300 --scale 3
# vetorial (requer Inkscape):
python scripts/emf_convert.py "arquivo_extração/figuras" --format svg
```
O Prism guarda cada gráfico como par tela/impressão; o extrator já **deduplica**
(fica ~metade). Alguns EMFs são tabelas-imagem (resultados renderizados), não só
gráficos — todos viram PNG legível.

### Passo 4 — Re-análise / auditoria (entregável 4)
Recalcule de forma independente e compare com o Prism:
```bash
python scripts/prism_reanalyze.py "arquivo_extração"          # varre tabelas/*.csv
python scripts/prism_reanalyze.py "tabela.csv" --out reanalise.md
```
Gera descritivas (n, média, DP, EPM, IC95%), checagem de **premissas**
(Shapiro/Levene) e o teste apropriado (t de Student+Welch+Mann-Whitney+d de Cohen
para 2 grupos; ANOVA 1-via+Kruskal-Wallis+η²+pairwise Holm para >2). **Confira**
os P/F recalculados contra os do `resultados.txt`.

> **Cuidado de auditoria:** a ANOVA da re-análise trata grupos como independentes.
> Muitos projetos do Prism são **RM/two-way** — nesse caso os P diferem e isto é
> triagem, não a reprodução do modelo. Além disso, colunas de réplica do `.pzfx`
> (`Grupo_rep1/2/3`) são **agregadas num só grupo** pela re-análise; se as réplicas
> cruzam um fator intra (ex.: dias), essa agregação simplifica o desenho. Para
> reproduzir fielmente, use os dados brutos (`.pzfx`) em R (`afex`/`ez`) ou
> Python (`pingouin`).

## Integração com as outras skills

- **`build_paper`:** os CSVs (dados) e os PNG/SVG (figuras) alimentam diretamente
  o manuscrito e as tabelas/figuras reprodutíveis. Cite a origem nos Métodos.
- **`auditoria_paper`:** use a re-análise (Passo 4) como recálculo independente de
  fidelidade dos dados; divergência entre o P recalculado e o reportado pelo Prism
  é achado de auditoria a investigar (desenho RM vs independente, n, exclusões).
- **`git_dione`:** os scripts de recálculo + tabelas + figuras (com legenda) são
  exatamente o tipo de artefato de cálculo que vai ao repositório do paper.

## Referências

- `reference/formatos_prism.md` — anatomia dos formatos `.pzf`/`.pzfx`, assinatura
  `PCFFGRA4`, EMF, e como reexportar do Prism para fidelidade total.
- `reference/fluxo_reanalise.md` — mapeamento dos testes do Prism → recálculo em
  Python/R e como comparar corretamente (RM/two-way, correções múltiplas).

## Limitações (honestas)

- `.pzf` binário: reconstrução célula-a-célula das tabelas de **entrada** é
  aproximada. Resultados e figuras são fiéis; dados brutos são best-effort.
- Modelos complexos (RM/two-way/mistos, regressão não-linear) não são
  re-executados fielmente pela re-análise — ela é triagem estatística.
- Conversão vetorial SVG/PDF exige Inkscape/LibreOffice; PNG é garantido no Windows.
- Não escreve nem altera arquivos do Prism — a skill é somente-leitura sobre eles.
