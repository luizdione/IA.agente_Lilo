---
name: gerente_memoria
description: >
  Gerente de memoria do projeto LILO: atualiza o CONTEXT.md da raiz (estado,
  entregas, pendencias, decisoes) para que qualquer sessao — LILO ou Claude
  Code — retome o projeto sem re-explorar o repositorio. Use quando o usuario
  pedir para salvar/atualizar o contexto ou a memoria do projeto, "onde
  paramos", ou ao encerrar uma rodada de trabalho relevante.
---

# /gerente_memoria — memoria do projeto com economia de tokens

## Principio

O `CONTEXT.md` (raiz) e a memoria compartilhada do projeto: o LILO o le
automaticamente (dir_synthesis, E4) e o Claude Code o enxerga em toda sessao.
A parte mecanica (versao, git, testes, diagnostico, entregas) e regenerada
por script com **0 tokens**; o seu papel e so curar as secoes MANUAL.

## Protocolo (obrigatorio)

1. **UM comando primeiro:** `python scripts/memoria_projeto.py`
   (`--no-diag` se o diagnostico ja rodou nesta sessao). Ele regenera as
   secoes AUTO e preserva as MANUAL byte a byte.
2. Depois, atualize APENAS as secoes MANUAL do `CONTEXT.md`, refletindo a
   sessao: pendencias concluidas saem, novas entram (com dono: "so na
   maquina do dono" quando for o caso); decisoes novas em 1 linha cada.
3. Limites rigidos (o arquivo entra em contexto de sessao):
   - Pendencias: <= 8 itens. Decisoes: <= 10 linhas. Total: <= 80 linhas.
   - Nao duplicar o que ja vive no CHANGELOG/README — memoria e estado,
     nao historico.
4. Nao edite dentro dos marcadores `<!-- AUTO:... -->`.
5. Se algo mudou, commite junto com o trabalho da sessao (mensagem
   `docs(memoria): ...`) — o CONTEXT.md desatualizado e pior que ausente.

## Saida esperada

Resumo de 3-6 linhas: o que o script atualizou + o que voce mudou nas
secoes MANUAL. Nada de despejar o arquivo inteiro na conversa.
