# Changelog

## 2.0.0

- **Faster-Whisper**: Replaced vanilla openai-whisper with faster-whisper (CTranslate2, int8 on CPU, float16 on GPU). Now transcribes directly from memory with no temporary `.wav` files on disk.
- **Silero VAD**: Added Silero VAD to detect natural speech pauses (`PAUSE_THRESHOLD_SECONDS=0.65`) instead of fixed 4.5s hard slicing. Words are no longer cut in half.
- **Flush on Exit**: Added a flush routine so whatever you were saying right before pressing ESC (or stopping) gets transcribed and typed instead of being dropped.
- **Single-Shortcut Toggle**: You can now map one shortcut to start dictation and press the same shortcut again to stop.
- **Config & .env**: Added `config.py` that parses `.env` / env vars / CLI flags with default fallback to system settings.
- **Indian Dialect & Context Support**: Prompt priming for natural conversational English, punctuation, and dialect vocabulary.
- **X11 Text Injection**: Cleaner typing with `xdotool --clearmodifiers` (plus optional clipboard paste mode) and auto-detection for Wayland.
- **Audio Feedback**: Subtle start/stop chime.
