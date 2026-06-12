# Build e logística de versionamento

Logística comprovada para produzir e versionar manuscritos de forma
reprodutível. Genérica — parametrizada pela raiz do projeto.

## Layout de diretórios (convenção)

```
<RAIZ_DO_PROJETO>/
├── PAPER/
│   ├── src/                      # FONTE ÚNICA (editável)
│   │   ├── manuscrito_PT.md
│   │   └── manuscrito_EN.md      # quantas versões/idiomas existirem
│   ├── figuras/                  # PNGs gerados por scripts (idempotentes)
│   ├── build/                    # SAÍDA derivada: .docx .tex .pdf
│   ├── LOG_VERSOES.md            # diário de rodadas
│   ├── build.sh                  # (cópia/atalho de assets/build.sh)
│   └── figuras_rebuild.sh        # regenera figuras a partir dos dados
└── OBSOLETOS/                    # versões arquivadas por rodada
```

Regras:
- **Edite só `src/*.md`.** DOCX/TEX/PDF são derivados; nunca editados à mão.
- Uma fonte por idioma/versão (ex.: EN para submissão + PT para análise).
- Três formatos de saída por fonte: DOCX, TEX, PDF.

## Build: Markdown -> DOCX/TEX/PDF

Motor: **pandoc** (DOCX/TEX) + **tectonic** (PDF, via `--pdf-engine`). No setup
do usuário ambos vivem no env conda `datascience` do Miniforge3.

```bash
bash ~/.claude/skills/build_paper/assets/build.sh "<RAIZ_DO_PROJETO>"
```

O script: localiza `PAPER/src/manuscrito_*.md`, gera os três formatos em
`PAPER/build/`, e (opcional) sincroniza para uma pasta de submissão.

### Notação Markdown que o pipeline espera
- Cabeçalho **YAML** com `title`, `author`, `date`, `lang`, `abstract: |`.
- Sobrescrito/subscrito: `Mg^2+^`, `10^-5^`, `Zn^2+^` (pandoc `^...^` / `~...~`).
- Itálico para nomes de espécies/genes: `*Trypanosoma cruzi*`.
- Tabelas em **pipe table** do pandoc (renderizam limpas em DOCX/PDF).
- Seções numeradas: `# 1. Introdução`, `## 2.1 ...`.

### Fontes e Unicode (PDF)
Use uma fonte com cobertura Unicode ampla para símbolos científicos
(≤ ≥ ≈ · × Å µ). O default testado é **Cambria** (`-V mainfont="Cambria"`).
Se um glifo falhar no PDF, troque a fonte principal antes de suspeitar do texto.

### Solução de problemas
- **PDF falhou / glifo ausente:** trocar `mainfont`; conferir se tectonic está
  no PATH (o script exporta o `Library/bin` do env).
- **Tabela quebrada:** validar a sintaxe pipe table (linha de `---|---`).
- **Figura não aparece:** caminho relativo; usar `--resource-path=.:src` (já no
  script) e conferir se o PNG existe em `figuras/`.

## Figuras e tabelas reprodutíveis
- Cada figura é produzida por um script (ex.: `tools/figura_*.py`) a partir dos
  **dados reais**, salvo em `PAPER/figuras/FigN_*.png`. Mantenha um
  `figuras_rebuild.sh` que regenera todas (idempotente: só sobrescreve PNGs,
  não edita os `.md`).
- Tabelas grandes: script -> TSV/`COMPARATIVO.tsv` -> tabela pandoc inserida na
  fonte. Reexecutável se os dados mudarem (reinserir após rebuild da fonte).
- Renumerou figuras? Ajuste todas as chamadas in-text e as legendas.

## Versionamento por rodadas

A cada melhoria significativa:
1. **Arquive** as versões atuais em `OBSOLETOS/paper_rodadaN_<data>/` antes de
   gerar as novas. Use `assets/nova_rodada.sh`.
2. **Rebuild** (figuras se preciso, depois `build.sh`).
3. **Registre** a rodada no `LOG_VERSOES.md`.

Mudanças incrementais pequenas na mesma fonte podem dispensar arquivamento
separado (o build atual substitui o anterior) — mas o log deve registrá-las.

### Formato de entrada do LOG_VERSOES.md
```
## Rodada N — <data> (foco: <objetivo da rodada>)
- <o que mudou e por quê> (decisões, dados/refs incorporados).
- <nº de arquivos regenerados; nº de páginas dos PDFs>.
- **Pendências:** <o que ficou para a próxima rodada>.
```
O log é a memória do manuscrito: deve permitir reconstruir o raciocínio de
cada decisão editorial. Registre periódico-alvo, mudanças de ferramenta/refs,
ajustes a normas (abstract, keywords, highlights, declarações) e pendências.

---

## Graphical abstract (resumo gráfico) — atualizado a cada versão

Todo paper leva um graphical abstract na 1ª página, regenerado a cada build.
Prioridade **override → fallback**:

1. **`PAPER/figuras/graphical_abstract_manual.{pdf,png}`** (arte BioRender/Canva do
   usuário) → o build a usa como `graphical_abstract.{pdf,png}` (acabamento de
   publicação).
2. **Fallback vetorial data-aware** (`assets/ga_icons.py` + RDKit p/ a molécula),
   puxando os números reais dos resultados. Reproduzível, sempre coerente c/ a versão.

Inserção: logo após `\maketitle` (LaTeX) ou antes do Abstract (Markdown:
`![Graphical abstract ...](graphical_abstract.png)`).

### Feed do BioRender (a cada versão; executado por mim via MCP)
- Config por paper: `PAPER/graphical_abstract.config.json`
  ```json
  { "title": "...", "biorender_terms": ["mouse","Trypanosoma cruzi trypomastigote",
    "Leishmania promastigote","mitochondria","reactive oxygen species"],
    "key_numbers_from": "caminho do JSON/דados canônicos" }
  ```
- A cada versão eu chamo `search-icons` + `search-templates` do BioRender com
  `biorender_terms` e (re)escrevo `PAPER/figuras/graphical_abstract_RECIPE.md`
  com os nomes EXATOS dos ícones recomendados + links de templates. O recipe
  evolui junto com o paper (novas entidades/resultados → novos ícones sugeridos).
- **Limitação:** ícones BioRender são proprietários e o MCP é só de busca — não
  embuto os assets. O usuário monta no BioRender e exporta como
  `graphical_abstract_manual.pdf`; o build passa a usá-lo. Até lá, fallback vetorial.

### ga_icons.py — biblioteca de ícones vetoriais
Primitivas desenháveis (matplotlib, sem assets externos): `mouse`, `cattle`,
`trypanosome`, `leishmania`, `mitochondrion(healthy=)`, `host_cell(collapsed=)`,
`ros_burst`, `dna`, `flow_arrow`, `cycle_arrow`. Componha um GA sob medida para a
história do paper (não há engine rígida — eu monto o fluxo por paper usando estas
primitivas + os números reais).
