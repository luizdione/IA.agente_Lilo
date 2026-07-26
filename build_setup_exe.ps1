# build_setup_exe.ps1 -- gera dist\setup_LILO.exe a partir de install.py (Windows).
#
# O .exe e' o INSTALADOR do LILO congelado (PyInstaller). Uso previsto: colocar
# o setup_LILO.exe DENTRO da pasta do LILO (ao lado de requirements.txt) e dar
# duplo-clique -> instala deps, cria .env, configura a chave do Claude e baixa
# o modelo Ollama base. Para instalar as dependencias ele usa um Python do
# sistema (py/python) -- portanto o usuario precisa ter Python 3.10+ instalado.
#
# Requisitos de build: Python 3.10+ e PyInstaller (este script instala se faltar).
# Saida: dist\setup_LILO.exe  (o binario NAO e' versionado -- ver .gitignore: dist/)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Instalando PyInstaller (se necessario)..." -ForegroundColor Yellow
python -m pip install --quiet --upgrade pyinstaller

Write-Host "Compilando setup_LILO.exe..." -ForegroundColor Yellow
python -m PyInstaller --onefile --console --name setup_LILO `
    --distpath "$here\dist" --workpath "$here\build\pyi" --specpath "$here\build" `
    "$here\install.py"

$exe = Join-Path $here "dist\setup_LILO.exe"
if (Test-Path $exe) {
    Write-Host "OK -> $exe" -ForegroundColor Green
} else {
    Write-Host "FALHOU: dist\setup_LILO.exe nao foi gerado." -ForegroundColor Red
    exit 1
}
