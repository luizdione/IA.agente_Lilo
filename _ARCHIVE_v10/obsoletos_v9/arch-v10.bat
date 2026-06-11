@echo off
REM ============================================================
REM  arch-v10 — Roteiro de commits para o usuario rodar no Windows
REM  Pre-requisito: cd para C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
REM  ============================================================

echo.
echo ============================================================
echo  LILO arch-v10 - Refatoracao para arquitetura simplificada
echo ============================================================
echo.
echo  As mudancas no filesystem JA FORAM APLICADAS pelo Claude.
echo  Este script apenas faz os commits no git em ordem atomica.
echo.

REM Repara o index corrompido se houver
git status >nul 2>&1
if errorlevel 1 (
    echo [INFO] Reparando index do git...
    del .git\index 2>nul
    git read-tree HEAD
)

git checkout -b arch-v10
if errorlevel 1 (
    echo [WARN] Branch arch-v10 ja existe. Use 'git checkout arch-v10' e siga manualmente.
    pause
    exit /b 1
)

REM ── Commit A — lixo confirmado ──────────────────────────────
git add -A _ARCHIVE_v10/to_delete/_ul _ARCHIVE_v10/to_delete/llm-gateway_*
git rm --cached -r _ul llm-gateway/bioinfo llm-gateway/sql 2>nul
git rm --cached -f llm-gateway/agents/lilo_agent.py llm-gateway/agents/health_check.py llm-gateway/requirements.txt 2>nul
git commit -m "arch-v10 [A]: remove lixo confirmado (orfaos, dirs vazios)" -m "Movido para _ARCHIVE_v10/to_delete/: _ul, llm-gateway/bioinfo, llm-gateway/sql, llm-gateway/agents/lilo_agent.py (328 linhas orfaes), health_check.py, requirements.txt duplicado."

REM ── Commit C — archive backend/frontend/docker ─────────────
git add -A _ARCHIVE_v10/v6_fastapi/
git rm --cached -r backend frontend 2>nul
git rm --cached -f docker-compose.yml Dockerfile.dashboard 2>nul
git commit -m "arch-v10 [C]: archive backend/frontend/Docker para _ARCHIVE_v10/v6_fastapi/" -m "FastAPI v6 (~3000 linhas) e React frontend nao iniciados pelo START_LILO_WINDOWS.bat. Mantidos como referencia para o futuro lilo_api.py v10."

REM ── Commit D — llm-gateway → agents/gateway ────────────────
git add -A agents/gateway/ config/litellm_config.yaml shared/llm_client.py
git rm --cached -r llm-gateway 2>nul
git commit -m "arch-v10 [D]: llm-gateway/ -> agents/gateway/ + config/" -m "Move agent.py para agents/gateway/agent.py (uniformiza com demais subagentes). litellm_config.yaml para config/. Atualiza imports em lilo.py e dashboard.py."

REM ── Commit B — copias raiz dos subagentes ──────────────────
git add -A agents/PDFs_library/scripts agents/PDFs_library/data
git rm --cached -r Analise_SQL scholaragent PDFs_library 2>nul
git commit -m "arch-v10 [B]: remove copias raiz de Analise_SQL, scholaragent, PDFs_library" -m "Diff entre raiz e agents/ era 1 linha (path resolution). PDFs_library/scripts/ e workaholics.db migrados para agents/PDFs_library/. dashboard.py ja apontava para agents/."

REM ── Commit E — MCP unificado ───────────────────────────────
git add lilo_mcp.py config/mcp/ docs/
git rm --cached -f lilo_pycharm_mcp.py 2>nul
git commit -m "arch-v10 [E]: unifica lilo_mcp.py com flag --profile {desktop,pycharm,http}" -m "lilo_pycharm_mcp.py (211 linhas, 95% identico) eliminado. Profile pycharm expoe 10 tools, desktop expoe 16. Adiciona config/mcp/ com perfis prontos."

REM ── Commit das correcoes da auditoria anterior ─────────────
git add shared/policy.py shared/llm_client.py requirements.txt lilo_skills/skills/bio lilo_skills/schemas/bio
git commit -m "arch-v10: aplica patches da auditoria 2026-05-06" -m "- shared/policy.py: 26 tokens DM/OpenMM em COMPLEX_INDICATORS
- shared/llm_client.py: ordem LiteLLM-first (alinhada com docstring)
- shared/policy.py + llm_client.py: restaura truncamento (NameError, SyntaxError)
- requirements.txt: declara duckduckgo-search, bs4, lxml
- lilo_skills/skills/bio/openmm_nvt_equilibration_safe.py: NOVA skill anti-NaN"

echo.
echo ============================================================
echo  Refatoracao concluida em branch arch-v10
echo  Verifique com:    git log --oneline arch-v10
echo  Testes:           python lilo.py health
echo                    python lilo_mcp.py --profile desktop
echo  Merge se OK:      git checkout main ^&^& git merge arch-v10
echo ============================================================
echo.
echo  Apos validar e mergear, voce pode deletar permanentemente:
echo    rmdir /s /q _ARCHIVE_v10\to_delete
echo  (mantenha _ARCHIVE_v10\v6_fastapi como referencia historica)
echo.
pause@echo off
REM ============================================================
REM  arch-v10 — Roteiro de commits para o usuario rodar no Windows
REM  Pre-requisito: cd para C:\Users\luizd\OneDrive\Data_Science\Projetos\IA.agente
REM  ============================================================

echo.
echo ============================================================
echo  LILO arch-v10 - Refatoracao para arquitetura simplificada
echo ============================================================
echo.
echo  As mudancas no filesystem JA FORAM APLICADAS pelo Claude.
echo  Este script apenas faz os commits no git em ordem atomica.
echo.

REM Repara o index corrompido se houver
git status >nul 2>&1
if errorlevel 1 (
    echo [INFO] Reparando index do git...
    del .git\index 2>nul
    git read-tree HEAD
)

git checkout -b arch-v10
if errorlevel 1 (
    echo [WARN] Branch arch-v10 ja existe. Use 'git checkout arch-v10' e siga manualmente.
    pause
    exit /b 1
)

REM ── Commit A — lixo confirmado ──────────────────────────────
git add -A _ARCHIVE_v10/to_delete/_ul _ARCHIVE_v10/to_delete/llm-gateway_*
git rm --cached -r _ul llm-gateway/bioinfo llm-gateway/sql 2>nul
git rm --cached -f llm-gateway/agents/lilo_agent.py llm-gateway/agents/health_check.py llm-gateway/requirements.txt 2>nul
git commit -m "arch-v10 [A]: remove lixo confirmado (orfaos, dirs vazios)" -m "Movido para _ARCHIVE_v10/to_delete/: _ul, llm-gateway/bioinfo, llm-gateway/sql, llm-gateway/agents/lilo_agent.py (328 linhas orfaes), health_check.py, requirements.txt duplicado."

REM ── Commit C — archive backend/frontend/docker ─────────────
git add -A _ARCHIVE_v10/v6_fastapi/
git rm --cached -r backend frontend 2>nul
git rm --cached -f docker-compose.yml Dockerfile.dashboard 2>nul
git commit -m "arch-v10 [C]: archive backend/frontend/Docker para _ARCHIVE_v10/v6_fastapi/" -m "FastAPI v6 (~3000 linhas) e React frontend nao iniciados pelo START_LILO_WINDOWS.bat. Mantidos como referencia para o futuro lilo_api.py v10."

REM ── Commit D — llm-gateway → agents/gateway ────────────────
git add -A agents/gateway/ config/litellm_config.yaml shared/llm_client.py
git rm --cached -r llm-gateway 2>nul
git commit -m "arch-v10 [D]: llm-gateway/ -> agents/gateway/ + config/" -m "Move agent.py para agents/gateway/agent.py (uniformiza com demais subagentes). litellm_config.yaml para config/. Atualiza imports em lilo.py e dashboard.py."

REM ── Commit B — copias raiz dos subagentes ──────────────────
git add -A agents/PDFs_library/scripts agents/PDFs_library/data
git rm --cached -r Analise_SQL scholaragent PDFs_library 2>nul
git commit -m "arch-v10 [B]: remove copias raiz de Analise_SQL, scholaragent, PDFs_library" -m "Diff entre raiz e agents/ era 1 linha (path resolution). PDFs_library/scripts/ e workaholics.db migrados para agents/PDFs_library/. dashboard.py ja apontava para agents/."

REM ── Commit E — MCP unificado ───────────────────────────────
git add lilo_mcp.py config/mcp/ docs/
git rm --cached -f lilo_pycharm_mcp.py 2>nul
git commit -m "arch-v10 [E]: unifica lilo_mcp.py com flag --profile {desktop,pycharm,http}" -m "lilo_pycharm_mcp.py (211 linhas, 95% identico) eliminado. Profile pycharm expoe 10 tools, desktop expoe 16. Adiciona config/mcp/ com perfis prontos."

REM ── Commit das correcoes da auditoria anterior ─────────────
git add shared/policy.py shared/llm_client.py requirements.txt lilo_skills/skills/bio lilo_skills/schemas/bio
git commit -m "arch-v10: aplica patches da auditoria 2026-05-06" -m "- shared/policy.py: 26 tokens DM/OpenMM em COMPLEX_INDICATORS
- shared/llm_client.py: ordem LiteLLM-first (alinhada com docstring)
- shared/policy.py + llm_client.py: restaura truncamento (NameError, SyntaxError)
- requirements.txt: declara duckduckgo-search, bs4, lxml
- lilo_skills/skills/bio/openmm_nvt_equilibration_safe.py: NOVA skill anti-NaN"

echo.
echo ============================================================
echo  Refatoracao concluida em branch arch-v10
echo  Verifique com:    git log --oneline arch-v10
echo  Testes:           python lilo.py health
echo                    python lilo_mcp.py --profile desktop
echo  Merge se OK:      git checkout main ^&^& git merge arch-v10
echo ============================================================
echo.
echo  Apos validar e mergear, voce pode deletar permanentemente:
echo    rmdir /s /q _ARCHIVE_v10\to_delete
echo  (mantenha _ARCHIVE_v10\v6_fastapi como referencia historica)
echo.
pause