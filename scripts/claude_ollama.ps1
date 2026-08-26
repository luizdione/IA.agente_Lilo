# claude_ollama.ps1 — abre o Claude Code CLI rodando nos SEUS modelos Ollama.
#
# O Ollama (>= 0.12) expoe um endpoint compativel com a API da Anthropic
# (/v1/messages); apontando o Claude Code para ele, o CLI roda 100% na sua
# maquina — nenhum dado sai. Requer o CLI `claude` instalado
# (npm install -g @anthropic-ai/claude-code) e o Ollama em execucao.
#
# Uso:  .\scripts\claude_ollama.ps1                     # qwen3:14b + qwen3:4b
#       .\scripts\claude_ollama.ps1 qwen3:4b            # so o modelo principal
#       .\scripts\claude_ollama.ps1 qwen3:14b qwen3:4b  # principal + background
#
# Avisos (docs.ollama.com/integrations/claude-code):
# - contexto recomendado >= 32K: rode o servidor com
#   $env:OLLAMA_CONTEXT_LENGTH = "32768" antes de `ollama serve`;
# - sem prompt caching/token counting — mais lento que o Claude na nuvem;
# - as variaveis valem SO nesta janela; feche-a e o Claude Code volta ao
#   normal (nuvem Anthropic) nas demais.
param([string]$Modelo = "qwen3:14b", [string]$ModeloFast = "qwen3:4b")

$env:ANTHROPIC_BASE_URL = "http://localhost:11434"
$env:ANTHROPIC_AUTH_TOKEN = "ollama"              # o Ollama ignora o valor
$env:ANTHROPIC_MODEL = $Modelo
$env:ANTHROPIC_DEFAULT_HAIKU_MODEL = $ModeloFast  # tarefas de fundo/rapidas

Write-Host "Claude Code -> Ollama local ($Modelo; fundo: $ModeloFast)." -ForegroundColor Cyan
Write-Host "Modelos 4-14B sao bem mais fracos que o Claude: use p/ tarefas simples/privadas." -ForegroundColor DarkGray
claude
