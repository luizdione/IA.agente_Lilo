@echo off
REM ============================================================
REM  LILO v7.0 — Inicialização Automática com o Windows
REM ============================================================
REM  Coloque um atalho deste .bat em:
REM    Win+R → shell:startup → colar atalho aqui
REM
REM  Inicia: Ollama, Dashboard Streamlit, Docker Compose
REM  Tudo roda em background (janelas minimizadas)
REM ============================================================

set LILO_ROOT=C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
set VILLA_ROOT=C:\Users\luizd\OneDrive\Data_Science\Projetos\osquestrador_ollama

REM ── 1. Ollama (motor LLM local) ─────────────────────────────
REM Verifica se já está rodando
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [LILO] Iniciando Ollama...
    start /MIN "" "ollama" serve
    REM Aguarda Ollama subir
    timeout /t 8 /nobreak >nul
) else (
    echo [LILO] Ollama ja esta rodando.
)

REM ── 2. Dashboard Streamlit (porta 8506) ──────────────────────
REM Verifica se já está rodando
curl -s http://localhost:8506 >nul 2>&1
if %errorlevel% neq 0 (
    echo [LILO] Iniciando Dashboard Streamlit...
    start /MIN "LILO Dashboard" cmd /c "cd /d %LILO_ROOT% && streamlit run dashboard.py --server.port 8506 --server.headless true"
) else (
    echo [LILO] Dashboard ja esta rodando na porta 8506.
)

REM ── 3. Docker Compose (backend, chromadb, frontend) ──────────
REM Verifica se Docker Desktop está rodando
docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo [LILO] Docker detectado. Iniciando containers...
    start /MIN "LILO Docker" cmd /c "cd /d %LILO_ROOT% && docker-compose up -d"
) else (
    echo [LILO] Docker Desktop nao esta rodando — containers nao iniciados.
    echo        Inicie o Docker Desktop manualmente se precisar dos containers.
)

REM ── 4. Villa Lobos (disponível via PyCharm MCP) ──────────────
REM Villa Lobos não precisa de processo separado — é chamado
REM sob demanda pelo lilo_pycharm_mcp.py quando o PyCharm
REM invoca as tools villa_pipeline ou villa_quick_ask.
REM Apenas verificamos se o path existe.
if exist "%VILLA_ROOT%\villa_lobos\main.py" (
    echo [LILO] Villa Lobos disponivel em %VILLA_ROOT%
) else (
    echo [LILO] Villa Lobos nao encontrado em %VILLA_ROOT%
)

REM ── Resumo ───────────────────────────────────────────────────
echo.
echo ============================================================
echo   LILO v7.0 — Inicializado
echo ============================================================
echo.
echo   Ollama:      http://localhost:11434
echo   Dashboard:   http://localhost:8506
echo   Backend:     http://localhost:8000  (se Docker ativo)
echo   Frontend:    http://localhost:3000  (se Docker ativo)
echo   ChromaDB:    http://localhost:8001  (se Docker ativo)
echo.
echo   PyCharm MCP: lilo_pycharm_mcp.py (sob demanda)
echo   Claude MCP:  lilo_mcp.py (configurado)
echo.
echo   Esta janela pode ser fechada.
echo ============================================================

REM Fecha automaticamente após 10s (para pasta Inicializar)
timeout /t 10 /nobreak >nul
