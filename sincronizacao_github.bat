@echo off
REM ============================================================
REM  LILO v7.0 — Sincronizacao com GitHub
REM ============================================================
REM  Repositorio: https://github.com/luizdione/IA.gente_Lilo
REM
REM  Uso:
REM    sincronizacao_github.bat              (commit + push padrao)
REM    sincronizacao_github.bat "mensagem"   (commit com mensagem custom)
REM ============================================================

set REPO_URL=https://github.com/luizdione/IA.gente_Lilo.git
set LILO_ROOT=C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente

cd /d "%LILO_ROOT%"

REM ── Verificar se git esta instalado ──────────────────────────
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Git nao encontrado! Instale: winget install Git.Git
    pause
    exit /b 1
)

REM ── Inicializar repo se necessario ───────────────────────────
if not exist ".git" (
    echo [INIT] Inicializando repositorio Git...
    git init
    git branch -M main
    git remote add origin %REPO_URL%
    echo [INIT] Repositorio inicializado com remote 'origin'
)

REM ── Verificar remote ─────────────────────────────────────────
git remote get-url origin >nul 2>&1
if %errorlevel% neq 0 (
    echo [FIX] Adicionando remote origin...
    git remote add origin %REPO_URL%
)

REM ── Limpar __pycache__ antes do commit ───────────────────────
echo [CLEAN] Removendo __pycache__...
for /d /r %%d in (__pycache__) do if exist "%%d" rmdir /s /q "%%d"

REM ── Stage + Commit ───────────────────────────────────────────
git add -A

REM Mensagem de commit
if "%~1"=="" (
    for /f "tokens=1-3 delims=/ " %%a in ('date /t') do set DATA=%%c-%%b-%%a
    for /f "tokens=1-2 delims=: " %%a in ('time /t') do set HORA=%%a:%%b
    set MSG=LILO auto-sync %DATA% %HORA%
) else (
    set MSG=%~1
)

REM Verificar se ha mudancas
git diff --cached --quiet
if %errorlevel% equ 0 (
    echo [INFO] Nenhuma mudanca para commitar.
    goto :pull
)

echo [COMMIT] %MSG%
git commit -m "%MSG%"

:pull
REM ── Pull (rebase) + Push ─────────────────────────────────────
echo [SYNC] Sincronizando com GitHub...
git pull --rebase origin main 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Primeiro push — sem historico remoto para pull.
)

git push -u origin main
if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo   Sincronizacao concluida!
    echo   https://github.com/luizdione/IA.gente_Lilo
    echo ============================================================
) else (
    echo.
    echo [ERRO] Push falhou. Verifique:
    echo   1. Credenciais Git configuradas (gh auth login)
    echo   2. Repositorio existe no GitHub
    echo   3. Permissoes de escrita
    echo.
    echo   Para criar o repo: gh repo create luizdione/IA.gente_Lilo --public
)

pause
