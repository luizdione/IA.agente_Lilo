@echo off
REM ============================================================
REM BUILD_E_ABRIR.bat
REM ------------------------------------------------------------
REM Indexa D:\OneDrive\Documentos\Workaholics e abre a UI da
REM biblioteca em http://localhost:8101
REM
REM Uso (clique duplo ou):
REM     BUILD_E_ABRIR.bat
REM
REM Para apenas reindexar (sem abrir UI):
REM     BUILD_E_ABRIR.bat --build-only
REM ============================================================

REM Configura cmd.exe para UTF-8 (acentos em paths sao exibidos
REM corretamente — interno o scanner sempre lida com unicode).
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

setlocal
cd /d "%~dp0..\.."

set ROOT=D:\OneDrive\Documentos\Workaholics\Artigos PDF

echo.
echo === LILO PDFs_library ===
echo Raiz : %ROOT%
echo.

REM 1) Indexar (varredura)
echo [1/2] Varrendo PDFs (offline, sem tokens)...
python "agents\PDFs_library\scripts\build_workaholics_db.py" --root "%ROOT%"
if errorlevel 1 (
    echo ERRO no scanner. Verifique se PyMuPDF esta instalado:
    echo     pip install pymupdf
    pause
    exit /b 1
)

REM Se --build-only, nao abre UI
if /i "%~1"=="--build-only" goto :done

REM 2) Abrir UI em :8101
echo.
echo [2/2] Abrindo biblioteca em http://localhost:8101 ...
start "" http://localhost:8101
streamlit run "agents\PDFs_library\scripts\library_app.py" --server.port 8101

:done
echo.
echo === Concluido ===
endlocal
