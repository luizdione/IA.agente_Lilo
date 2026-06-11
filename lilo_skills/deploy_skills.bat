@echo off
REM ============================================================
REM  LILO Skills Deploy — Copia SKILL.md para Claude Desktop
REM  Execute como administrador se necessario
REM ============================================================

SET SRC=%~dp0skills
SET DST_BASE=%APPDATA%\Claude\local-agent-mode-sessions\skills-plugin

REM Encontrar o diretorio de skills automaticamente
FOR /D %%A IN ("%DST_BASE%\*") DO (
  FOR /D %%B IN ("%%A\*") DO (
    IF EXIST "%%B\skills\docx\SKILL.md" (
      SET DST=%%B\skills
    )
  )
)

IF NOT DEFINED DST (
  echo [ERRO] Nao foi possivel encontrar a pasta de skills do Claude Desktop.
  echo Verifique se o Claude Desktop esta instalado.
  pause
  exit /b 1
)

echo [INFO] Destino: %DST%
echo.

SET SKILLS=lilo_chat lilo_sql lilo_pdf lilo_scholar prism_analyze prism_classify prism_audit villa_pipeline villa_quick_ask lilo_web_search lilo_web_fetch lilo_health lilo_models

FOR %%S IN (%SKILLS%) DO (
  IF EXIST "%SRC%\%%S\SKILL.md" (
    IF NOT EXIST "%DST%\%%S" mkdir "%DST%\%%S"
    copy /Y "%SRC%\%%S\SKILL.md" "%DST%\%%S\SKILL.md" > nul
    echo [OK] %%S
  ) ELSE (
    echo [SKIP] %%S - SKILL.md nao encontrado
  )
)

echo.
echo ============================================================
echo  Deploy concluido! Reinicie o Claude Desktop para aplicar.
echo  As skills apareceram no menu / como:
echo    /lilo_chat  /lilo_sql  /lilo_pdf  /lilo_scholar
echo    /prism_analyze  /prism_classify  /prism_audit
echo    /villa_pipeline  /villa_quick_ask
echo    /lilo_web_search  /lilo_web_fetch
echo    /lilo_health  /lilo_models
echo ============================================================
pause
