# LILO v13 — lancador PowerShell (o icone da Area de Trabalho aponta p/ ca).
# Abre o REPL do agente NO TERMINAL — nao existe dashboard de navegador no v13.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
Set-Location $PSScriptRoot
if (Test-Path ".venv\Scripts\Activate.ps1") { . ".venv\Scripts\Activate.ps1" }
python -m lilo @args
