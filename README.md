# Whisper Dictate (Linux)

Offline, simple, system-wide speech-to-text for Linux using OpenAI Whisper.

Press a shortcut, speak, and the text is typed directly into the currently focused text field.
Runs fully locally. No cloud, no API keys, no telemetry.

[![Demo GIF](whisper_demo.GIF)](https://www.youtube.com/watch?v=5lCzA79Nh_I?si=n5zIrvNtfmzjpADw)
---

## Features

- Offline speech-to-text (after first model download)
- Works in any app / text box
- Uses CPU by default, optional GPU (CUDA) acceleration
- No background service when idle
- Simple global keyboard shortcut
- Privacy-friendly

---

## Requirements

- Linux (tested on Ubuntu, should work on most distros)
- Python 3.9+
- Microphone
- Optional: NVIDIA GPU with drivers for faster transcription

---

## Project Structure

```text
.
├── install.sh           # Cross-distro installer (GPU-aware)
├── LICENSE              # MIT License
├── README.md            # Documentation
├── requirements.txt     # Python dependencies
├── whisper_dictate.py   # Main dictation logic
└── whisper_dictate.sh   # Execution wrapper (Point your shortcut here)
```


## Installation

Clone the repository and run the installer:

```bash
git clone https://github.com/Kr-Adarsh/whisper-dictate.git
cd whisper-dictate
chmod +x install.sh
./install.sh (ref below)
```
## Installer options:
```bash 
./install.sh          # CPU-only install (default)
./install.sh --cuda   # CUDA-enabled PyTorch (large)
./install.sh --help   # Show help

```


The installer will:
- Install system dependencies
- Create a local Python virtual environment
- Install Whisper and required Python packages
- Install CPU or CUDA-enabled PyTorch based on your choice

---


## Run Dictation (Manual Test)
```python
cd whisper-dictate
source .venv/bin/activate
./whisper_dictate.sh
# Press ESC to stop dictation
```

Usage:
- Click inside any text field
- Start speaking
- Press ESC to stop dictation

When stopped, the process exits and releases CPU/GPU resources.

---

## Set Global Keyboard Shortcut (GNOME)

1. Open Settings → Keyboard → Shortcuts
2. Add a Custom Shortcut (like mine's "ctrl+super+G")

```text
Name:
    Whisper Dictation

Command:
    /home/yourusername/path/to/whisper-dictate/whisper_dictate.sh

Shortcut:
    Ctrl + Alt + G
```

After this:
- Press the shortcut to start dictation
- Press ESC to stop

---

## GPU Acceleration

If an NVIDIA GPU and drivers are available, Whisper will use CUDA automatically.

To verify GPU usage:

    nvidia-smi

If CUDA is not available, Whisper falls back to CPU automatically.
No manual configuration is required.

---

## Configuration (Optional)

Change the Whisper model in whisper_dictate.py:

    WHISPER_MODEL=base

Available models:
- tiny   (fastest, least accurate)
- base   (default, balanced)
- small (ref the openai/whisper repo)
- medium

```python
silence_threshold = 0.002 # Adjust this to make it more or less sensitive to silence (lower = more sensitive). You can see it in the terminal output your current mic sensitivity and adjust accordingly.
```
##### Other parameters can also be tweaked in the script via whisper_dictate.py.
---

## Project Files

- install.sh            Cross-distro installer (GPU-aware)
- whisper_dictate.sh    Launcher script (used by keyboard shortcut)
- whisper_dictate.py    Main dictation logic
- requirements.txt      Python dependencies

---

## Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **No text is typed** | 1. Ensure a text field is focused (cursor is active).<br>2. Test `xdotool` manually:<br>`xdotool type "hello"` |
| **Microphone not detected** | 1. Check input device in system sound settings.<br>2. Verify detection with:<br>`arecord -l` |
| **GPU not being used** | 1. Ensure NVIDIA drivers are installed.<br>2. Check `nvidia-smi`.<br>3. Re-run `install.sh` to retry CUDA setup. |
| **Still having Issues?** | c'mon dude, you're linux user. (^^) |
---

## License

MIT License
