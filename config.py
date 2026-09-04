import os
import sys
import argparse
import sounddevice as sd


def load_dotenv(dotenv_path=".env"):
    if not os.path.exists(dotenv_path):
        return
    try:
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.split("#", 1)[0].strip().strip("'\"")
                    if key:
                        os.environ[key] = val
    except Exception:
        pass


load_dotenv()


class Config:
    def __init__(self):
        # Default to small.en for highest accuracy English/Indian English dictation
        self.language = os.environ.get("LANGUAGE", "en")
        default_model = "small.en" if self.language == "en" else "small"
        self.model_name = os.environ.get("WHISPER_MODEL", default_model)
        self.device = os.environ.get("DEVICE", "auto")
        self.compute_type = os.environ.get("COMPUTE_TYPE", "auto")
        
        self.sample_rate = 16000
        self.channels = 1
        self.audio_device = os.environ.get("AUDIO_DEVICE", None)
        self.vad_threshold = float(os.environ.get("VAD_THRESHOLD", "0.35"))
        self.pause_threshold = float(os.environ.get("PAUSE_THRESHOLD_SECONDS", "0.7"))
        self.min_speech_duration = float(os.environ.get("MIN_SPEECH_DURATION", "0.2"))
        self.max_speech_duration = float(os.environ.get("MAX_SPEECH_DURATION", "8.0"))
        self.pre_roll_duration = float(os.environ.get("PRE_ROLL_SECONDS", "0.3"))
        self.post_roll_duration = float(os.environ.get("POST_ROLL_SECONDS", "0.3"))
        
        self.typing_backend = os.environ.get("TYPING_BACKEND", "auto")
        self.typing_delay_ms = int(os.environ.get("TYPING_DELAY_MS", "1"))
        self.typing_method = os.environ.get("TYPING_METHOD", "type")
        
        self.initial_prompt = os.environ.get(
            "INITIAL_PROMPT",
            "Hello, this is standard conversational English, including Indian Diallect, Accent of English terms and natural punctuation."
        )

        self.sound_alerts = os.environ.get("SOUND_ALERTS", "true").lower() in ("true", "1", "yes")
        self.toggle_mode = os.environ.get("TOGGLE_MODE", "true").lower() in ("true", "1", "yes")

    def parse_cli_args(self):
        parser = argparse.ArgumentParser(description="Whisper Dictate")
        parser.add_argument("--model", "-m", type=str, default=None, help=f"Whisper model (default: {self.model_name})")
        parser.add_argument("--language", "-l", type=str, default=None, help=f"Language code: auto, en, hi, etc. (default: {self.language})")
        parser.add_argument("--device", "-d", type=str, default=None, help=f"Device: auto, cuda, cpu (default: {self.device})")
        parser.add_argument("--list-devices", action="store_true", help="List audio input devices")
        parser.add_argument("--no-alerts", action="store_true", help="Disable start/stop sound alerts")
        parser.add_argument("--no-toggle", action="store_true", help="Disable single-instance toggle")

        args = parser.parse_args()

        if args.list_devices:
            print("\n=== Audio Input Devices ===")
            devices = sd.query_devices()
            default_input = sd.default.device[0]
            for idx, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    prefix = " * " if idx == default_input else "   "
                    print(f"{prefix}[{idx}] {dev['name']}")
            print(" * = Default device\n")
            sys.exit(0)

        if args.model:
            self.model_name = args.model
        if args.language:
            self.language = args.language
        if args.device:
            self.device = args.device
        if args.no_alerts:
            self.sound_alerts = False
        if args.no_toggle:
            self.toggle_mode = False

        return self


config = Config()
