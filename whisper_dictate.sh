#!/usr/bin/env bash
# robust wrapper that runs relative to its own location

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# activate venv if exists
if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
fi

# optional env overrides:
# export WHISPER_MODEL=base

python "$SCRIPT_DIR/whisper_dictate.py"
