"""
app.py — ScholarAgent
Agente local para sumarização de PDFs científicos com LLM via Ollama.
Autor: Dione B. Melo
"""

import os
import json
import traceback
from pathlib import Path

from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename

import ollama_client
import pdf_processor
import reference_formatter

# ─── Configuração ────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {"pdf"}

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ─── System Prompts por modo ─────────────────────────────────────────────────
SYSTEM_PROMPTS = {
    "simple": (
        "Você é um pesquisador sênior com expertise em bioquímica, biologia molecular, "
        "parasitologia e biotecnologia. Resuma o artigo científico fornecido de forma "
        "clara e concisa, destacando: objetivo, metodologia principal, resultados-chave "
        "e conclusão. Use linguagem técnica adequada. Responda em português brasileiro."
    ),
    "introduction": (
        "Você é um pesquisador sênior escrevendo a seção de Introdução de um artigo científico. "
        "Com base no texto fornecido, produza um resumo analítico que possa ser usado como "
        "suporte para redigir uma introdução. Inclua:\n"
        "- Contexto do problema e lacuna no conhecimento\n"
        "- Hipótese ou objetivo central dos autores\n"
        "- Relevância para o campo\n"
        "- Principais conceitos/moléculas/organismos mencionados\n"
        "Redija em formato de texto corrido, não em tópicos. Português brasileiro, "
        "linguagem técnica de nível de doutorado."
    ),
    "methods": (
        "Você é um pesquisador sênior analisando a seção de Métodos de um artigo científico. "
        "Extraia e organize as informações metodológicas do texto fornecido:\n"
        "- Desenho experimental\n"
        "- Modelos biológicos (organismos, linhagens celulares, enzimas-alvo)\n"
        "- Técnicas analíticas e instrumentação\n"
        "- Softwares e parâmetros computacionais\n"
        "- Controles e critérios estatísticos\n"
        "Apresente de forma estruturada e precisa, em português brasileiro."
    ),
    "graph": (
        "Você é um pesquisador sênior especialista em análise de dados experimentais. "
        "Analise a imagem do gráfico/figura fornecida e produza:\n"
        "1. Descrição do tipo de gráfico e variáveis representadas\n"
        "2. Tendências e padrões principais observados\n"
        "3. Valores notáveis (picos, vales, outliers, significância estatística se indicada)\n"
        "4. Interpretação biológica/bioquímica dos resultados\n"
        "5. Sugestão de texto para seção de Resultados\n"
        "Responda em português brasileiro, linguagem técnica."
    ),
}

# ─── Metadados dos Modelos ───────────────────────────────────────────────────
MODEL_SPECS = {
    "mistral-large-3:675b-cloud": {
        "name": "Mistral Large 3 (675B)",
        "description": "🎓 Premium - Análises profundas e introduções acadêmicas",
        "best_for": ["introduction"],
        "speed": "lento",
        "quality": "excelente",
    },
    "gpt-oss:120b-cloud": {
        "name": "GPT-OSS (120B)",
        "description": "📚 Avançado - Resumos detalhados de textos longos",
        "best_for": ["introduction", "simple"],
        "speed": "lento",
        "quality": "muito bom",
    },
    "gpt-oss:20b-cloud": {
        "name": "GPT-OSS (20B)",
        "description": "📖 Intermediário - Resumos gerais com boa qualidade",
        "best_for": ["simple"],
        "speed": "médio",
        "quality": "bom",
    },
    "deepseek-coder-v2:16b": {
        "name": "DeepSeek Coder V2 (16B)",
        "description": "💻 Especialista - Métodos computacionais/bioinformática",
        "best_for": ["methods"],
        "speed": "médio",
        "quality": "muito bom",
    },
    "qwen2.5-coder:14b": {
        "name": "Qwen 2.5 Coder (14B)",
        "description": "🔬 Estruturado - Protocolos e métodos experimentais",
        "best_for": ["methods"],
        "speed": "médio",
        "quality": "muito bom",
    },
    "qwen2.5-coder:7b-instruct": {
        "name": "Qwen 2.5 Coder (7B)",
        "description": "🧪 Métodos - Versão rápida para protocolos",
        "best_for": ["methods"],
        "speed": "rápido",
        "quality": "bom",
    },
    "phi3:14b-medium-128k-instruct-q4_K_M": {
        "name": "Phi-3 Medium (14B)",
        "description": "🧠 Contexto longo - Bom para textos extensos",
        "best_for": ["simple", "introduction"],
        "speed": "médio",
        "quality": "bom",
    },
    "codellama:13b-instruct-q4_K_M": {
        "name": "CodeLlama (13B)",
        "description": "⚙️ Código - Pipelines e scripts computacionais",
        "best_for": ["methods"],
        "speed": "médio",
        "quality": "bom",
    },
    "llama3.1:8b-instruct-q8_0": {
        "name": "Llama 3.1 (8B)",
        "description": "⚡ Balanceado - Uso geral (recomendado)",
        "best_for": ["simple", "introduction", "methods"],
        "speed": "rápido",
        "quality": "bom",
    },
    "mistral:7b-instruct-q5_K_M": {
        "name": "Mistral (7B)",
        "description": "🚀 Rápido - Resumos simples com baixa latência",
        "best_for": ["simple"],
        "speed": "muito rápido",
        "quality": "bom",
    },
    "llava:7b": {
        "name": "LLaVA (7B)",
        "description": "📊 Visão - Análise de gráficos e figuras (recomendado)",
        "best_for": ["graph"],
        "speed": "rápido",
        "quality": "bom",
    },
    "llava:13b": {
        "name": "LLaVA (13B)",
        "description": "📈 Visão Premium - Análise detalhada de imagens",
        "best_for": ["graph"],
        "speed": "médio",
        "quality": "muito bom",
    },
}


# ─── Rotas ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def api_status():
    """Retorna status do Ollama e modelos disponíveis com metadados."""
    status = ollama_client.check_ollama_status()

    # Adicionar metadados dos modelos
    models_with_metadata = []
    for model in status.get("models", []):
        model_info = MODEL_SPECS.get(model, {
            "name": model,
            "description": "Modelo sem descrição específica",
            "best_for": ["simple"],
            "speed": "desconhecido",
            "quality": "desconhecido",
        })
        models_with_metadata.append({
            "id": model,
            **model_info
        })

    status["models_metadata"] = models_with_metadata
    return jsonify(status)


@app.route("/api/upload", methods=["POST"])
def upload_pdf():
    """Upload de PDF. Retorna metadados e seções identificadas."""
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files["file"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Envie um arquivo PDF válido"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        meta = pdf_processor.extract_metadata(filepath)
        sections = pdf_processor.extract_sections(filepath)
        images = pdf_processor.extract_images(filepath)

        # Não retornar base64 das imagens no upload (pesado demais)
        image_summary = [
            {"page": img["page"], "index": img["index"],
             "width": img["width"], "height": img["height"]}
            for img in images
        ]

        section_keys = [k for k in sections if k != "full_text"]

        return jsonify({
            "filename": filename,
            "metadata": meta,
            "sections_found": section_keys,
            "image_count": len(images),
            "images": image_summary,
            "text_preview": sections.get("full_text", "")[:500],
        })
    except Exception as e:
        return jsonify({"error": f"Erro ao processar PDF: {e}"}), 500


@app.route("/api/summarize", methods=["POST"])
def summarize():
    """
    Gera resumo do PDF no modo selecionado.
    Body JSON: {filename, mode, model, section (opcional)}
    mode: simple | introduction | methods
    """
    data = request.get_json()
    filename = data.get("filename")
    mode = data.get("mode", "simple")
    model = data.get("model", "llama3.1:8b-instruct-q8_0")  # Modelo padrão atualizado
    section_filter = data.get("section")  # ex: "introduction", "methods"

    if not filename:
        return jsonify({"error": "filename obrigatório"}), 400

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({"error": "Arquivo não encontrado"}), 404

    try:
        if section_filter:
            sections = pdf_processor.extract_sections(filepath)
            text = sections.get(section_filter, "")
            if not text:
                text = sections.get("full_text", "")
        else:
            text = pdf_processor.extract_full_text(filepath)

        # Limitar tamanho do texto para não estourar contexto
        max_chars = 12000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[... texto truncado por limite de contexto ...]"

        system = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["simple"])
        prompt = f"ARTIGO CIENTÍFICO:\n\n{text}\n\n---\nGere o resumo conforme instruído."

        response = ollama_client.generate(
            prompt=prompt,
            model=model,
            system=system,
            temperature=0.3,
        )

        return jsonify({"result": response, "mode": mode, "model": model})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/interpret-graph", methods=["POST"])
def interpret_graph():
    """
    Interpreta gráfico/figura extraído do PDF usando modelo multimodal.
    Body JSON: {filename, image_index, model, context}
    """
    data = request.get_json()
    filename = data.get("filename")
    image_index = data.get("image_index", 0)
    model = data.get("model", "llava:7b")  # Padrão alterado para 7b (recomendado)
    context = data.get("context", "")

    if not filename:
        return jsonify({"error": "filename obrigatório"}), 400

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({"error": "Arquivo não encontrado"}), 404

    try:
        images = pdf_processor.extract_images(filepath)
        if image_index >= len(images):
            return jsonify({"error": f"Índice de imagem {image_index} inválido. Total: {len(images)}"}), 400

        img = images[image_index]
        system = SYSTEM_PROMPTS["graph"]

        prompt = "Analise esta figura/gráfico de um artigo científico."
        if context:
            prompt += f"\n\nContexto adicional do artigo: {context}"

        response = ollama_client.generate_with_image(
            prompt=prompt,
            image_base64=img["base64"],
            model=model,
            temperature=0.3,
        )

        return jsonify({
            "result": response,
            "image_page": img["page"],
            "image_size": f"{img['width']}x{img['height']}",
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/format-references", methods=["POST"])
def format_references():
    """
    Formata referências no estilo da revista (busca por ISSN).
    Body JSON: {issn, references, model, filename (opcional)}
    """
    data = request.get_json()
    issn = data.get("issn", "").strip()
    raw_refs = data.get("references", "").strip()
    model = data.get("model", "llama3.1:8b-instruct-q8_0")  # Modelo padrão atualizado
    filename = data.get("filename")

    if not issn:
        return jsonify({"error": "ISSN obrigatório"}), 400

    try:
        # Se forneceu filename mas não refs, extrair do PDF
        if not raw_refs and filename:
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(filename))
            if os.path.exists(filepath):
                raw_refs = pdf_processor.extract_references_section(filepath) or ""

        if not raw_refs:
            return jsonify({"error": "Forneça as referências ou um PDF com seção de referências"}), 400

        # Buscar info da revista e construir prompt
        journal_info = reference_formatter.lookup_journal_by_issn(issn)
        prompt = reference_formatter.build_reference_prompt(issn, raw_refs)

        response = ollama_client.generate(
            prompt=prompt,
            model=model,
            temperature=0.2,
            max_tokens=4096,
        )

        return jsonify({
            "result": response,
            "journal": journal_info.get("title", ""),
            "publisher": journal_info.get("publisher", ""),
            "issn": issn,
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/journal-info/<issn>", methods=["GET"])
def journal_info(issn):
    """Retorna informações da revista pelo ISSN (via CrossRef)."""
    try:
        info = reference_formatter.lookup_journal_by_issn(issn)
        return jsonify(info)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n╔══════════════════════════════════════════════════╗")
    print("║          ScholarAgent — PDF Analyzer             ║")
    print("║   Agente local para sumarização científica       ║")
    print("╠══════════════════════════════════════════════════╣")
    status = ollama_client.check_ollama_status()
    if status["online"]:
        print(f"║  Ollama: ✓ Online                                ║")
        print(f"║  Modelos: {', '.join(status['models'][:3]):38s}  ║")
    else:
        print("║  Ollama: ✗ Offline — execute 'ollama serve'      ║")
    print("╠══════════════════════════════════════════════════╣")
    print("║  Acesse: http://localhost:5002                   ║")
    print("╚══════════════════════════════════════════════════╝\n")
    app.run(debug=False, host='127.0.0.1', port=5002)
