"""
LILO Agent - Agente de IA alternativo via LiteLLM Gateway
Suporte local gratuito usando modelos Ollama (llama3, codellama)

Uso:
    python agents/lilo_agent.py                     # Chat interativo
    python agents/lilo_agent.py --model codellama   # Modelo especifico
    python agents/lilo_agent.py --mode code         # Modo codigo
    python agents/lilo_agent.py --mode bioinfo      # Modo bioinformatica
"""

import argparse
import json
import sys
import os
import requests
from pathlib import Path

# === Configuracao ===
LITELLM_URL = os.getenv("LITELLM_PROXY_URL", "http://localhost:4000")
OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
API_KEY = os.getenv("LITELLM_API_KEY", "sk-litellm-local-dev")

SYSTEM_PROMPTS = {
    "chat": (
        "Voce e o LILO, um assistente de IA inteligente e prestativo. "
        "Responda de forma clara, concisa e pratica. "
        "Quando o usuario falar em portugues, responda em portugues. "
        "Quando falar em ingles, responda em ingles."
    ),
    "code": (
        "Voce e o LILO Code, um assistente especializado em programacao. "
        "Foque em: codigo limpo, boas praticas, performance e seguranca. "
        "Sempre forneca exemplos de codigo quando apropriado. "
        "Explique suas sugestoes de forma didatica."
    ),
    "bioinfo": (
        "Voce e o LILO Bio, um assistente especializado em bioinformatica "
        "e ciencia de dados biologicos. Voce domina: genomica, proteomics, "
        "analise de sequencias, pipelines NGS, R/Bioconductor, Python/Biopython, "
        "estatistica biologica e visualizacao de dados. "
        "Forneca solucoes praticas e cientificamente fundamentadas."
    ),
    "sql": (
        "Voce e o LILO SQL, um assistente especializado em bancos de dados "
        "e consultas SQL. Voce domina: PostgreSQL, MySQL, SQLite, "
        "otimizacao de queries, modelagem de dados e ETL. "
        "Sempre forneca queries otimizadas e explique o plano de execucao."
    ),
}

MODEL_DEFAULTS = {
    "chat": "llama3",
    "code": "codellama",
    "bioinfo": "llama3",
    "sql": "codellama",
}


def check_health() -> dict:
    """Verifica saude do LiteLLM proxy e Ollama."""
    status = {"litellm": False, "ollama": False, "models": []}

    try:
        r = requests.get(f"{LITELLM_URL}/health", timeout=3)
        status["litellm"] = r.status_code == 200
    except requests.ConnectionError:
        pass

    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        if r.status_code == 200:
            status["ollama"] = True
            data = r.json()
            status["models"] = [m["name"] for m in data.get("models", [])]
    except requests.ConnectionError:
        pass

    return status


def chat_completion(messages: list, model: str, stream: bool = True) -> str:
    """Envia mensagens para o LiteLLM proxy e retorna a resposta."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    payload = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    try:
        if stream:
            response = requests.post(
                f"{LITELLM_URL}/v1/chat/completions",
                headers=headers,
                json=payload,
                stream=True,
                timeout=120,
            )
            response.raise_for_status()

            full_response = ""
            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                print(content, end="", flush=True)
                                full_response += content
                        except json.JSONDecodeError:
                            continue
            print()  # newline ao final
            return full_response
        else:
            response = requests.post(
                f"{LITELLM_URL}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            print(content)
            return content

    except requests.ConnectionError:
        print("\n[ERRO] Nao foi possivel conectar ao LiteLLM proxy.")
        print(f"       Verifique se o proxy esta rodando em {LITELLM_URL}")
        print("       Execute: .\\lilo.ps1  ou  start.bat")
        return ""
    except requests.HTTPError as e:
        print(f"\n[ERRO] HTTP {e.response.status_code}: {e.response.text}")
        return ""


def fallback_ollama(messages: list, model: str) -> str:
    """Fallback direto para Ollama se LiteLLM nao estiver disponivel."""
    print("[INFO] Usando Ollama diretamente (LiteLLM indisponivel)...")

    # Extrair modelo base (sem prefixo ollama/)
    base_model = model.replace("ollama/", "")

    payload = {
        "model": base_model,
        "messages": messages,
        "stream": True,
    }

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
            stream=True,
            timeout=120,
        )
        response.raise_for_status()

        full_response = ""
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        print(content, end="", flush=True)
                        full_response += content
                except json.JSONDecodeError:
                    continue
        print()
        return full_response

    except Exception as e:
        print(f"\n[ERRO] Fallback Ollama falhou: {e}")
        return ""


def interactive_chat(model: str, mode: str):
    """Loop de chat interativo."""
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["chat"])
    messages = [{"role": "system", "content": system_prompt}]

    # Header
    print("=" * 60)
    print(f"  LILO Agent - Modo: {mode.upper()} | Modelo: {model}")
    print(f"  Gateway: {LITELLM_URL}")
    print("=" * 60)
    print("  Comandos: /clear /mode /model /health /quit")
    print("=" * 60)
    print()

    # Health check inicial
    status = check_health()
    use_fallback = False

    if status["litellm"]:
        print(f"[OK] LiteLLM proxy conectado")
    elif status["ollama"]:
        print(f"[WARN] LiteLLM indisponivel, usando Ollama direto")
        use_fallback = True
    else:
        print("[ERRO] Nenhum backend disponivel!")
        print("       Inicie o Ollama: ollama serve")
        print("       Inicie o LiteLLM: .\\lilo.ps1")
        return

    if status["models"]:
        print(f"[OK] Modelos disponiveis: {', '.join(status['models'])}")
    print()

    while True:
        try:
            user_input = input("voce> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[LILO] Ate mais! 👋")
            break

        if not user_input:
            continue

        # Comandos especiais
        if user_input.startswith("/"):
            cmd = user_input.lower().split()[0]

            if cmd in ("/quit", "/exit", "/q"):
                print("[LILO] Ate mais! 👋")
                break

            elif cmd == "/clear":
                messages = [{"role": "system", "content": system_prompt}]
                print("[LILO] Historico limpo.\n")
                continue

            elif cmd == "/mode":
                parts = user_input.split()
                if len(parts) > 1 and parts[1] in SYSTEM_PROMPTS:
                    mode = parts[1]
                    model = MODEL_DEFAULTS.get(mode, model)
                    system_prompt = SYSTEM_PROMPTS[mode]
                    messages = [{"role": "system", "content": system_prompt}]
                    print(f"[LILO] Modo alterado para: {mode.upper()} (modelo: {model})\n")
                else:
                    modes = ", ".join(SYSTEM_PROMPTS.keys())
                    print(f"[LILO] Modos disponiveis: {modes}\n")
                continue

            elif cmd == "/model":
                parts = user_input.split()
                if len(parts) > 1:
                    model = parts[1]
                    print(f"[LILO] Modelo alterado para: {model}\n")
                else:
                    print(f"[LILO] Modelo atual: {model}")
                    print(f"       Disponiveis: llama3, codellama, claude\n")
                continue

            elif cmd == "/health":
                s = check_health()
                print(f"  LiteLLM: {'OK' if s['litellm'] else 'OFFLINE'}")
                print(f"  Ollama:  {'OK' if s['ollama'] else 'OFFLINE'}")
                print(f"  Modelos: {', '.join(s['models']) or 'nenhum'}\n")
                continue

            else:
                print(f"[LILO] Comando desconhecido: {cmd}\n")
                continue

        # Enviar mensagem
        messages.append({"role": "user", "content": user_input})
        print("\nlilo> ", end="", flush=True)

        if use_fallback:
            response = fallback_ollama(messages, model)
        else:
            response = chat_completion(messages, model, stream=True)

        if response:
            messages.append({"role": "assistant", "content": response})
        print()


def main():
    parser = argparse.ArgumentParser(description="LILO Agent - LLM Gateway CLI")
    parser.add_argument(
        "--model", type=str, default=None,
        help="Modelo a usar (llama3, codellama, claude)"
    )
    parser.add_argument(
        "--mode", type=str, default="chat",
        choices=["chat", "code", "bioinfo", "sql"],
        help="Modo do agente (chat, code, bioinfo, sql)"
    )
    parser.add_argument(
        "--health", action="store_true",
        help="Verificar saude dos servicos"
    )
    parser.add_argument(
        "--no-stream", action="store_true",
        help="Desabilitar streaming"
    )

    args = parser.parse_args()

    if args.health:
        status = check_health()
        print(f"LiteLLM Proxy: {'OK' if status['litellm'] else 'OFFLINE'}")
        print(f"Ollama:        {'OK' if status['ollama'] else 'OFFLINE'}")
        print(f"Modelos:       {', '.join(status['models']) or 'nenhum'}")
        sys.exit(0 if status["ollama"] else 1)

    model = args.model or MODEL_DEFAULTS.get(args.mode, "llama3")
    interactive_chat(model, args.mode)


if __name__ == "__main__":
    main()
