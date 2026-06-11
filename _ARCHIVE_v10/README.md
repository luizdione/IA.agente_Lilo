# Arquivos movidos pela refatoração arch-v10 (2026-05-06)

Este diretório contém **tudo o que foi removido da raiz do projeto** durante a simplificação para a arquitetura v10.0.

## Estrutura

```
_ARCHIVE_v10/
├── README.md                ← este arquivo
├── APPLY_arch_v10.bat       ← roteiro de commits git (rodar no Windows)
├── to_delete/               ← lixo confirmado, deletar com segurança após merge
│   ├── _ul                  (0 bytes, arquivo vazio inexplicado)
│   ├── llm-gateway_bioinfo/ (diretório vazio)
│   ├── llm-gateway_sql/     (diretório vazio)
│   ├── llm-gateway_agents/  (lilo_agent.py 328 linhas orphan + health_check.py 68 linhas)
│   ├── llm-gateway_requirements.txt   (duplicado, agora consolidado em requirements.txt da raiz)
│   ├── llm-gateway_pycache/ (cache pycache)
│   ├── lilo_pycharm_mcp.py  (211 linhas, 95% idêntico a lilo_mcp.py)
│   ├── Analise_SQL_root/    (cópia raiz, idêntica ao agents/Analise_SQL/ exceto 1 linha)
│   ├── scholaragent_root/   (idem)
│   └── PDFs_library_root/   (idem; scripts/ e data/workaholics.db já migrados para agents/)
└── v6_fastapi/              ← código FastAPI v6 + React, manter como referência
    ├── backend/             (FastAPI ~3000 linhas — base para futuro lilo_api.py)
    ├── frontend/            (React + nginx — referência de UI)
    ├── docker-compose.yml   (5 serviços: ollama, memory, backend, dashboard, frontend)
    └── Dockerfile.dashboard
```

## Comandos pós-merge

Depois de validar a branch `arch-v10` e fazer merge na `main`:

```bash
# (opcional) deletar lixo permanentemente
rmdir /s /q _ARCHIVE_v10\to_delete

# manter v6_fastapi como referência histórica (ou também deletar se preferir)
# rmdir /s /q _ARCHIVE_v10\v6_fastapi
```

## Antes de commitar

Confirme:

1. `python lilo.py health` retorna OK para todos os subagentes.
2. `python lilo_mcp.py --profile desktop` inicia sem erro.
3. `python lilo_mcp.py --profile pycharm` inicia sem erro.
4. Claude Desktop reconhece o servidor (testar a tool `lilo_health`).
5. Streamlit (`streamlit run dashboard.py`) carrega sem ImportError.

## Reverter tudo

Se algo der errado:

```bash
git checkout main
git branch -D arch-v10
```

E manualmente mover os diretórios de `_ARCHIVE_v10/` de volta para os locais originais (ou usar `git stash apply` se aplicável).

## Estatísticas da refatoração

| Métrica | v9.0 (antes) | v10.0 (depois) | Redução |
|---|---|---|---|
| Pontos de entrada `*.py` na raiz | 5 (lilo, lilo_mcp, lilo_pycharm_mcp, lilo_server, dashboard) | 4 (sem lilo_pycharm_mcp) | -20% |
| Diretórios `agent.py` espalhados | 8 (3 duplicados + 5 únicos) | 6 (todos em `agents/`) | -25% |
| Tools MCP duplicadas | ~10 entre lilo_mcp e lilo_pycharm_mcp | 0 (profile flag) | -100% |
| Diretórios vazios/órfãos | 5 | 0 | -100% |
