---
name: perfil_dados
description: >-
  Perfila e consulta arquivos de dados GRANDES sem despejá-los no contexto, para
  economizar tokens: em vez de ler uma planilha de milhões de linhas, um .npz de
  GB ou um plasmídeo binário, o modelo lê um PERFIL compacto (forma, colunas,
  estatísticas, amostra) e faz consultas dirigidas que devolvem só as
  linhas/valores pedidos. Acione em pedidos como "perfilar/resumir esse CSV/
  Excel/JSON", "quais colunas tem essa tabela", "quantas linhas", "filtrar linhas
  onde X", "o que tem nesse .npz/.parquet", "resumir esse .cif/.pdb/FASTA", "ler
  o mapa desse plasmídeo SnapGene (.dna)", ou ao encontrar arquivos de dados
  grandes num projeto. Formatos: .csv/.tsv, .xlsx, .json, .npz/.npy, .parquet,
  .cif/.pdb, .fasta e SnapGene .dna. Para GraphPad .pzf/.pzfx use a skill
  graphpad_prism. Alimenta build_paper (tabelas/resultados) e auditoria_paper.
---

# perfil_dados — Perfil e consulta de dados grandes (economia de tokens)

## O que esta skill faz

Faz o modelo entender e usar um arquivo de dados **sem carregá-lo inteiro** no
contexto. Em vez do arquivo bruto (MB a GB), o modelo lê um **perfil compacto** e
extrai só o que precisa por **consulta dirigida**.

- **`perfil`** — forma, colunas (tipo, nulos, estatística/valores-topo), amostra.
- **`consultar`** — filtra (`query`), seleciona colunas, descreve uma coluna —
  devolve só o recorte.
- **`snapgene.py`** — mapa de um plasmídeo `.dna` (tamanho, topologia, %GC,
  features, primers, notas) sem despejar o binário nem a sequência.

## Por que economiza tokens

Uma planilha de 20 MB / 62 mil linhas vira um perfil de ~25 linhas; um `.npz` de
matriz PAE vira uma linha (`shape (524,524) float32`); um plasmídeo binário de
33 KB vira uma tabela de 11 features. O modelo lê o resumo e só puxa o recorte
necessário — nunca o arquivo inteiro.

## Formatos e ferramentas

| Tipo | Script | Saída compacta |
|---|---|---|
| `.csv` `.tsv` `.txt` | `perfil.py` | forma, colunas, stats, amostra; consulta com filtro |
| `.xlsx` `.xls` | `perfil.py` | abas + forma; `--sheet` para uma aba |
| `.json` | `perfil.py` | árvore de estrutura (chaves/tipos/tamanhos), sem valores brutos |
| `.npz` `.npy` | `perfil.py` | nome/shape/dtype de cada array |
| `.parquet` | `perfil.py` | como CSV (requer pyarrow/fastparquet) |
| `.cif` `.pdb` | `perfil.py` | título, nº de átomos, cadeias, resolução |
| `.fasta` `.fa` `.fna` | `perfil.py` | nº de sequências, comprimentos, nomes |
| SnapGene `.dna` | `snapgene.py` | mapa do plasmídeo (features/primers/notas) |
| GraphPad `.pzf`/`.pzfx` | → **skill `graphpad_prism`** | (não é esta skill) |

## Fluxo de trabalho

```bash
# Perfil compacto (auto-detecta o tipo)
python scripts/perfil.py perfil "dados.csv"
python scripts/perfil.py perfil "planilha.xlsx" --sheet "Resultados"
python scripts/perfil.py perfil "matriz.npz"

# Consulta dirigida — devolve só o recorte
python scripts/perfil.py consultar "dados.csv" --query "grupo=='tratado'" --cols "id,valor" --head 20
python scripts/perfil.py consultar "dados.csv" --describe "valor"

# Mapa de plasmídeo SnapGene (binário)
python scripts/snapgene.py "vetor.dna"            # mapa compacto
python scripts/snapgene.py "vetor.dna" --fasta out.fasta   # exporta a sequência
```

## Integração com as outras skills

- **`build_paper` / `auditoria_paper`:** perfile a tabela de resultados e extraia
  só as linhas/colunas citadas no manuscrito — sem carregar a planilha inteira.
- **`graphpad_prism`:** para arquivos do GraphPad Prism (`.pzf`/`.pzfx`) use aquela
  skill (extrai dados/resultados/figuras); esta cobre os demais formatos.
- **`gerente_memoria_projeto`:** registre no `CONTEXT.md` os caminhos dos dados
  principais e a forma resumida (n linhas × colunas), não os dados.

## Arquivos desta skill

| Arquivo | Conteúdo |
|---|---|
| `scripts/perfil.py` | Perfil + consulta (pandas/numpy; openpyxl p/ xlsx, pyarrow p/ parquet) |
| `scripts/snapgene.py` | Leitor do binário SnapGene `.dna` (stdlib) |
| `reference/formatos.md` | Detalhes por formato, limites e o binário SnapGene |

## Limitações (honestas)

- CSV/Parquet são lidos por inteiro para estatística (ok até dezenas de MB); para
  arquivos de vários GB, use `consultar` com `--query` desde o início.
- `.cif` do Boltz/AlphaFold nem sempre têm `_struct.title` → o campo pode vir vazio
  (o nº de átomos é o sinal útil).
- Não interpreta o CONTEÚDO científico (só estrutura/estatística) — a leitura é
  factual; a interpretação é do modelo/pesquisador.
- Para reanálise estatística de resultados do Prism, use `graphpad_prism`.
