---
name: lilo_pdf
description: "Análise e sumarização de PDFs científicos com LILO. Use para resumir artigos, extrair introdução/métodos/resultados, detectar DOI, análise RAG de documentos. Triggers: 'resumir pdf', 'artigo pdf', 'sumarizar', 'extrair introducao', 'lilo pdf', 'analisar artigo', 'ler paper', 'metodos do paper', 'doi'."
---

# LILO PDF — Análise de Artigos Científicos

## Função
Roteia para `agents/PDFs_library/agent.py` — pipeline de leitura, indexação vetorial (RAG), sumarização e análise de PDFs científicos.

## Como executar

```bash
cd C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
python lilo.py pdf "<query>" --file <caminho/arquivo.pdf> --mode <modo>
```

Modos disponíveis:
- `introduction` — extrai e resume a introdução
- `methods` — extrai materiais e métodos
- `results` — extrai resultados e discussão
- `full` — sumarização completa
- `rag` — busca por trecho específico no documento

Exemplo:
```bash
python lilo.py pdf "quais métodos foram usados?" --file ~/artigo.pdf --mode methods
python lilo.py pdf "resumo completo" --file ~/paper.pdf --mode full
```

## Pipeline interno
`pdf_parser → doi_detector → embedder → vector_store → retriever → summarizer`

## Passos
1. Verifique se o usuário forneceu o caminho do PDF.
2. Se não forneceu, peça o caminho completo do arquivo.
3. Execute o comando com o modo apropriado.
4. Apresente o resumo com estrutura clara (objetivo, métodos, resultados, conclusão).
5. Inclua DOI/PMID se detectado.

## Capacidades extras
- Detecção automática de DOI
- Classificação do tipo de documento
- Busca semântica (RAG) em múltiplos PDFs indexados
- Análise tabular de dados extraídos
