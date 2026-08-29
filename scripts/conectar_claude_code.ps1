# conectar_claude_code.ps1 — registra o LILO como servidor MCP do Claude Code.
#
# Depois disso, em QUALQUER projeto (escopo user), o Claude Code ganha as
# tools do LILO: memoria persistente compartilhada (memorizar/lembrar/
# esquecer — o MESMO banco que o LILO usa), ler_pdf (artigos/manuais) e
# `delegar` — despachar uma tarefa COMPLETA ao agente LILO local (qwen3 na
# sua GPU): gratis, offline, privado.
#
# Pre-requisito (uma vez, no ambiente escolhido):  pip install mcp
#
# ESCOLHA DO AMBIENTE (v13.11) — importa de verdade: o LILO roda os seus
# scripts com o interpretador que voce registrar aqui. Se os seus pacotes
# (bioinformatica, ciencia de dados) estao num env conda, registre o python
# DELE, senao o `shell`/`delegar` do LILO vai quebrar com ModuleNotFoundError:
#
#   .\scripts\conectar_claude_code.ps1 -Python C:\Users\<voce>\miniforge3\envs\<env>\python.exe
#
# Sem -Python, usa o `python` ativo no PATH (o env que estiver ativado agora).
#
# v13.10 — COMANDO A PROVA DE SHELL. O `claude mcp add` recebe o comando do
# servidor depois de `--`, mas esse separador nem sempre sobrevive ao
# PowerShell/shim do npm: sumindo ele, o `-m` de `python -m lilo mcp-serve`
# virava "error: unknown option '-m'". Agora registramos
# `<python> ...\scripts\servir_mcp.py` — NENHUM token comeca com `-`, entao
# o registro funciona com ou sem o separador, em qualquer shell.
# (v13.9 corrigiu a ordem dos argumentos: `--env` e variadico e engolia o
# nome do servidor se viesse colado nele.)
#
# Nao conectou? Rode:  python scripts\diagnosticar_mcp.py
# Desfazer:            claude mcp remove lilo --scope user

param([string]$Python = "")

# --- pre-checagens ----------------------------------------------------------
$claude = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claude) {
    Write-Host "[ERRO] CLI 'claude' nao encontrado no PATH." -ForegroundColor Red
    Write-Host "Instale: npm install -g @anthropic-ai/claude-code"
    exit 1
}

# O Claude Code sobe o servidor com o PATH DELE: gravamos o caminho absoluto
# do interpretador que acabamos de testar, nao a palavra 'python'.
if ($Python) {
    if (-not (Test-Path $Python)) {
        Write-Host "[ERRO] -Python nao existe: $Python" -ForegroundColor Red
        exit 1
    }
    $pyExe = (Resolve-Path $Python).Path
} else {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
    if (-not $py) {
        Write-Host "[ERRO] Python nao encontrado no PATH." -ForegroundColor Red
        Write-Host "Instale o Python 3.11+ e marque 'Add python.exe to PATH'."
        exit 1
    }
    $pyExe = $py.Source
}
Write-Host "Ambiente do LILO: $pyExe" -ForegroundColor Cyan
Write-Host "(o LILO vai rodar os seus scripts com ESTE interpretador)" -ForegroundColor DarkGray
$checagem = & $pyExe -c "import mcp; print('ok')" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] o pacote 'mcp' nao importa em $pyExe" -ForegroundColor Red
    Write-Host $checagem
    Write-Host "Rode:  & '$pyExe' -m pip install mcp"
    Write-Host "Ou registre outro ambiente:  .\scripts\conectar_claude_code.ps1 -Python <caminho\python.exe>"
    exit 1
}

# --- o comando do servidor (SEM nenhum token comecando com '-') -------------
$servidor = Join-Path $PSScriptRoot "servir_mcp.py"
if (-not (Test-Path $servidor)) {
    Write-Host "[ERRO] nao achei $servidor (repo incompleto? rode git pull)" -ForegroundColor Red
    exit 1
}
$cmdServidor = @($pyExe, $servidor)

# --- autoteste: o comando EXATO que vamos registrar responde o handshake? ---
$diag = Join-Path $PSScriptRoot "diagnosticar_mcp.py"
if (Test-Path $diag) {
    & $pyExe $diag --handshake --cmd @cmdServidor
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

# ORDEM EXIGIDA PELA DOC: --env ... (outra opcao) ... NOME -- comando
$argsAdd = @('mcp', 'add',
             '--env', 'LILO_MCP_SERVE_MODE=accept_edits',
             '--scope', 'user',
             '--transport', 'stdio',
             'lilo', '--') + $cmdServidor
$saida = & $claude.Source @argsAdd 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] 'claude mcp add' falhou:" -ForegroundColor Red
    Write-Host $saida
    Write-Host ""
    Write-Host "Comando tentado:"
    Write-Host ("  claude " + ($argsAdd -join ' '))
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
