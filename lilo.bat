@echo off
rem LILO v13 — lancador Windows. Duplo clique = REPL; "lilo.bat "tarefa"" = one-shot.
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
python -m lilo %*
set RC=%ERRORLEVEL%
rem Sem argumentos (duplo clique): segura a janela p/ ler a saida ao encerrar.
if "%~1"=="" pause
endlocal & exit /b %RC%
