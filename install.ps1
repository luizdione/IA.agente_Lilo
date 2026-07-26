# install.ps1 -- bootstrap do instalador do LILO (Windows).
# Uso:  .\install.ps1   (ou:  powershell -ExecutionPolicy Bypass -File install.ps1)
# Encontra o Python e delega para install.py (o instalador real, multiplataforma).

$here = Split-Path -Parent $MyInvocation.MyCommand.Path

if (Get-Command py -ErrorAction SilentlyContinue) {
    $pyExe = "py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pyExe = "python"
} else {
    Write-Host "Python 3.10+ nao encontrado. Instale de https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

Write-Host "Usando Python via '$pyExe'..." -ForegroundColor Yellow
& $pyExe "$here\install.py" @args
exit $LASTEXITCODE
