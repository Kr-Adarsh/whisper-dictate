# Whisper Dictate (Linux)

Offline, fast, simple, system-wide speech-to-text for Linux using Faster-Whisper and Silero VAD.

Press a shortcut, speak, and the text is typed directly into whatever text field you are focused on.
Runs fully locally on your machine. No cloud, no API keys, no telemetry.

[![Demo GIF](whisper_demo.GIF)](https://www.youtube.com/watch?v=5lCzA79Nh_I?si=n5zIrvNtfmzjpADw)

---

## Features

- Offline speech-to-text (runs fully locally)
- Works in any app / text box
- Silero VAD: cuts audio on natural pauses (no more cut-off words)
- Fast in-memory transcription (faster-whisper int8 CPU / cuda GPU)
- Zero word loss on exit (flushes remaining speech when you stop)
- Single-shortcut toggle (press once to start, press again or ESC to stop)
- Works great with Indian dialect / conversational English
- Simple global keyboard shortcut
- Privacy-friendly

---

## Requirements

- Linux (tested on Ubuntu, should work on most distros)
- Python 3.9+
- Microphone
- Optional: NVIDIA GPU with drivers for faster transcription (CPU is already fast with INT8)

---

## Project Structure

```text
.
├── config.py            # Simple config parser (.env & flags)
├── vad.py               # Silero VAD pause detection
├── injector.py          # xdotool / clipboard text typing
├── whisper_dictate.py   # Main dictation logic
├── whisper_dictate.sh   # Launcher script (point your shortcut here)
├── .env                 # Optional custom settings
├── change_log.md        # What changed
├── install.sh           # Cross-distro installer
├── requirements.txt     # Python dependencies
└── README.md            # Documentation
```

---

## Installation

Clone the repository and run the installer:

```bash
git clone https://github.com/Kr-Adarsh/whisper-dictate.git
cd whisper-dictate
chmod +x install.sh whisper_dictate.sh
./install.sh
```

### Installer options:
```bash 
./install.sh          # CPU install (default, fast int8)
./install.sh --cuda   # CUDA-enabled PyTorch (for NVIDIA GPU)
./install.sh --help   # Show help
```

---

## Run Dictation (Manual Test)

```bash
cd whisper-dictate
./whisper_dictate.sh
```

Usage:
- Click inside any text field
- Start speaking
- When you pause, text gets typed
- Press ESC (or trigger the shortcut again) to stop

---

## Set Global Keyboard Shortcut (GNOME)

1. Open Settings → Keyboard → Shortcuts
2. Add a Custom Shortcut (like mine's `ctrl+super+G` or `ctrl+G`)

```text
Name:
    Whisper Dictation

Command:
    /home/yourusername/path/to/whisper-dictate/whisper_dictate.sh

Shortcut:
    Ctrl + Alt + G
```

After this:
- Press shortcut to start dictating (you'll hear a start beep)
- Press the shortcut again (or press ESC) to stop and finish typing

---

## Configuration (Optional)

You can tweak settings in `.env` or pass CLI flags:

```bash
# Model options: tiny, base, small, medium
WHISPER_MODEL=base

# Language (en, auto, etc.)
LANGUAGE=en

# Pause in seconds to trigger typing
PAUSE_THRESHOLD_SECONDS=0.65

# Sound alerts on start/stop
SOUND_ALERTS=true
```

Or run with flags:
```bash
./whisper_dictate.sh --list-devices     # List your mics
./whisper_dictate.sh --model small      # Use a specific model
./whisper_dictate.sh --language auto    # Auto-detect language
```

---

## Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **No text is typed** | 1. Ensure a text field is focused (cursor is active).<br>2. Test `xdotool` manually:<br>`xdotool type "hello"` |
| **Microphone not detected** | 1. Run `./whisper_dictate.sh --list-devices`<br>2. Check sound settings in Linux. |
| **GPU not being used** | 1. Ensure NVIDIA drivers are installed (`nvidia-smi`).<br>2. Re-run `./install.sh --cuda`. |
| **Still having Issues?** | c'mon dude, you're linux user. (^^) |

---
## Dev Notes:

*Long time ago, i only knew basics and thus built a simpler pretty direct version of `Whisper` but as i explored and learned more and more vad, stt, tts, etc.. i kept on upgrading this appn locally for my own use.. and honestly had forgotten to push for a long time ;p Anyways, here's `whisper-dictatev2`, it's quite fast, stable and works great (atleast for me), also i've resolved all the previous bugs and cache issues and have made a few more changes before pushing, to make it a lil more generic for others sys. That's it, all the controllers are in .env, feel free to edit em and use it how you'd like.. peace.*

*~Kr-Adarsh*