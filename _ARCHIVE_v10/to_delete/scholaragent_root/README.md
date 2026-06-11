# ScholarAgent — Agente Local para Análise de PDFs Científicos

Ferramenta Python + Flask que utiliza modelos LLM locais via **Ollama** para processar
publicações científicas em PDF e gerar saídas filtradas para escrita de artigos.

## Funcionalidades

| Modo | Descrição |
|------|-----------|
| **Resumo Simples** | Resumo geral: objetivo, metodologia, resultados-chave, conclusão |
| **Resumo p/ Introdução** | Análise de contexto, lacuna, hipótese e relevância do campo |
| **Extração de Métodos** | Desenho experimental, modelos biológicos, técnicas, softwares, estatística |
| **Interpretação de Gráficos** | Análise de figuras via modelo multimodal (LLaVA) com texto para Resultados |
| **Formatação de Referências** | Busca estilo da revista por ISSN (via CrossRef) e formata citações |

## Requisitos

- **Python 3.10+**
- **Ollama** instalado e rodando (`ollama serve`)
- Pelo menos um modelo de texto baixado (recomendado: `llama3.1:8b` ou superior)
- Para interpretação de gráficos: modelo multimodal (`llava:13b` ou `llava:7b`)

## Instalação

```bash
# 1. Clonar/copiar o projeto
cd scholar-agent

# 2. Instalar dependências Python
pip install -r requirements.txt

# 3. Instalar modelos no Ollama (se ainda não tiver)
ollama pull llama3.1:8b        # Modelo de texto
ollama pull llava:13b           # Modelo multimodal (para gráficos)

# 4. Garantir que o Ollama está rodando
ollama serve                    # Em outro terminal, se necessário

# 5. Executar a aplicação
python app.py
```

Acesse **http://localhost:5000** no navegador.

## Arquitetura

```
scholar-agent/
├── app.py                  # Flask: rotas e orquestração
├── ollama_client.py        # Cliente da API local do Ollama
├── pdf_processor.py        # Extração de texto, seções e imagens (PyMuPDF)
├── reference_formatter.py  # Busca ISSN no CrossRef + prompt de formatação
├── templates/
│   └── index.html          # Frontend (HTML/CSS/JS)
├── uploads/                # PDFs enviados (local, não versionado)
├── requirements.txt
└── README.md
```

## Modelos Recomendados

### Para texto (resumo, métodos, referências)
- `llama3.1:8b` — bom equilíbrio desempenho/qualidade
- `llama3.1:70b` — melhor qualidade, requer GPU potente
- `mistral:7b` — alternativa leve
- `command-r:35b` — bom para tarefas analíticas

### Para gráficos (multimodal)
- `llava:13b` — recomendado (melhor interpretação visual)
- `llava:7b` — alternativa mais leve
- `bakllava:7b` — alternativa
- `moondream:1.8b` — ultra-leve, qualidade limitada

## Fluxo de Uso

1. **Upload** do PDF no painel lateral
2. O sistema extrai automaticamente texto, seções e figuras
3. **Selecionar aba** conforme a necessidade (Resumo, Introdução, Métodos, etc.)
4. **Executar** — o LLM local processa e retorna o resultado
5. **Copiar** o resultado para usar no seu artigo

### Para Referências
1. Informar o **ISSN** da revista-alvo
2. Clicar **Buscar** para identificar a revista via CrossRef
3. Colar as referências brutas (ou extrair do PDF)
4. **Formatar** — o LLM formata no estilo da revista

## Notas Técnicas

- O texto do PDF é truncado em ~12.000 caracteres para caber no contexto do modelo 8B.
  Para modelos maiores, ajuste `max_chars` em `app.py`.
- A detecção de seções usa heurística por regex em headings comuns (EN/PT).
  Funciona bem para artigos com formatação padrão.
- A busca de estilo de citação por ISSN usa a API pública do CrossRef
  (sem necessidade de chave de API).
- Imagens menores que 5KB são filtradas (logos, ícones). Ajuste `min_size`
  em `pdf_processor.py` se necessário.

## Roadmap

- [ ] Streaming de resposta do LLM (SSE)
- [ ] Suporte a múltiplos PDFs simultâneos
- [ ] Exportação para .docx
- [ ] RAG com ChromaDB para base de artigos
- [ ] Integração com Zotero/Mendeley
- [ ] OCR para PDFs escaneados (Tesseract)

---
*ScholarAgent — Dione B. Melo, 2026*
