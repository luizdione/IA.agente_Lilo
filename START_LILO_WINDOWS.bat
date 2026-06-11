@echo off
REM ============================================================
REM  LILO v7.0 — Inicializacao Automatica com o Windows
REM ============================================================
REM  Coloque um atalho deste .bat em:
REM    Win+R -> shell:startup -> colar atalho aqui
REM
REM  Inicia: Ollama, Dashboard Streamlit, Docker Compose
REM  Tudo roda em background (janelas minimizadas)
REM ============================================================

set LILO_ROOT=C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
set VILLA_ROOT=C:\Users\luizd\OneDrive\Data_Science\Projetos\osquestrador_ollama

REM -- 0. Verificacao MCP: Desktop Commander deve estar desligado -----
REM     Otimizacao 2026-05-12: profile 'opus' do LILO ja oferece as
REM     mesmas tools (fs_*, run_*); manter DC duplica ~2077 tokens no
REM     system prompt de cada chamada do Claude Desktop. O script
REM     scripts\disable_desktop_commander.py --check apenas inspeciona
REM     (nao modifica) e imprime ATENCAO se DC continuar ativo.
echo [LILO] Verificando MCP do Claude Desktop...
python "%LILO_ROOT%\scripts\disable_desktop_commander.py" --check 2>nul
if %errorlevel% neq 0 (
    echo [LILO] Aviso: nao foi possivel checar config MCP do Claude Desktop.
    echo        Se Claude Desktop estiver instalado, rode manualmente:
    echo          python "%LILO_ROOT%\scripts\disable_desktop_commander.py"
)

REM -- 1. Ollama (motor LLM local) -----------------------------------
REM Verifica se ja esta rodando
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [LILO] Iniciando Ollama...
    start /MIN "" "ollama" serve
    REM Aguarda Ollama subir
    timeout /t 8 /nobreak >nul
) else (
    echo [LILO] Ollama ja esta rodando.
)

REM -- 2. Dashboard Streamlit (porta 8100) ---------------------------
REM Verifica se ja esta rodando
curl -s http://localhost:8100 >nul 2>&1
if %errorlevel% neq 0 (
    echo [LILO] Iniciando Dashboard Streamlit...
    start /MIN "LILO Dashboard" cmd /c "cd /d %LILO_ROOT% && streamlit run dashboard.py --server.port 8100 --server.headless true"
) else (
    echo [LILO] Dashboard ja esta rodando na porta 8100.
)

REM -- 3. Docker Compose (backend, chromadb, frontend) ---------------
REM Verifica se Docker Desktop esta rodando
docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo [LILO] Docker detectado. Iniciando containers...
    start /MIN "LILO Docker" cmd /c "cd /d %LILO_ROOT% && docker-compose up -d"
) else (
    echo [LILO] Docker Desktop nao esta rodando -- containers nao iniciados.
    echo        Inicie o Docker Desktop manualmente se precisar dos containers.
)

REM -- 4. Villa Lobos (disponivel via PyCharm MCP) -------------------
REM Villa Lobos nao precisa de processo separado -- e chamado
REM sob demanda pelo lilo_pycharm_mcp.py quando o PyCharm
REM invoca as tools villa_pipeline ou villa_quick_ask.
REM Apenas verificamos se o path existe.
if exist "%VILLA_ROOT%\villa_lobos\main.py" (
    echo [LILO] Villa Lobos disponivel em %VILLA_ROOT%
) else (
    echo [LILO] Villa Lobos nao encontrado em %VILLA_ROOT%
)

REM -- Resumo --------------------------------------------------------
echo.
echo ============================================================
echo   LILO v7.0 -- Inicializado
echo ============================================================
echo.
echo   Ollama:      http://localhost:11434
echo   Dashboard:   http://localhost:8100
echo   Backend:     http://localhost:8000  (se Docker ativo)
echo   Frontend:    http://localhost:3000  (se Docker ativo)
echo   ChromaDB:    http://localhost:8001  (se Docker ativo)
echo.
echo   PyCharm MCP: lilo_pycharm_mcp.py (sob demanda)
echo   Claude MCP:  lilo_mcp.py (profile=opus, 18 tools, -53% tokens)
echo.
echo   Esta janela pode ser fechada.
echo ============================================================

REM Fecha automaticamente apos 10s (para pasta Inicializar)
timeout /t 10 /nobreak >nul
