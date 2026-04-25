@echo off
echo ============================================================
echo   LILO Dashboard — Streamlit
echo ============================================================
echo.

:: Verificar se Ollama está rodando
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Ollama nao esta rodando. Iniciando...
    start /B ollama serve
    timeout /t 5 /nobreak >nul
)

:: Verificar dependências
python -c "import streamlit" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Instalando dependencias...
    pip install streamlit pandas requests PyMuPDF python-dotenv anthropic
)

:: Iniciar dashboard
echo [INFO] Iniciando dashboard em http://localhost:8506
echo.
streamlit run dashboard.py --server.port 8506
