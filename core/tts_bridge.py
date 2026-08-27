"""
core/tts_bridge — the 64-bit half of the TTS bridge.

`BridgeTTS` is a full synth implementation (same shape as SapiSynthBase)
that launches the unified 32-bit bridge — `bridge/TechNoteBridge32.exe`
when present, otherwise `bridge/bridge_main.py` under a 32-bit Python —
in `tts` mode and talks to it over a localhost socket using
newline-delimited JSON. This lets 32-bit-only TTS engines (older SAPI
voices, Dectalk, Eloquence...) run inside the 64-bit Tech-Note process.

The launch command comes from `core.bridge_launcher` and the helper is
respawned automatically if it dies.
"""

import json
import os
import socket
import subprocess
import threading
import time

from core.bridge_launcher import bridge_command

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Reuse SAPI5's punctuation / capital-pitch handling so the bridge sounds
# the same as the native path.
from synths.sapi_synth import SapiSynthBase as _SapiBase


class BridgeTTS:
    def __init__(self, python_path=None, script_path=None):
        # Explicit overrides (tests / development) launch a specific
        # interpreter + script; otherwise the unified launcher picks the
        # compiled TechNoteBridge32.exe (or the 32-bit Python fallback).
        if python_path is not None or script_path is not None:
            from synths.registry import _find_32bit_python
            self._cmd = [python_path or _find_32bit_python(),
                         script_path or os.path.join(BASE_DIR, "bridge",
                                                     "bridge_main.py")]
        else:
            self._cmd = bridge_command("tts")
        self._proc = None
        self._sock = None
        self._lock = threading.RLock()     # reentrant: _ensure_connected is
                                           # also called while the lock is held
        self._speak_lock = threading.Lock()  # one utterance thread at a time
        self._pending = None               # current speak thread
        self._rate = 0
        self._volume = 100
        self._pitch = 50
        self._voice_index = 0
        self._voice_names = []
        self._punctuation_level = "Some"
        self._capital_pitch_change = "Off"
        self._speech_history = []
        self._history_max = 50
        self._temp = {}
        self._saved = {}
        self._ducking = False
        self._ensure_connected()

    # ------------------------------------------------------------ lifecycle

    def _ensure_connected(self):
        with self._lock:
            if self._sock is not None:
                return True
            if not self._cmd:
                return False
            try:
                self._proc = subprocess.Popen(
                    self._cmd,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                line = self._proc.stdout.readline().strip()
                if not line.startswith("LISTENING"):
                    return False
                port = int(line.split()[1])
                self._sock = socket.create_connection(("127.0.0.1", port),
                                                      timeout=5)
                self._sock.settimeout(10)
                return True
            except Exception:
                self._teardown_locked()
                return False

    def _teardown_locked(self):
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        if self._proc:
            try:
                self._proc.kill()
            except Exception:
                pass
            self._proc = None

    def is_bridge_alive(self):
        return self._sock is not None

    def _request(self, msg, timeout=10):
        """Send one command and wait for its reply. Reconnects once if the
        helper has died. Returns the reply dict or None on failure."""
        payload = json.dumps(msg) + "\n"
        for attempt in (0, 1):
            with self._lock:
                if self._sock is None and not self._ensure_connected():
                    return None
                sock = self._sock
            try:
                sock.settimeout(timeout)
                sock.sendall(payload.encode("utf-8"))
                line = sock.makefile("r", encoding="utf-8", errors="replace").readline()
                if not line:
                    raise OSError("empty reply")
                return json.loads(line)
            except Exception:
                with self._lock:
                    self._teardown_locked()
                if attempt == 1:
                    return None
        return None

    def close(self):
        try:
            self._request({"cmd": "shutdown"}, timeout=2)
        except Exception:
            pass
        with self._lock:
            self._teardown_locked()

    # -------------------------------------------------------------- speaking

    def speak(self, text, interrupt=True):
        if not text:
            return
        # Mirror the native SAPI path: punctuation and capital-pitch rules.
        if self._punctuation_level and self._punctuation_level != "None":
            text = _SapiBase._filter_punctuation(text, self._punctuation_level)
        if self._capital_pitch_change == "On":
            text = _SapiBase._apply_capital_pitch(text)
        self._record_history(text)
        if interrupt:
            self.stop()
        # Apply per-app temp params (rate/pitch) for this utterance.
        if self._temp.get("rate") is not None:
            self.set_rate(self._temp["rate"])
        if self._temp.get("pitch") is not None:
            self.set_pitch(self._temp["pitch"])
        if self._temp.get("voice_index") is not None:
            try:
                self.set_voice_by_index(self._temp["voice_index"])
            except Exception:
                pass
        t = threading.Thread(target=self._do_speak, args=(text,), daemon=True)
        with self._speak_lock:
            self._pending = t
        t.start()

    def _do_speak(self, text):
        try:
            self._request({"cmd": "speak", "text": text, "interrupt": True},
                          timeout=600)
        finally:
            with self._speak_lock:
                self._pending = None

    def stop(self):
        try:
            self._request({"cmd": "stop"}, timeout=5)
        except Exception:
            pass

    def wait_until_done(self, timeout_ms=5000):
        end = time.time() + timeout_ms / 1000.0
        while time.time() < end:
            with self._speak_lock:
                if self._pending is None:
                    return True
            time.sleep(0.05)
        return False

    # ---------------------------------------------------------------- params

    def get_rate(self):
        return self._temp.get("rate", self._rate)

    def set_rate(self, value):
        self._rate = int(value)
        self._request({"cmd": "rate", "value": self._rate})

    def get_volume(self):
        return self._volume

    def set_volume(self, value):
        self._volume = max(0, min(100, int(value)))
        self._request({"cmd": "volume", "value": self._volume})

    def get_pitch(self):
        return self._temp.get("pitch", self._pitch)

    def set_pitch(self, value):
        self._pitch = max(0, min(100, int(value)))
        self._request({"cmd": "pitch", "value": self._pitch})

    def get_voice_names(self):
        if not self._voice_names:
            reply = self._request({"cmd": "voices"})
            if reply and reply.get("ok"):
                self._voice_names = reply.get("voices", []) or []
        return list(self._voice_names)

    def get_current_voice_name(self):
        names = self.get_voice_names()
        if 0 <= self._voice_index < len(names):
            return names[self._voice_index]
        return ""

    def set_voice(self, name):
        names = self.get_voice_names()
        if name in names:
            self._voice_index = names.index(name)
            self._request({"cmd": "voice", "name": name})

    def set_voice_by_index(self, index):
        names = self.get_voice_names()
        if 0 <= index < len(names):
            self._voice_index = index
            self._request({"cmd": "voice", "name": names[index]})

    def get_voice_index(self):
        return self._voice_index

    def set_punctuation_level(self, level):
        self._punctuation_level = level

    def get_punctuation_level(self):
        return self._punctuation_level

    def set_capital_pitch_change(self, value):
        self._capital_pitch_change = value

    def get_capital_pitch_change(self):
        return self._capital_pitch_change

    def set_volume_ducking(self, enabled):
        self._ducking = bool(enabled)

    def get_volume_ducking(self):
        return self._ducking

    # -------------------------------------------------------------- profiles

    def save_defaults(self):
        pass  # the bridge holds no persisted engine state

    def apply_profile(self, voice_index=None, rate=None, pitch=None):
        if voice_index is not None:
            self.set_voice_by_index(voice_index)
        if rate is not None:
            self.set_rate(rate)
        if pitch is not None:
            self.set_pitch(pitch)

    def set_temp_params(self, rate=None, pitch=None, voice_index=None):
        if not self._temp:
            self._saved = {"rate": self._rate, "pitch": self._pitch,
                           "voice_index": self._voice_index}
        if rate is not None:
            self._temp["rate"] = rate
        if pitch is not None:
            self._temp["pitch"] = pitch
        if voice_index is not None:
            self._temp["voice_index"] = voice_index

    def reset_temp_params(self):
        self._temp = {}
        if self._saved:
            self.set_rate(self._saved.get("rate", 0))
            self.set_pitch(self._saved.get("pitch", 50))
            try:
                self.set_voice_by_index(self._saved.get("voice_index", 0))
            except Exception:
                pass
            self._saved = {}

    # --------------------------------------------------------------- history

    def _record_history(self, text):
        self._speech_history.append(text)
        if len(self._speech_history) > self._history_max:
            self._speech_history = self._speech_history[-self._history_max:]

    def get_speech_history(self):
        return list(self._speech_history)

    def get_history_max(self):
        return self._history_max

    def set_history_max(self, value):
        self._history_max = max(10, min(200, int(value)))
        if len(self._speech_history) > self._history_max:
            self._speech_history = self._speech_history[-self._history_max:]

    def repeat_last(self):
        if self._speech_history:
            self.speak(self._speech_history[-1])
