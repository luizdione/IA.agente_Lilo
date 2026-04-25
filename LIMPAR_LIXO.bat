@echo off
echo ============================================================
echo   LILO v7.0 — Limpeza de Arquivos Desnecessarios
echo ============================================================
echo.
echo   Este script remove arquivos mortos de versoes anteriores.
echo   Pressione Ctrl+C para cancelar.
echo.
pause

cd /d "C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente"

echo.
echo [1/8] Removendo Analise_SQL/.venv (371MB+)...
if exist "Analise_SQL\.venv" rmdir /s /q "Analise_SQL\.venv"

echo [2/8] Removendo diretorios IDE...
if exist ".codex" rmdir /s /q ".codex"
if exist ".cursor" rmdir /s /q ".cursor"
if exist ".junie" rmdir /s /q ".junie"
if exist ".continue" rmdir /s /q ".continue"
if exist "Analise_SQL\.idea" rmdir /s /q "Analise_SQL\.idea"
if exist "PDFs_library\.idea" rmdir /s /q "PDFs_library\.idea"
if exist "scholaragent\.idea" rmdir /s /q "scholaragent\.idea"
if exist "llm-gateway\.idea" rmdir /s /q "llm-gateway\.idea"
if exist "llm-gateway\.vscode" rmdir /s /q "llm-gateway\.vscode"

echo [3/8] Removendo arquivos lixo do Windows...
if exist "nul" del /f "nul"
del /f "START_LILO_WINDOWS.bat - Atalho.lnk" 2>nul

echo [4/8] Removendo configs obsoletas...
if exist ".env.docker" del /f ".env.docker"
if exist ".claude_analysis.json" del /f ".claude_analysis.json"
if exist "config\lilo_optimized.json" del /f "config\lilo_optimized.json"
if exist "config\settings.example.yaml" del /f "config\settings.example.yaml"
if exist "config\claude_api.yaml" del /f "config\claude_api.yaml"

echo [5/8] Removendo scripts antigos dos subagentes...
if exist "Analise_SQL\run_sql_analyzer.bat" del /f "Analise_SQL\run_sql_analyzer.bat"
if exist "Analise_SQL\nasa_weather_api.py" del /f "Analise_SQL\nasa_weather_api.py"
if exist "Analise_SQL\plugin_nasa.py" del /f "Analise_SQL\plugin_nasa.py"
if exist "Analise_SQL\test_connection.py" del /f "Analise_SQL\test_connection.py"
if exist "Analise_SQL\sql_analyzer_icon.ico" del /f "Analise_SQL\sql_analyzer_icon.ico"
if exist "Analise_SQL\sql_analyzer_icon.png" del /f "Analise_SQL\sql_analyzer_icon.png"
if exist "Analise_SQL\.installed" del /f "Analise_SQL\.installed"
if exist "Analise_SQL\NOVIDADES.md" del /f "Analise_SQL\NOVIDADES.md"
if exist "Analise_SQL\SQL_ANALYZER_README.md" del /f "Analise_SQL\SQL_ANALYZER_README.md"
if exist "scholaragent\Iniciar_ScholarAgent.bat" del /f "scholaragent\Iniciar_ScholarAgent.bat"
if exist "scholaragent\start_scholaragent.bat" del /f "scholaragent\start_scholaragent.bat"
if exist "PDFs_library\inicializar.bat" del /f "PDFs_library\inicializar.bat"
if exist "llm-gateway\start.bat" del /f "llm-gateway\start.bat"
if exist "llm-gateway\lilo.ps1" del /f "llm-gateway\lilo.ps1"
if exist "llm-gateway\.continuerc.json" del /f "llm-gateway\.continuerc.json"
if exist "llm-gateway\.env.example" del /f "llm-gateway\.env.example"

echo [6/8] Removendo diretorio corrompido do scholaragent...
if exist "scholaragent\{static,templates,uploads}" rmdir /s /q "scholaragent\{static,templates,uploads}"

echo [7/8] Removendo __pycache__ em todo o projeto...
for /d /r %%d in (__pycache__) do if exist "%%d" rmdir /s /q "%%d"

echo [8/8] Removendo diretorios de versoes antigas (se ainda existirem)...
if exist "src" rmdir /s /q "src"
if exist "maintenance" rmdir /s /q "maintenance"
if exist "ajuda_atualizacao" rmdir /s /q "ajuda_atualizacao"
if exist "examples" rmdir /s /q "examples"
if exist "workspace" rmdir /s /q "workspace"
if exist "tools" rmdir /s /q "tools"
if exist "ide-assistant" rmdir /s /q "ide-assistant"

echo.
echo ============================================================
echo   Limpeza concluida!
echo ============================================================
pause
