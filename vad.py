import os
import urllib.request
import torch
import numpy as np


class SileroVADProcessor:
    def __init__(self,
                 threshold: float = 0.35,
                 pause_threshold_sec: float = 0.7,
                 min_speech_sec: float = 0.2,
                 max_speech_sec: float = 8.0,
                 pre_roll_sec: float = 0.3,
                 post_roll_sec: float = 0.3,
                 sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.pause_samples = int(pause_threshold_sec * sample_rate)
        self.min_speech_samples = int(min_speech_sec * sample_rate)
        self.max_speech_samples = int(max_speech_sec * sample_rate)
        self.pre_roll_samples = int(pre_roll_sec * sample_rate)
        self.frame_size = 512
        self.post_roll_frames = int((post_roll_sec * sample_rate) / self.frame_size)
        self.min_consecutive_speech_frames = 2

        self.model = self._load_model()
        self.reset()

    def _load_model(self):
        cache_dir = os.path.expanduser("~/.cache/whisper-dictate")
        os.makedirs(cache_dir, exist_ok=True)
        vad_file = os.path.join(cache_dir, "silero_vad.jit")

        if not os.path.exists(vad_file):
            print("Downloading Silero VAD model...")
            url = "https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.jit"
            urllib.request.urlretrieve(url, vad_file)

        model = torch.jit.load(vad_file)
        model.eval()
        return model

    def reset(self):
        if hasattr(self.model, "reset_states"):
            self.model.reset_states()
        self.pre_roll_buffer = []
        self.pre_roll_len = 0
        self.speech_buffer = []
        self.speech_len = 0
        self.is_speech_active = False
        self.silence_samples_count = 0
        self.consecutive_speech_frames = 0
        self.actual_speech_samples = 0
        self.incoming_buffer = np.array([], dtype=np.float32)

    def _trim_and_build_segment(self):
        if not self.speech_buffer or self.actual_speech_samples < self.min_speech_samples:
            return None

        # trim excess dead silence, keep full post-roll margin
        num_silence_frames = self.silence_samples_count // self.frame_size
        frames_to_cut = max(0, num_silence_frames - self.post_roll_frames)
        usable_frames = self.speech_buffer[:-frames_to_cut] if frames_to_cut > 0 else self.speech_buffer

        if not usable_frames:
            return None

        segment = np.concatenate(usable_frames)
        rms = np.sqrt(np.mean(segment**2))
        if len(segment) >= self.min_speech_samples and rms > 0.0015:
            return segment
        return None

    def process_chunk(self, audio_chunk: np.ndarray):
        segments = []
        self.incoming_buffer = np.append(self.incoming_buffer, audio_chunk)

        while len(self.incoming_buffer) >= self.frame_size:
            frame = self.incoming_buffer[:self.frame_size]
            self.incoming_buffer = self.incoming_buffer[self.frame_size:]

            tensor_frame = torch.from_numpy(frame).unsqueeze(0)
            with torch.no_grad():
                prob = self.model(tensor_frame, self.sample_rate).item()

            is_speech = prob >= self.threshold

            if not self.is_speech_active:
                # collect pre roll buffer so initial consonants are never lost
                self.pre_roll_buffer.append(frame)
                self.pre_roll_len += self.frame_size
                while self.pre_roll_len > self.pre_roll_samples:
                    popped = self.pre_roll_buffer.pop(0)
                    self.pre_roll_len -= len(popped)

                if is_speech:
                    self.consecutive_speech_frames += 1
                    if self.consecutive_speech_frames >= self.min_consecutive_speech_frames:
                        self.is_speech_active = True
                        self.speech_buffer = list(self.pre_roll_buffer)
                        self.speech_len = sum(len(f) for f in self.speech_buffer)
                        self.actual_speech_samples = self.consecutive_speech_frames * self.frame_size
                        self.silence_samples_count = 0
                else:
                    self.consecutive_speech_frames = 0
            else:
                self.speech_buffer.append(frame)
                self.speech_len += self.frame_size

                if is_speech:
                    self.actual_speech_samples += self.frame_size
                    self.silence_samples_count = 0
                else:
                    self.silence_samples_count += self.frame_size

                # If natural pause occurs (~0.7s), emit full grammatical phrase
                if self.silence_samples_count >= self.pause_samples:
                    seg = self._trim_and_build_segment()
                    if seg is not None:
                        segments.append(seg)
                    self.speech_buffer = []
                    self.speech_len = 0
                    self.is_speech_active = False
                    self.silence_samples_count = 0
                    self.consecutive_speech_frames = 0
                    self.actual_speech_samples = 0
                    self.pre_roll_buffer = []
                    self.pre_roll_len = 0
                    if hasattr(self.model, "reset_states"):
                        self.model.reset_states()

                # If continuous talking reaches max duration, split cleanly
                elif self.speech_len >= self.max_speech_samples:
                    seg = self._trim_and_build_segment()
                    if seg is not None:
                        segments.append(seg)
                    self.speech_buffer = []
                    self.speech_len = 0
                    self.silence_samples_count = 0
                    self.actual_speech_samples = 0

        return segments

    def flush(self):
        #flusing remaining speech on stop
        if self.is_speech_active:
            seg = self._trim_and_build_segment()
            self.speech_buffer = []
            self.speech_len = 0
            self.is_speech_active = False
            self.consecutive_speech_frames = 0
            self.actual_speech_samples = 0
            if seg is not None:
                return [seg]
        return []
