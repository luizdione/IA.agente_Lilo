#!/usr/bin/env bash
# install.sh -- bootstrap do instalador do LILO (Linux / macOS).
# Uso:  bash install.sh   (ou:  chmod +x install.sh && ./install.sh)
# Encontra o Python e delega para install.py (o instalador real, multiplataforma).
set -e

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Python 3.10+ nao encontrado. Instale python3 pelo gerenciador do seu sistema."
  exit 1
fi

echo "Usando $PY..."
exec "$PY" "$here/install.py" "$@"
