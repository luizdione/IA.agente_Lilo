"""lilo_host — ponte do LILO v14 com o host (servidor MCP HTTP em 127.0.0.1:8790).

Roda no conda `datascience`. Tres grupos, cada um num endpoint:
  /conhecimento/mcp  memoria dos projetos, leitura de PDF/texto, resumo de arquivo
  /analise/mcp       estatistica (pingouin/statsmodels), parsers bio, DOCX
  /exec/mcp          Python, R e WSL no host — exige token (Authorization: Bearer)

Lancador: scripts\\lilo_host_serve.py. Operacao: lilo.ps1 (ponte up|down, status).
"""
__version__ = "14.0.0"
