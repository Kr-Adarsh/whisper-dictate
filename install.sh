#!/usr/bin/env bash
set -euo pipefail

# Robust cross-distro installer for Whisper Dictate
# - installs system deps using detected package manager
# - creates .venv and installs python deps
# - tries to install CUDA-enabled torch if NVIDIA GPU found, else cpu torch
# - installs remaining requirements from requirements.txt

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Project dir: $PROJECT_DIR"

# quick python3 check
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but not found. Please install Python 3 and retry."
  exit 1
fi

# basic internet check (best-effort)
if ! curl -s --head https://pypi.org/ --max-time 6 >/dev/null 2>&1; then
  echo "Warning: cannot reach pypi.org. Make sure you have internet access for installation."
fi

# detect package manager
PKGMGR=""
if command -v apt >/dev/null 2>&1; then
    PKGMGR="apt"
elif command -v dnf >/dev/null 2>&1; then
    PKGMGR="dnf"
elif command -v pacman >/dev/null 2>&1; then
    PKGMGR="pacman"
elif command -v zypper >/dev/null 2>&1; then
    PKGMGR="zypper"
else
    echo "Unsupported distro: please install python3, python3-venv, ffmpeg, xdotool, libsndfile, portaudio (system packages) manually."
    exit 1
fi

echo "Using package manager: $PKGMGR"

# install system dependencies
case "$PKGMGR" in
  apt)
    sudo apt update
    sudo apt install -y python3 python3-venv python3-pip ffmpeg xdotool build-essential libsndfile1 portaudio19-dev libportaudio2 curl
    ;;
  dnf)
    sudo dnf install -y python3 python3-venv python3-pip ffmpeg xdotool make automake gcc gcc-c++ libsndfile portaudio-devel curl
    ;;
  pacman)
    sudo pacman -Sy --noconfirm python python-virtualenv ffmpeg xdotool base-devel libsndfile portaudio curl
    ;;
  zypper)
    sudo zypper install -y python3 python3-venv python3-pip ffmpeg xdotool libsndfile1 libportaudio0 curl
    ;;
esac

# create venv if missing
cd "$PROJECT_DIR"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# activate venv
# shellcheck disable=SC1091
source "$PROJECT_DIR/.venv/bin/activate"

# pip basics
python -m pip install --upgrade pip setuptools wheel

echo "Detecting NVIDIA GPU (nvidia-smi)..."
USE_CUDA=false
if command -v nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi found. Trying to install CUDA-enabled PyTorch wheel..."
  USE_CUDA=true
fi

# prepare temp file for pip output and ensure cleanup
TMPFILE="$(mktemp /tmp/torch_install.XXXXXX)"
cleanup() {
  rm -f "$TMPFILE" || true
}
trap cleanup EXIT

# Install torch: prefer GPU wheel if possible, otherwise CPU wheel
if [ "$USE_CUDA" = true ]; then
  set +e
  echo "Attempting to install torch (GPU wheel) using cu121 index..."
  pip install --upgrade "torch" --index-url https://download.pytorch.org/whl/cu121 >"$TMPFILE" 2>&1 || true
  RC=$?
  set -e
  if [ $RC -ne 0 ]; then
    echo "GPU wheel install failed (falling back to CPU-only torch). Last output:"
    tail -n 200 "$TMPFILE" || true
    pip install --upgrade "torch" --index-url https://download.pytorch.org/whl/cpu
  else
    echo "Installed torch (CUDA-enabled) from cu121 index."
  fi
else
  echo "No NVIDIA GPU detected. Installing CPU-only torch wheel."
  pip install --upgrade "torch" --index-url https://download.pytorch.org/whl/cpu
fi

# Install remaining python requirements
if [ -f "requirements.txt" ]; then
  pip install -r requirements.txt
else
  echo "requirements.txt missing in $PROJECT_DIR. Please make sure it's present."
fi

echo
echo "#! Setup complete."
echo "To start dictation (once):"
echo "  cd \"$PROJECT_DIR\" && source .venv/bin/activate && ./whisper_dictate.sh"
echo
echo "To make a global shortcut, point it at \"$PROJECT_DIR/whisper_dictate.sh\""
echo "Enjoy!"
