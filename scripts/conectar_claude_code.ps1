# conectar_claude_code.ps1 — registra o LILO como servidor MCP do Claude Code.
#
# Depois disso, em QUALQUER projeto (escopo user), o Claude Code ganha as
# tools do LILO: memoria persistente compartilhada (memorizar/lembrar/
# esquecer — o MESMO banco que o LILO usa), ler_pdf (artigos/manuais) e
# `delegar` — despachar uma tarefa COMPLETA ao agente LILO local (qwen3 na
# sua GPU): gratis, offline, privado.
#
# Pre-requisitos (uma vez, na raiz do repo):
#   pip install -e .        (o modulo `lilo` importavel de qualquer pasta)
#   pip install mcp         (protocolo MCP)
#
# v13.9 — o que mudou (a conexao falhava na v13.8):
#   * ORDEM DOS ARGUMENTOS: a doc do Claude Code exige pelo menos uma opcao
#     ENTRE `--env` e o nome do servidor; `--env K=V lilo` fazia o `lilo`
#     ser lido como mais um par de variavel e o `add` falhava.
#   * Sem $ErrorActionPreference="Stop": no PowerShell 5.1 o stderr de um
#     comando nativo virava erro terminante e escondia a mensagem util.
#   * Registra o CAMINHO ABSOLUTO do python que passou no teste (o Claude
#     Code sobe o servidor com o PATH dele — venv/py launcher quebravam).
#   * Idempotente: remove um `lilo` antigo antes de registrar.
#
# Nao conectou? Rode:  python scripts\diagnosticar_mcp.py
# Desfazer:            claude mcp remove lilo --scope user

# --- pre-checagens ----------------------------------------------------------
$claude = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claude) {
    Write-Host "[ERRO] CLI 'claude' nao encontrado no PATH." -ForegroundColor Red
    Write-Host "Instale: npm install -g @anthropic-ai/claude-code"
    exit 1
}

# Python: precisa ser o MESMO interpretador que tem lilo+mcp, e vamos gravar
# o caminho absoluto dele no registro (nao a palavra 'python').
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if (-not $py) {
    Write-Host "[ERRO] Python nao encontrado no PATH." -ForegroundColor Red
    Write-Host "Instale o Python 3.11+ e marque 'Add python.exe to PATH'."
    exit 1
}
$pyExe = $py.Source
$checagem = & $pyExe -c "import lilo, mcp; print('ok')" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] 'lilo' e/ou 'mcp' nao importam em $pyExe" -ForegroundColor Red
    Write-Host $checagem
    Write-Host "Na raiz do repo rode (um comando por linha):"
    Write-Host "  pip install -e ."
    Write-Host "  pip install mcp"
    exit 1
}

# --- autoteste: o servidor sobe e responde o handshake? ---------------------
$diag = Join-Path $PSScriptRoot "diagnosticar_mcp.py"
if (Test-Path $diag) {
    & $pyExe $diag --handshake
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "[ERRO] o servidor MCP do LILO nao respondeu ao handshake." -ForegroundColor Red
        Write-Host "Relatorio completo:  python scripts\diagnosticar_mcp.py"
        exit 1
    }
}

# --- registro ---------------------------------------------------------------
# Idempotencia: um 'lilo' anterior impede o add (ignoramos a saida aqui).
& $claude.Source mcp remove lilo --scope user 2>&1 | Out-Null

# ORDEM EXIGIDA PELA DOC: --env ... --scope/--transport ... NOME -- comando
$saida = & $claude.Source mcp add `
    --env LILO_MCP_SERVE_MODE=accept_edits `
    --scope user --transport stdio lilo `
    -- $pyExe -m lilo mcp-serve 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] 'claude mcp add' falhou:" -ForegroundColor Red
    Write-Host $saida
    exit 1
}
Write-Host $saida

# --- verificacao ------------------------------------------------------------
Write-Host ""
Write-Host "Verificando..." -ForegroundColor Cyan
$lista = & $claude.Source mcp list 2>&1
Write-Host $lista
if ("$lista" -notmatch "lilo") {
    Write-Host ""
    Write-Host "[AVISO] o 'lilo' nao apareceu na lista." -ForegroundColor Yellow
    Write-Host "Diagnostico:  python scripts\diagnosticar_mcp.py"
    Write-Host "Detalhes:     claude mcp get lilo"
    Write-Host "Log do Claude Code: %USERPROFILE%\.claude\debug\<sessao>.txt"
    exit 1
}

Write-Host ""
Write-Host "LILO registrado no Claude Code (escopo user, todos os projetos)." -ForegroundColor Green
Write-Host "No REPL do Claude Code, /mcp mostra as tools. Peca por exemplo:"
Write-Host '  "use o lilo para lembrar o que sei sobre X"'
Write-Host '  "delegue ao lilo: <tarefa simples>"'
