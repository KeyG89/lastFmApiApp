#!/usr/bin/env bash
set -euo pipefail

echo "Project diagnostics"
echo "pwd: $(pwd)"

PYTHON_BIN="python3"
if [ -x .venv/bin/python ]; then
  PYTHON_BIN=".venv/bin/python"
fi

if [ -d .git ]; then
  echo "git: ok"
else
  echo "git: missing"
  exit 1
fi

if [ -f .env ]; then
  echo ".env: present"
else
  echo ".env: absent (ok if no local secrets are needed)"
fi

if [ -f Diagnostics/project_doctor.py ]; then
  "$PYTHON_BIN" Diagnostics/project_doctor.py .
fi

if [ -f Diagnostics/integration_doctor.py ]; then
  "$PYTHON_BIN" Diagnostics/integration_doctor.py .
fi

PYTHONPATH=src "$PYTHON_BIN" Diagnostics/lastfm_doctor.py
PYTHONPATH=src "$PYTHON_BIN" Diagnostics/shazam_doctor.py
PYTHONPATH=src "$PYTHON_BIN" -m pytest -q
