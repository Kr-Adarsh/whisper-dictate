import os
import shutil
import subprocess


class BaseInjector:
    def type_text(self, text: str):
        raise NotImplementedError


class X11Injector(BaseInjector):
    def __init__(self, delay_ms: int = 1, method: str = "type"):
        self.delay_ms = delay_ms
        self.method = method
        self.has_xdotool = shutil.which("xdotool") is not None
        self.has_xclip = shutil.which("xclip") is not None

        if not self.has_xdotool:
            print("Warning: xdotool not found.")

    def type_text(self, text: str):
        if not text:
            return

        clean_text = text.replace("\r", "").replace("\n", " ").strip()
        if not clean_text:
            return
        clean_text = clean_text + " "

        if self.method == "paste" and self.has_xclip and self.has_xdotool:
            self._paste_text(clean_text)
        elif self.has_xdotool:
            subprocess.run([
                "xdotool", "type",
                "--clearmodifiers",
                "--delay", str(self.delay_ms),
                "--",
                clean_text
            ])
        else:
            print(f"[xdotool missing]: {clean_text}")

    def _paste_text(self, text: str):
        try:
            proc = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
            proc.communicate(input=text.encode("utf-8"))
            subprocess.run(["xdotool", "key", "--clearmodifiers", "ctrl+v"])
        except Exception as e:
            print(f"Paste error: {e}")


class WaylandInjector(BaseInjector):
    def __init__(self, delay_ms: int = 1):
        self.delay_ms = delay_ms
        self.has_wtype = shutil.which("wtype") is not None
        self.has_ydotool = shutil.which("ydotool") is not None
        self.has_xdotool = shutil.which("xdotool") is not None

    def type_text(self, text: str):
        if not text:
            return

        clean_text = text.replace("\r", "").replace("\n", " ").strip() + " "

        if self.has_wtype:
            subprocess.run(["wtype", "-d", str(self.delay_ms), clean_text])
        elif self.has_ydotool:
            subprocess.run(["ydotool", "type", "-d", str(self.delay_ms), clean_text])
        elif self.has_xdotool:
            subprocess.run(["xdotool", "type", "--clearmodifiers", "--delay", str(self.delay_ms), "--", clean_text])
        else:
            print(f"[No typing tool found]: {clean_text}")


def get_injector(backend: str = "auto", delay_ms: int = 1, method: str = "type") -> BaseInjector:
    if backend == "xdotool":
        return X11Injector(delay_ms=delay_ms, method=method)
    elif backend in ("ydotool", "wtype"):
        return WaylandInjector(delay_ms=delay_ms)

    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    wayland_display = os.environ.get("WAYLAND_DISPLAY", "")

    if "wayland" in session_type or wayland_display:
        return WaylandInjector(delay_ms=delay_ms)
    return X11Injector(delay_ms=delay_ms, method=method)
