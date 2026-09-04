#!/usr/bin/env python3
import os
import sys
import time
import signal
import queue
import threading
import shutil
import subprocess
import atexit
import re
import numpy as np
import sounddevice as sd
from pynput import keyboard
from faster_whisper import WhisperModel

from config import config
from vad import SileroVADProcessor
from injector import get_injector

PID_FILE = "/tmp/whisper_dictate.pid"
stop_flag = False
audio_queue = queue.Queue()


def play_sound(sound_type: str = "start"):
    if not config.sound_alerts:
        return
    sound_files = {
        "start": [
            "/usr/share/sounds/freedesktop/stereo/audio-volume-change.oga",
            "/usr/share/sounds/sound-icons/prompt.wav",
            "/usr/share/sounds/gnome/default/alerts/glass.ogg"
        ],
        "stop": [
            "/usr/share/sounds/freedesktop/stereo/complete.oga",
            "/usr/share/sounds/sound-icons/prompt.wav",
            "/usr/share/sounds/gnome/default/alerts/drip.ogg"
        ]
    }
    player = shutil.which("paplay") or shutil.which("pw-play") or shutil.which("aplay")
    if player:
        for path in sound_files.get(sound_type, []):
            if os.path.exists(path):
                try:
                    subprocess.Popen([player, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
                except Exception:
                    pass
    print("\a", end="", flush=True)


def check_single_instance():
    if not config.toggle_mode:
        return

    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)
            print(f"Whisper Dictate is already running (PID {old_pid}). Stopping it...")
            os.kill(old_pid, signal.SIGINT)
            sys.exit(0)
        except (ValueError, OSError):
            try:
                os.remove(PID_FILE)
            except OSError:
                pass

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    def cleanup_pid():
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except OSError:
                pass

    atexit.register(cleanup_pid)


def audio_callback(indata, frames, time_info, status):
    if status:
        print(f"Audio status: {status}", file=sys.stderr)
    audio_queue.put(indata[:, 0].copy())


def on_press(key):
    global stop_flag
    try:
        if key == keyboard.Key.esc:
            print("\nStop requested (ESC).")
            stop_flag = True
            return False
    except Exception:
        pass


def handle_signal(sig, frame):
    global stop_flag
    print("\nStop requested (signal).")
    stop_flag = True


def is_valid_speech(text: str) -> bool:
    clean = text.strip()
    if not clean:
        return False
    if re.fullmatch(r'[\s\.\,\!\?\:\;\-\_\~\*]+', clean):
        return False
    if len(set(clean.replace(' ', ''))) <= 1 and len(clean) > 1:
        return False
    if not any(c.isalnum() for c in clean):
        return False
    return True


def format_text_continuation(text: str, prev_text: str, is_english: bool = True) -> str:
    """Ensures smooth capitalization and removes unintended non-English tokens."""
    # Strip any CJK/foreign glyphs when English is configured
    if is_english:
        text = re.sub(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+', '', text)

    text = text.strip()
    if not text:
        return ""

    if prev_text:
        last_char = prev_text.rstrip()[-1] if prev_text.rstrip() else ""
        if last_char not in (".", "!", "?", "\n"):
            if text[0].isupper() and not text.startswith(("I ", "I'", "I’")):
                text = text[0].lower() + text[1:]
    return text


def main():
    global stop_flag

    config.parse_cli_args()
    check_single_instance()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Auto detect device
    import torch
    has_cuda = torch.cuda.is_available()
    device = ("cuda" if has_cuda else "cpu") if config.device == "auto" else config.device
    compute_type = ("float16" if device == "cuda" else "int8") if config.compute_type == "auto" else config.compute_type

    print(f"Loading Whisper model '{config.model_name}' on {device} ({compute_type})...")
    try:
        model = WhisperModel(config.model_name, device=device, compute_type=compute_type)
    except Exception as e:
        print(f"Error loading model: {e}", file=sys.stderr)
        if device == "cuda":
            print("Falling back to CPU (int8)...")
            model = WhisperModel(config.model_name, device="cpu", compute_type="int8")
        else:
            sys.exit(1)

    vad = SileroVADProcessor(
        threshold=config.vad_threshold,
        pause_threshold_sec=config.pause_threshold,
        min_speech_sec=config.min_speech_duration,
        max_speech_sec=config.max_speech_duration,
        pre_roll_sec=config.pre_roll_duration,
        post_roll_sec=config.post_roll_duration,
        sample_rate=config.sample_rate
    )

    injector = get_injector(
        backend=config.typing_backend,
        delay_ms=config.typing_delay_ms,
        method=config.typing_method
    )

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    prompt_context = config.initial_prompt
    last_typed_text = ""
    is_english = config.language == "en" or config.model_name.endswith(".en")

    def transcribe_and_type(audio_segment: np.ndarray):
        nonlocal prompt_context, last_typed_text
        if len(audio_segment) == 0:
            return

        try:
            # If using an .en specific model, don't pass language parameter
            lang = None if (config.model_name.endswith(".en") or config.language == "auto") else config.language
            segments, info = model.transcribe(
                audio_segment,
                language=lang,
                initial_prompt=prompt_context,
                condition_on_previous_text=False,
                temperature=0.0,
                beam_size=1,
                repetition_penalty=1.1,
                no_repeat_ngram_size=3,
                compression_ratio_threshold=2.4,
                no_speech_threshold=0.6,
                log_prob_threshold=-1.0,
                vad_filter=False
            )

            valid_texts = []
            for s in segments:
                if s.compression_ratio > 2.4 or s.no_speech_prob > 0.6 or s.avg_logprob < -1.0:
                    continue
                clean = s.text.strip()
                if is_valid_speech(clean):
                    valid_texts.append(clean)

            if valid_texts:
                raw_text = " ".join(valid_texts)
                formatted_text = format_text_continuation(raw_text, last_typed_text, is_english=is_english)
                if formatted_text:
                    print("->", formatted_text)
                    injector.type_text(formatted_text)
                    last_typed_text = formatted_text

                    words = [w for w in formatted_text.split() if any(c.isalnum() for c in w)]
                    if words:
                        prompt_context = " ".join(words[-15:])
        except Exception as err:
            print(f"Transcription error: {err}", file=sys.stderr)

    def worker_loop():
        while not stop_flag or not audio_queue.empty():
            try:
                chunk = audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            segments = vad.process_chunk(chunk)
            for seg in segments:
                transcribe_and_type(seg)

        # Flush any speech left in buffer on stop
        flushed = vad.flush()
        for seg in flushed:
            transcribe_and_type(seg)

    worker_thread = threading.Thread(target=worker_loop, daemon=True)
    worker_thread.start()

    play_sound("start")
    print("Ready to dictate. Speak into any text field. Press ESC to stop.\n")

    try:
        input_device = int(config.audio_device) if config.audio_device is not None and config.audio_device.isdigit() else None
        with sd.InputStream(
            samplerate=config.sample_rate,
            channels=config.channels,
            dtype="float32",
            device=input_device,
            callback=audio_callback
        ):
            while not stop_flag:
                time.sleep(0.05)
    except KeyboardInterrupt:
        stop_flag = True
    except Exception as e:
        print(f"Audio error: {e}", file=sys.stderr)
        stop_flag = True

    print("Stopping dictation...")
    worker_thread.join(timeout=3.0)
    play_sound("stop")
    print("Exited.")


if __name__ == "__main__":
    main()