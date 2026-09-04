#!/usr/bin/env bash
#wrapper for whisper-dictate that runs relative to its own directory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Source .env if present
if [ -f ".env" ]; then
    set -a
    source ".env"
    set +a
fi

if [ -f ".venv/bin/activate" ]; then
    source ".venv/bin/activate"
fi

exec python3 "$SCRIPT_DIR/whisper_dictate.py" "$@"
