#!/usr/bin/env bash
set -euo pipefail

# Whisper Dictate installer (final)
# - cross-distro system deps install
# - creates .venv and installs python deps
# - installs CPU torch by default, use --cuda to install CUDA-enabled torch
# - installs remaining requirements from requirements.txt

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<EOF
Usage:
  ./install.sh          Install CPU-only (default)
  ./install.sh --cuda   Install CUDA-enabled PyTorch (large download)
  ./install.sh --help   Show this message
EOF
}

# parse args
USE_CUDA=false
if [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi
if [ "${1:-}" = "--cuda" ] || [ "${1:-}" = "-cuda" ]; then
  USE_CUDA=true
fi
if [ "${1:-}" = "--cpu" ]; then
  USE_CUDA=false
fi

echo "Project dir: $PROJECT_DIR"
echo

# quick python3 check
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but not found. Please install Python 3 and retry."
  exit 1
fi

# basic internet check (best-effort)
if ! command -v curl >/dev/null 2>&1 || ! curl -s --head https://pypi.org/ --max-time 6 >/dev/null 2>&1; then
  echo "Warning: cannot reach pypi.org or curl missing. Internet is required for installation."
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
echo

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

# spinner helper (shows activity while background process runs)
spinner() {
  local pid=$1
  local delay=0.15
  local spinstr='|/-\'
  printf " "
  while ps -p "$pid" > /dev/null 2>&1; do
    for i in 0 1 2 3; do
      printf "\b%c" "${spinstr:$i:1}"
      sleep "$delay"
    done
  done
  printf "\b"
}

# prepare temp file for pip output and ensure cleanup
TMPFILE="$(mktemp /tmp/whisper_torch_install.XXXXXX)"
cleanup() {
  rm -f "$TMPFILE" || true
}
trap cleanup EXIT

# Notify user about torch choice
if [ "$USE_CUDA" = true ]; then
  echo "CUDA install selected."
  echo "This will download large PyTorch CUDA binaries (~500MB-1.5GB). Make sure you have a working NVIDIA driver (nvidia-smi)."
else
  echo "CPU-only install selected (default). This is smaller and works on all machines."
fi
echo

# Install torch: run pip install in background and show spinner/progress indicator
install_torch_bg() {
  local cmd="$1"
  # run pip in background, redirect both stdout and stderr to TMPFILE
  bash -c "$cmd" >"$TMPFILE" 2>&1 &
  local pip_pid=$!
  spinner "$pip_pid"
  wait "$pip_pid"
  return $?
}

if [ "$USE_CUDA" = true ]; then
  # Try CUDA wheel (cu121). If it fails, fall back to CPU wheel.
  echo "Installing CUDA-enabled PyTorch (cu121 index)..."
  install_torch_bg "pip install --upgrade torch --index-url https://download.pytorch.org/whl/cu121" || true
  RC=$?
  if [ $RC -ne 0 ]; then
    echo
    echo "CUDA wheel install failed or was interrupted. Falling back to CPU-only torch. See last logs:"
    tail -n 200 "$TMPFILE" || true
    echo
    echo "Installing CPU-only PyTorch..."
    install_torch_bg "pip install --upgrade torch --index-url https://download.pytorch.org/whl/cpu"
    RC=$?
    if [ $RC -ne 0 ]; then
      echo
      echo "Failed to install torch (CPU wheel) as well. See logs in $TMPFILE"
      exit 1
    fi
  fi
  echo
  echo "PyTorch installation complete."
else
  echo "Installing CPU-only PyTorch..."
  install_torch_bg "pip install --upgrade torch --index-url https://download.pytorch.org/whl/cpu"
  RC=$?
  if [ $RC -ne 0 ]; then
    echo
    echo "Failed to install CPU PyTorch. See logs in $TMPFILE"
    tail -n 200 "$TMPFILE" || true
    exit 1
  fi
  echo
  echo "PyTorch installation complete."
fi

# Install remaining python requirements (if present)
if [ -f "requirements.txt" ]; then
  echo "Installing remaining Python requirements from requirements.txt ..."
  pip install -r requirements.txt
else
  echo "requirements.txt missing in $PROJECT_DIR. Please make sure it's present."
fi

echo
echo "Setup complete."
echo "To start dictation (manual test):"
echo "  cd \"$PROJECT_DIR\" && source .venv/bin/activate && ./whisper_dictate.sh"
echo
echo "To make a global shortcut, point it at: $PROJECT_DIR/whisper_dictate.sh"
echo "Enjoy!"