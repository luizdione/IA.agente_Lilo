# conectar_claude_code.ps1 — registra o LILO como servidor MCP do Claude Code.
#
# Depois disso, em QUALQUER projeto (escopo user), o Claude Code ganha as
# tools do LILO: memoria persistente compartilhada (memorizar/lembrar/
# esquecer — o MESMO banco que o LILO usa), ler_pdf (artigos/manuais) e
# `delegar` — despachar uma tarefa COMPLETA ao agente LILO local (qwen3 na
# sua GPU): gratis, offline, privado.
#
# Pre-requisitos (uma vez, na raiz do repo):
#   pip install -e .        (comando `python -m lilo` de qualquer pasta)
#   pip install mcp         (protocolo MCP)
#
# Timeouts: os defaults do Claude Code ja comportam o `delegar` (execucao de
# tool ~28h; ocioso stdio 30min). Tarefa delegada MUITO longa (>30min sem
# emitir nada)? Suba CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT (em ms) antes do
# `claude`. Desfazer: claude mcp remove --scope user lilo

$ErrorActionPreference = "Stop"

if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Host "[ERRO] CLI 'claude' nao encontrado no PATH." -ForegroundColor Red
    Write-Host "Instale: npm install -g @anthropic-ai/claude-code"
    exit 1
}
python -c "import lilo, mcp" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] pacotes 'lilo' e/ou 'mcp' nao importam neste Python." -ForegroundColor Red
    Write-Host "Na raiz do repo rode (um por linha):"
    Write-Host "  pip install -e ."
    Write-Host "  pip install mcp"
    exit 1
}

claude mcp add --scope user --env LILO_MCP_SERVE_MODE=accept_edits lilo -- python -m lilo mcp-serve
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] 'claude mcp add' falhou (veja a mensagem acima)." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "LILO registrado no Claude Code (escopo user)." -ForegroundColor Green
Write-Host "Verifique:  claude mcp list      (esperado: lilo ... Connected)"
Write-Host "No REPL do Claude Code, /mcp mostra as tools; peca por exemplo:"
Write-Host '  "use o lilo para lembrar o que sei sobre X"'
Write-Host '  "delegue ao lilo: <tarefa simples>"'
