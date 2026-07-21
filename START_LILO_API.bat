@echo off
REM ============================================================
REM  START_LILO_API.bat -- inicia o servidor HTTP do LILO
REM  Endpoints: http://localhost:8088/v1/{health,chat,tools,...}
REM  Ver lilo_api.py para a lista completa.
REM ============================================================

cd /d "%~dp0"

REM Detecta python (preferencia: .venv local, depois conda lilo, depois sistema)
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else if exist "%USERPROFILE%\anaconda3\envs\lilo\python.exe" (
    set "PYTHON=%USERPROFILE%\anaconda3\envs\lilo\python.exe"
) else if exist "%USERPROFILE%\miniconda3\envs\lilo\python.exe" (
    set "PYTHON=%USERPROFILE%\miniconda3\envs\lilo\python.exe"
) else (
    set "PYTHON=python"
)

echo ============================================================
echo  LILO API -- subindo servidor HTTP
echo  Python: %PYTHON%
echo  URL:    http://localhost:8088
echo ============================================================

REM Garante dependencias minimas (ignora se ja instaladas)
"%PYTHON%" -c "import fastapi, uvicorn, sse_starlette" 2>nul
if errorlevel 1 (
    echo [LILO API] Instalando dependencias...
    "%PYTHON%" -m pip install -q fastapi uvicorn sse-starlette pydantic
)

REM Sobe a API
"%PYTHON%" lilo_api.py

pause
