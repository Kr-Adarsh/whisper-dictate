#!/usr/bin/env python3
"""
Simple chunked dictation script using OpenAI Whisper.
- Records short chunks from microphone
- Appends to a buffer and transcribes each chunk
- Types result into the currently focused text input via xdotool
- Press ESC to stop (global key captured with pynput)

Notes:
- This implementation writes temporary WAV files for each chunk to feed Whisper (stable and simple)
- First run: downloads the model (may take a few minutes depending on your internet)
"""

import os
import tempfile
import queue
import threading
import subprocess
import sys
import time
import torch
import numpy as np
import sounddevice as sd
import soundfile as sf
from pynput import keyboard

import whisper

# Config
MODEL_NAME = os.environ.get("WHISPER_MODEL", "small")  # change to tiny/small/medium if desired
CHUNK_SECONDS = 4.5  # length of each audio chunk (seconds)
SAMPLE_RATE = 16000
CHANNELS = 1

stop_flag = False

q = queue.Queue()

print("Loading Whisper model (this can take a while)...")

device = "cuda" if torch.cuda.is_available() else "cpu"
model = whisper.load_model(MODEL_NAME, device=device) # auto change
print(f"Model '{MODEL_NAME}' loaded. Ready to dictate. Press ESC to stop.")


def on_press(key):
    global stop_flag
    try:
        if key == keyboard.Key.esc:
            print("Stop requested (ESC).")
            stop_flag = True
            return False
    except Exception:
        pass


# Audio callback — put raw frames into queue

def callback(indata, frames, time_info, status):
    if status:
        print(f"Audio status: {status}")
    q.put(indata.copy())


# Typing helper

def type_text(text: str):
    if not text:
        return
    # Replace newlines with spaces so xdotool types a clean stream
    text = text.replace('\n', ' ')
    subprocess.run(["xdotool", "type", "--delay", "1", text])


# Transcription worker — takes queued frames and when enough seconds accumulated, writes a temp wav and transcribes

def transcriber_worker():
    buffer = []
    frames_needed = int(CHUNK_SECONDS * SAMPLE_RATE)
    samples_collected = 0

    while not stop_flag:
        try:
            frames = q.get(timeout=0.5)
        except queue.Empty:
            continue

        # frames shape: (n_frames, channels)
        buffer.append(frames)
        samples_collected += frames.shape[0]

        # If enough samples gathered, transcribe
        if samples_collected >= frames_needed:
            data = np.concatenate(buffer, axis=0)
            # ensure single channel
            if data.ndim > 1:
                data = data.mean(axis=1)

            # normalize to float32
            data = data.astype('float32')

            # write to temp wav
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                fname = f.name
            sf.write(fname, data, SAMPLE_RATE, format='WAV')

            try:
                print("Transcribing chunk...")
                result = model.transcribe(fname, language='en')
                text = result.get('text', '').strip()
                print("->", text)
                if text:
                    type_text(text + ' ')
            except Exception as e:
                print('Transcription error:', e)
            finally:
                try:
                    os.remove(fname)
                except OSError:
                    pass

            # reset
            buffer = []
            samples_collected = 0


def main():
    global stop_flag

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    # Start transcriber thread
    t = threading.Thread(target=transcriber_worker, daemon=True)
    t.start()

    print("Starting microphone stream — speak now.")

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=callback):
            while not stop_flag:
                time.sleep(0.1)
    except KeyboardInterrupt:
        stop_flag = True

    print("Stopping — waiting for worker to finish...")
    t.join(timeout=2.0)
    print("Exited.")


if __name__ == '__main__':
    main()
