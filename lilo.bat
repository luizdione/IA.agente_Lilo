@echo off
rem LILO v14 - lancador Windows. Duplo clique = abre a interface no navegador.
rem   lilo.bat status | up | down | warm | bench | gpu-livre [motivo] | gpu-ok
powershell -NoProfile -File "%~dp0lilo.ps1" %*
set RC=%ERRORLEVEL%
rem Sem argumentos (duplo clique): segura a janela p/ ler a saida.
if "%~1"=="" pause
exit /b %RC%
