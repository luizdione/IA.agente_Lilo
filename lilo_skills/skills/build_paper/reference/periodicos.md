# Periódicos, áreas e regra de entrega bilíngue

## Áreas cobertas
Esta skill é calibrada para as áreas de atuação do usuário:
bioquímica, biologia celular, ômicas (genômica, transcriptômica, proteômica,
metabolômica, epigenômica), genética animal, parasitologia, biologia molecular
e farmacologia. O vocabulário, o estilo e os tipos de evidência esperados
seguem essas comunidades (ex.: ipTM/pLDDT em biologia estrutural; IC50/Ki/EC50
e MoA em farmacologia; QTL/SNP/herdabilidade em genética animal; e-value/
identidade/cobertura em ômicas; CFU/parasitemia/curvas de sobrevida em
parasitologia).

## Regra de entrega bilíngue (OBRIGATÓRIA)

Para todo manuscrito, entregar **dois pares** de arquivos, cada um em **três
formatos (DOCX, PDF, TEX)**:

1. **Versão de SUBMISSÃO — Inglês — LIMPA.**
   Nome: `manuscript_EN.{docx,pdf,tex}` (ou `manuscript_EN_submission.{...}`).
   Sem banner, sem caixa de notas. É o arquivo que vai ao periódico.

2. **Versão de ANÁLISE/AUDITORIA — Português — MARCADA.**
   Nome: `manuscrito_PT_analise.{docx,pdf,tex}` (ou `manuscript_PT.{...}`).
   **Deve** conter os dois elementos de segurança abaixo. É o arquivo de
   revisão interna; **nunca** é submetido.

A presença do banner é o **sinal canônico de "não submeter este arquivo"**.
Regra completa de referência (com snippets):
`C:/Users/luizd/OneDrive/Data_Science/Projetos/artigos_submissao/_REGRA_VERSAO_ANALISE_PT.md`.

### Elemento 1 — Banner vermelho (logo após o título)
```
[VERSÃO DE ANÁLISE E CORREÇÃO — PORTUGUÊS — NÃO SUBMETER]
```

### Elemento 2 — Caixa de pendências (abaixo dos autores, antes do resumo)
Título: **"Notas de análise e correção (pendências antes da submissão)"**.
Enumere pendências **reais**, tipicamente:
- Confirmar autoria, ordem dos coautores, afiliações e ORCIDs.
- Verificar conformidade ao escopo/instruções do periódico-alvo (formato,
  limite de palavras, nº de figuras).
- Validar números-chave contra os dados-fonte versionados.
- Conferir referências cruzadas (figuras/tabelas/citações) após formatação.
- Adicionar financiamento, conflitos de interesse, contribuições (CRediT) e
  disponibilidade de dados/código.
- Reconciliar versão PT ↔ EN.
- Remover esta caixa e o banner antes do envio.

### Implementação técnica (pandoc + tectonic)
O PDF é gerado por **tectonic (LaTeX)**, então o banner **não** pode ser HTML
(seria descartado). Use **blocos raw do pandoc**, específicos por formato, para
que cada saída receba a versão certa sem duplicar:

- PDF/TEX recebem blocos `{=latex}` (vermelho via `xcolor`, caixa via
  `tcolorbox`); o cabeçalho YAML carrega esses pacotes em `header-includes`.
- DOCX recebe blocos `{=openxml}` (parágrafo vermelho/negrito).

O script `assets/marcar_versao_analise.py` injeta (ou remove, com `--strip`)
automaticamente o banner e a caixa na fonte PT. O `assets/build.sh` aplica a
marcação à versão PT e mantém a EN limpa. **Antes da submissão**, rode o build
em modo final (ou `--strip`) para remover banner + caixa e regenerar.

## Enquadramento por periódico-alvo
Antes de finalizar, ajuste a fonte às instruções do periódico. Parâmetros que
variam e devem ser confirmados:

| Parâmetro | Onde afeta |
|---|---|
| Limite de palavras do abstract | YAML `abstract` |
| Estrutura do abstract (estruturado vs corrido) | Abstract |
| Nº de keywords | Bloco de keywords |
| Highlights (nº e limite de caracteres) | Bloco de highlights |
| Estilo de citação (autor-ano/Harvard, numérico/Vancouver) | Refs + in-text |
| Seções de declarações exigidas | Declarações |
| Limite de figuras/tabelas | Resultados |

### Exemplo trabalhado — Acta Tropica (Elsevier)
Estilo autor-ano (Harvard); abstract ≤ 250 palavras; ~6 keywords; Highlights
(geralmente até 5 bullets, ≤ 85 caracteres cada); seção de declarações
(Financiamento, COI, CRediT, disponibilidade de dados/código). Publicação sem
custo se não-OA. Use como modelo de como destilar as "guide for authors" de
qualquer periódico em parâmetros acionáveis.

### Como adicionar um novo periódico
1. Abra a "Guide for Authors".
2. Extraia os parâmetros da tabela acima.
3. Aplique à fonte e registre no `LOG_VERSOES.md` ("Rodada N — alvo: periódico").
