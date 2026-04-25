@echo off
echo =========================================
echo   LILO v7.0 — Iniciando Sistema
echo =========================================
echo.

REM Verificar se Docker esta rodando
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Docker nao esta rodando!
    echo        Inicie o Docker Desktop e tente novamente.
    pause
    exit /b 1
)

REM Build e start
echo [1/3] Construindo containers...
docker-compose build
if errorlevel 1 (
    echo.
    echo [ERRO] Falha no build! Tente: docker-compose build --no-cache
    pause
    exit /b 1
)

echo.
echo [2/3] Iniciando servicos...
docker-compose up -d
if errorlevel 1 (
    echo [ERRO] Falha ao iniciar! Veja: docker-compose logs
    pause
    exit /b 1
)

echo.
echo [3/3] Aguardando servicos...
timeout /t 15 /nobreak >nul

echo.
echo Status:
docker-compose ps

echo.
echo =========================================
echo   LILO v7.0 inicializado!
echo =========================================
echo.
echo   Dashboard:  http://localhost:8506
echo   Frontend:   http://localhost:3000
echo   API:        http://localhost:8000/docs
echo   Ollama:     http://localhost:11434
echo   ChromaDB:   http://localhost:8001
echo.
echo   Logs:    docker-compose logs -f
echo   Parar:   docker-compose down
echo.
pause
