# Graphical Abstract via FigureLabs (chat.figurelabs.ai)

Procedimento PADRÃO (todos os projetos) para gerar o *graphical abstract* / TOC
graphic no **chat.figurelabs.ai** e ligá-lo às versões TEX/PDF/DOCX.

## Limite honesto de acesso (ler primeiro)
- **Não há acesso autônomo com credenciais.** A skill/scripts NÃO logam na sua
  conta FigureLabs nem geram imagens sozinhos/sem supervisão.
- O acesso é via a **extensão Claude-in-Chrome** dirigindo o **seu Chrome já
  logado** em chat.figurelabs.ai. A geração é **human-in-the-loop**: você pede,
  o assistente opera o navegador ao vivo (a janela é usada). Não é cron/batch
  desacompanhado.
- Pré-requisitos: extensão conectada (`list_connected_browsers`) e você logado
  no FigureLabs. Cada projeto gera SEU graphical abstract (prompt próprio).

## Passo a passo (por artigo)
1. **Montar o prompt** a partir do conteúdo do paper (mecanismo/abstract). Salvar
   em `PAPER/GRAPHICAL_ABSTRACT_PROMPT_figurelabs.md` (versão longa + curta +
   checagem científica). Recipe do prompt:
   - Cena: molécula/entidade central rotulada · atores biológicos (organismos/
     células) · cadeia de setas do mecanismo · contraste de seletividade/controle
     · faixa inferior com evidências ("in vitro · in vivo · in silico").
   - Estilo: "journal graphical abstract, flat vector, white background, muted
     palette, publication quality, clear labels, accurate chemistry, no clutter".
   - **Checagem científica obrigatória** na imagem gerada (não aceitar se errar):
     estrutura química correta, papéis biológicos corretos, sem texto inventado.
2. **Gerar** (Chrome MCP): abrir `https://chat.figurelabs.ai/` → modo *Scientific
   Illustration* (Nano Banana Pro) → colar o prompt → enviar → aguardar (~1–2 min).
3. **Exportar**: botão **Export → PNG** (resolução nativa). O arquivo cai em
   `~/Downloads/`. Mover/renomear para:
   `PAPER/figuras/graphical_abstract_figurelabs.png`
   e espelhar em `artigos_submissao/<projeto>/`.
4. **Ligar ao TEX** (flui para PDF e DOCX no rebuild):
   - Classe **achemso (ACS)**: `\begin{tocentry}\includegraphics[width=\linewidth]{graphical_abstract_figurelabs.png}\end{tocentry}`.
   - Outras classes: figura na 1ª página / TOC graphic com `\includegraphics`.
   - Rebuild normal (`build.sh` / `build_paper.py`) → o GA entra em TEX/PDF/DOCX.
5. **Versão DOCX**: como o DOCX é derivado do TEX/MD pelo pandoc, basta o passo 4
   + rebuild. (Se o DOCX for gerado de MD, inserir `![](figuras/graphical_abstract_figurelabs.png)`
   no ponto do TOC graphic no `.md`.)

## Convenção de nomes
- `graphical_abstract_figurelabs.png` (gerado no FigureLabs) — NÃO confundir com
  `graphical_abstract.pdf/png` (auto-gerado por script Python data-aware, que o
  build pode sobrescrever). Use nome distinto para evitar clobber pelo hook.

## Espelho de submissão
Após o rebuild, o `mirror_submission()` copia TEX/PDF/DOCX + figuras (incluindo o
GA) para `artigos_submissao/<projeto>/` (overwrite; só a versão corrente).

## Reuso / edição
O projeto fica salvo no FigureLabs (`/project/<id>`) — dá para reabrir, refazer
(Region Redraw / Text Edit), Upscale ou trocar o fundo (White BG) e re-exportar.
