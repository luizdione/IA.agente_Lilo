"""
shared/summarize.py -- Sumarizador local generico (V20).

Le QUALQUER arquivo de texto local (.log/.out/.txt/.csv/.tsv/.json/.md, codigo-
fonte, e PDFs via PyMuPDF/pdfminer) e devolve um RESUMO destilado pelo Ollama
LOCAL. O conteudo bruto NUNCA atravessa a fronteira MCP -> Claude: so o resumo
destilado volta ao cliente -- essa e a economia de tokens do Claude.

E o irmao generico de PDFs_library/agent.py::PDFAgent._summarize_file: mesma
ideia (ler local -> destilar via LLM local -> devolver so o resumo), estendida
a qualquer arquivo de texto. Reutiliza shared.llm_client.get_client (tier
'ollama') e a mesma cascata de extracao de PDF (fitz -> pdfminer).

Uso:
    from shared.summarize import summarize_file
    print(summarize_file("/caminho/vina.log", question="melhores poses?"))
"""
from __future__ import annotations

import os
from pathlib import Path

# Limite de ENTRADA enviado ao Ollama (chars). ~12k chars ~= 3k tokens: cabe com
# folga em num_ctx>=4096 do parque local, deixando espaco p/ system + resposta.
_MAX_INPUT_CHARS = int(os.environ.get("LILO_SUMMARIZE_MAX_INPUT", "12000"))

# Extensoes binarias/estruturadas que NAO devem ir cruas ao LLM -- ha tools
# melhores (lilo_pdf p/ PDF, perfil_dados/graphpad p/ planilhas/dados).
_BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp",
    ".zip", ".gz", ".7z", ".rar", ".tar", ".exe", ".dll", ".so", ".bin",
    ".xlsx", ".xls", ".docx", ".pptx", ".odt", ".npz", ".npy", ".parquet",
    ".pzf", ".pzfx", ".pzt", ".dna", ".sqlite", ".db", ".h5", ".hdf5",
}

_SYSTEM = (
    "Voce e um cientista de dados senior (bioinformatica, biologia molecular). "
    "Resuma o CONTEUDO do arquivo de forma densa e FIEL: o que e o arquivo, os "
    "numeros/resultados/erros que importam para uma decisao -- sem encher "
    "linguica. PRESERVE valores numericos exatos (nao arredonde). Se houver uma "
    "PERGUNTA, responda-a primeiro e diretamente. Portugues brasileiro, tecnico."
)


def _clip_head_tail(text: str, limit: int) -> str:
    """Recorta preservando INICIO e FIM (logs guardam o resultado no fim)."""
    if len(text) <= limit:
        return text
    head = int(limit * 0.7)
    tail = limit - head
    omitted = len(text) - limit
    return (text[:head]
            + f"\n\n... [meio omitido -- {omitted} chars] ...\n\n"
            + text[-tail:])


def _read_text(path: Path) -> tuple[str, int]:
    """Devolve (texto, tamanho_original_chars).

    tamanho_original == -1 sinaliza 'binario/nao-textual nao suportado'.
    """
    ext = path.suffix.lower()

    # PDF: mesma cascata do PDFAgent (fitz -> pdfminer).
    if ext == ".pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(path))
            txt = "\n".join(p.get_text() for p in doc)
            return txt, len(txt)
        except Exception:
            pass
        try:
            from pdfminer.high_level import extract_text
            txt = extract_text(str(path))
            return txt, len(txt)
        except Exception:
            return "", -1

    if ext in _BINARY_EXT:
        return "", -1

    # Texto: utf-8 -> latin-1 (mesma cascata tolerante do fs_read).
    try:
        raw = path.read_bytes()
    except Exception as e:  # noqa: BLE001
        return f"[erro ao ler bytes: {e}]", 0
    for enc in ("utf-8", "latin-1"):
        try:
            txt = raw.decode(enc)
            return txt, len(txt)
        except UnicodeDecodeError:
            continue
    return "", -1


def summarize_file(path: str, question: str = "", max_chars: int = 1200) -> str:
    """Le um arquivo local e devolve um resumo destilado pelo Ollama LOCAL.

    O arquivo bruto nao atravessa a fronteira MCP -> Claude; so o resumo volta.

    Args:
        path: caminho do arquivo local.
        question: pergunta especifica a responder (opcional).
        max_chars: teto de caracteres do resumo (default 1200 ~= 300 tokens).
    """
    p = Path(path).expanduser()
    if not p.exists():
        return f"[summarize] Arquivo nao encontrado: {path}"
    if p.is_dir():
        return f"[summarize] E um diretorio, nao um arquivo: {path}"

    text, orig = _read_text(p)
    if orig == -1:
        return (f"[summarize] Formato binario/nao-textual nao suportado ({p.suffix}). "
                f"Use lilo_pdf (PDF) ou as skills perfil_dados/graphpad (planilhas/dados).")
    if not text.strip():
        return f"[summarize] Nao foi possivel extrair texto de: {p.name}"

    snippet = _clip_head_tail(text, _MAX_INPUT_CHARS)
    prompt = f"ARQUIVO: {p.name}\n\nCONTEUDO:\n{snippet}"
    if question:
        prompt += f"\n\nPERGUNTA ESPECIFICA: {question}"

    # max_tokens da RESPOSTA proporcional ao teto pedido (~3-4 chars/token) + folga.
    resp_tokens = max(256, min(1024, max_chars // 3))
    try:
        from shared.llm_client import get_client
        # tier='ollama' forca o backend LOCAL: destilar NUNCA gasta token do Claude.
        out = get_client().chat(prompt, system=_SYSTEM, tier="ollama",
                                max_tokens=resp_tokens, cot=False)
    except Exception as e:  # noqa: BLE001
        return f"[summarize] Erro ao destilar via Ollama local: {e}"

    out = (out or "").strip()
    if len(out) > max_chars:
        out = out[:max_chars] + f"\n... [resumo truncado em {max_chars} chars]"
    header = f"[resumo local de {p.name} -- {orig} chars destilados via Ollama, sem entrar no contexto]"
    return f"{header}\n\n{out}"
