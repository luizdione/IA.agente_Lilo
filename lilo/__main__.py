"""Entry point: `python -m lilo` (e o script `lilo` do pyproject)."""

import sys


def main() -> int:
    try:
        from lilo.cli import main as cli_main  # F2+: REPL/one-shot reais
    except ImportError:
        from lilo import __version__
        print("LILO v%s — nucleo em reconstrucao (fase F1: cliente Ollama)."
              % __version__)
        print("Acompanhe: docs/versoes/CHANGELOG.md e CONTEXT.md.")
        return 0
    return cli_main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
