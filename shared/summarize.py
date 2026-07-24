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

V20.1 (apos auditoria adversarial): (a) erro de leitura NUNCA vira "conteudo"
destilado -- e um estado terminal; (b) deteccao de binario por SNIFF de conteudo
(NUL/proporcao nao-texto), nao por blacklist de extensao (latin-1 nunca falha);
(c) teto de LEITURA em bytes (nao materializa arquivo gigante em RAM);
(d) max_chars saneado (clamp).

Uso:
    from shared.summarize import summarize_file
    print(summarize_file("/caminho/vina.log", question="melhores poses?"))
"""
from __future__ import annotations

import os
from pathlib import Path

# Limite de ENTRADA (chars) enviado ao Ollama. ~12k chars ~= 3k tokens.
_MAX_INPUT_CHARS = int(os.environ.get("LILO_SUMMARIZE_MAX_INPUT", "12000"))
# Teto de LEITURA (bytes): nunca materializar arquivo gigante em RAM. Folga de
# 4 bytes/char (pior caso UTF-8) sobre o limite de chars do prompt.
_MAX_READ_BYTES = int(os.environ.get("LILO_SUMMARIZE_MAX_READ",
                                     str(_MAX_INPUT_CHARS * 4 + 8192)))
# Clamp superior do resumo (evita max_chars gigante silenciosamente ignorado).
_MAX_OUT_CHARS = 20000

# Extensoes binarias/estruturadas conhecidas -- atalho barato antes do sniff.
_BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp",
    ".zip", ".gz", ".7z", ".rar", ".tar", ".exe", ".dll", ".so", ".bin",
    ".xlsx", ".xls", ".docx", ".pptx", ".odt", ".npz", ".npy", ".parquet",
    ".pzf", ".pzfx", ".pzt", ".dna", ".sqlite", ".db", ".h5", ".hdf5",
    ".bam", ".cram", ".bcf", ".rds", ".rdata", ".pkl", ".pickle",
}

_SYSTEM = (
    "Voce e um cientista de dados senior (bioinformatica, biologia molecular). "
    "Resuma o CONTEUDO do arquivo de forma densa e FIEL: o que e o arquivo, os "
    "numeros/resultados/erros que importam para uma decisao -- sem encher "
    "linguica. PRESERVE valores numericos exatos (nao arredonde). Se houver uma "
    "PERGUNTA, responda-a primeiro e diretamente. Portugues brasileiro, tecnico."
)

# Bytes considerados "texto" para o sniff de binario.
_TEXT_BYTES = set(range(0x20, 0x7f)) | {0x09, 0x0a, 0x0d, 0x0c, 0x08}


def _looks_binary(raw: bytes) -> bool:
    """Heuristica robusta: NUL == binario; >30% de bytes de controle nao-texto
    na faixa ASCII == binario. (latin-1 decodifica qualquer byte, entao a guarda
    por 'UnicodeDecodeError' era codigo morto -- por isso sniffamos o conteudo.)"""
    head = raw[:8192]
    if not head:
        return False
    if b"\x00" in head:
        return True
    nontext = sum(1 for b in head if b < 0x80 and b not in _TEXT_BYTES)
    return (nontext / len(head)) > 0.30


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
    """Devolve (texto, orig).

    orig == -1 : binario/nao-textual nao suportado.
    orig == -2 : ERRO de leitura (o texto e a mensagem de erro, NAO conteudo).
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

    # Texto: ler so o teto (nunca o arquivo inteiro), depois sniff de binario.
    try:
        with open(path, "rb") as fh:
            raw = fh.read(_MAX_READ_BYTES + 1)
    except Exception as e:  # noqa: BLE001
        return f"[erro ao ler bytes: {e}]", -2
    if _looks_binary(raw):
        return "", -1
    raw = raw[:_MAX_READ_BYTES]
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc), len(raw)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), len(raw)


def summarize_file(path: str, question: str = "", max_chars: int = 1200) -> str:
    """Le um arquivo local e devolve um resumo destilado pelo Ollama LOCAL.

    O arquivo bruto nao atravessa a fronteira MCP -> Claude; so o resumo volta.

    Args:
        path: caminho do arquivo local.
        question: pergunta especifica a responder (opcional).
        max_chars: teto de caracteres do resumo (default 1200 ~= 300 tokens).
    """
    # Saneamento de max_chars (vem do chamador MCP): 0/negativo/nao-int -> default;
    # gigante -> clamp. Evita descartar o resumo inteiro ou ignorar o teto.
    try:
        max_chars = int(max_chars)
    except (TypeError, ValueError):
        max_chars = 1200
    if max_chars <= 0:
        max_chars = 1200
    max_chars = min(max_chars, _MAX_OUT_CHARS)

    p = Path(path).expanduser()
    if not p.exists():
        return f"[summarize] Arquivo nao encontrado: {path}"
    if p.is_dir():
        return f"[summarize] E um diretorio, nao um arquivo: {path}"

    text, orig = _read_text(p)
    if orig == -2:
        # Erro de leitura NAO vira conteudo destilado (nunca fabricar resumo).
        return f"[summarize] Falha ao ler {p.name}: {text}"
    if orig == -1:
        return (f"[summarize] Formato binario/nao-textual nao suportado ({p.suffix or '?'}). "
                f"Use lilo_pdf (PDF) ou perfil_dados/graphpad (planilhas/dados).")
    if not text.strip():
        return f"[summarize] Nao foi possivel extrair texto de: {p.name}"

    snippet = _clip_head_tail(text, _MAX_INPUT_CHARS)
    prompt = f"ARQUIVO: {p.name}\n\nCONTEUDO:\n{snippet}"
    if question:
        prompt += f"\n\nPERGUNTA ESPECIFICA: {question}"

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
