"""
Health Check - Verifica status de todos os servicos do LLM Gateway.
Util para diagnostico rapido e integracao com VS Code tasks.
"""

import json
import sys
import requests


def check_all():
    results = {}

    # 1. Ollama
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        results["ollama"] = {"status": "ok", "models": models}
    except Exception as e:
        results["ollama"] = {"status": "offline", "error": str(e)}

    # 2. LiteLLM Proxy
    try:
        r = requests.get("http://localhost:4000/health", timeout=3)
        results["litellm"] = {"status": "ok" if r.status_code == 200 else "error"}
    except Exception as e:
        results["litellm"] = {"status": "offline", "error": str(e)}

    # 3. LiteLLM Models
    try:
        r = requests.get(
            "http://localhost:4000/models",
            headers={"Authorization": "Bearer sk-litellm-local-dev"},
            timeout=3,
        )
        if r.status_code == 200:
            data = r.json()
            model_ids = [m["id"] for m in data.get("data", [])]
            results["litellm_models"] = {"status": "ok", "models": model_ids}
        else:
            results["litellm_models"] = {"status": "error", "code": r.status_code}
    except Exception as e:
        results["litellm_models"] = {"status": "offline", "error": str(e)}

    return results


def main():
    results = check_all()
    all_ok = all(v["status"] == "ok" for v in results.values())

    print(json.dumps(results, indent=2, ensure_ascii=False))
    print()

    if all_ok:
        print("✅ Todos os servicos estao funcionando!")
    else:
        print("⚠️  Alguns servicos estao com problemas.")
        if results["ollama"]["status"] != "ok":
            print("   → Inicie o Ollama: ollama serve")
        if results["litellm"]["status"] != "ok":
            print("   → Inicie o LiteLLM: .\\lilo.ps1")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
