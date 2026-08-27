"""
bridge_main — the unified 32-bit Tech-Note bridge.

One process serves both halves of the 32-bit story: the SAPI TTS backend
and `bits: 32` synth plugins (which cannot load their DLLs in the 64-bit
app). It listens on a localhost TCP socket and answers newline-delimited
JSON. Compiled with PyInstaller into a single 32-bit executable
(`TechNoteBridge32.exe`); also runnable directly under a 32-bit Python:

    python32 bridge_main.py tts [port]
    python32 bridge_main.py plugin <plugin.scrugn> [port]

Protocol (shared by both modes):

    {"cmd": "ping"}
    {"cmd": "speak", "text": "...", "interrupt": true}
    {"cmd": "stop"}
    {"cmd": "rate", "value": 5}   / {"cmd": "get_rate"}
    {"cmd": "volume", "value": 80} / {"cmd": "get_volume"}
    {"cmd": "pitch", "value": 50}  / {"cmd": "get_pitch"}
    {"cmd": "voice", "name": "..."} / {"cmd": "voices"} / {"cmd": "get_voice"}
    {"cmd": "call", "method": "get_voice_names", "args": [], "kwargs": {}}
    {"cmd": "shutdown"}

On startup it prints `LISTENING <port>` to stdout so the 64-bit side can
connect. `tts` mode uses pywin32 SAPI when available, falling back to
32-bit PowerShell's System.Speech. `plugin` mode loads a `.scrugn` synth
plugin (same manifest rules as core/plugin_manager) and proxies its
SynthPlugin methods via the generic `call` verb.
"""

import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import zipfile

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ------------------------------------------------------------------ backends

class _Win32Voice:
    """SAPI via pywin32 — requires the 32-bit Python to have pywin32."""

    def __init__(self):
        import win32com.client
        self._voice = win32com.client.Dispatch("SAPI.SpVoice")
        self._rate = self._voice.Rate
        self._volume = self._voice.Volume
        self._voice_name = ""
        try:
            self._voice_name = self._voice.Voice.GetDescription()
        except Exception:
            pass

    def available(self):
        return True

    def speak(self, text):
        # Flag 1 = SVSFlagsAsync: start speaking and return immediately.
        # This lets stop() interrupt a long utterance without waiting for
        # it to finish — the old synchronous call (flag 0) blocked until
        # the utterance completed, making cancel() ineffective.
        self._voice.Speak(text, 1)

    def cancel(self):
        try:
            # Flag 2 = SVSFPurgeBeforeSpeak: purge the queue and speak
            # an empty string, which stops any in-progress utterance.
            self._voice.Speak("", 2)
        except Exception:
            pass

    def set_rate(self, value):
        try:
            self._rate = int(value)
            self._voice.Rate = self._rate
        except Exception:
            pass

    def get_rate(self):
        return self._rate

    def set_volume(self, value):
        try:
            self._volume = max(0, min(100, int(value)))
            self._voice.Volume = self._volume
        except Exception:
            pass

    def get_volume(self):
        return self._volume

    def set_pitch(self, value):
        pass  # SAPI5 has no pitch control

    def get_pitch(self):
        return 50

    def set_voice(self, name):
        try:
            for v in self._voice.GetVoices():
                if v.GetDescription() == name:
                    self._voice.Voice = v
                    self._voice_name = name
                    break
        except Exception:
            pass

    def get_voice_names(self):
        try:
            return [v.GetDescription() for v in self._voice.GetVoices()]
        except Exception:
            return []

    def get_voice_name(self):
        return self._voice_name

    def shutdown(self):
        self.cancel()


_PS_EXE = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                       "SysWOW64", "WindowsPowerShell", "v1.0", "powershell.exe")


def _ps_escape(text):
    return text.replace("'", "''")


class _PSVoice:
    """System.Speech via the 32-bit PowerShell — no Python deps needed."""

    def __init__(self):
        self._rate = 0
        self._volume = 100
        self._pitch = 50
        self._voice_name = ""

    def _ps(self, script):
        if not os.path.exists(_PS_EXE):
            return ""
        try:
            proc = subprocess.run(
                [_PS_EXE, "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, text=True, timeout=120,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return proc.stdout
        except Exception:
            return ""

    def available(self):
        return os.path.exists(_PS_EXE)

    def speak(self, text):
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Rate={int(self._rate)}; $s.Volume={int(self._volume)}; "
        )
        if self._voice_name:
            script += f"$s.SelectVoice('{_ps_escape(self._voice_name)}'); "
        script += f"$s.Speak('{_ps_escape(text)}')"
        self._ps(script)

    def cancel(self):
        pass  # speak() runs synchronously in the worker thread

    def set_rate(self, value):
        self._rate = max(-10, min(10, int(value)))

    def get_rate(self):
        return self._rate

    def set_volume(self, value):
        self._volume = max(0, min(100, int(value)))

    def get_volume(self):
        return self._volume

    def set_pitch(self, value):
        self._pitch = max(0, min(100, int(value)))

    def get_pitch(self):
        return self._pitch

    def set_voice(self, name):
        names = self.get_voice_names()
        if name in names:
            self._voice_name = name

    def get_voice_names(self):
        out = self._ps(
            "Add-Type -AssemblyName System.Speech; "
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }"
        )
        return [ln.strip() for ln in out.splitlines() if ln.strip()]

    def get_voice_name(self):
        return self._voice_name

    def shutdown(self):
        pass


class _VoiceAdapter:
    """Wraps a voice backend in the SynthPlugin-shaped surface the unified
    dispatch speaks, so one server handles both SAPI and plugins."""

    def __init__(self, voice):
        self._v = voice

    def speak(self, text, interrupt=True):
        if interrupt:
            self._v.cancel()
        self._v.speak(text)

    def stop(self):
        self._v.cancel()

    def get_rate(self):
        return self._v.get_rate()

    def set_rate(self, value):
        self._v.set_rate(value)

    def get_volume(self):
        return self._v.get_volume()

    def set_volume(self, value):
        self._v.set_volume(value)

    def get_pitch(self):
        return self._v.get_pitch()

    def set_pitch(self, value):
        self._v.set_pitch(value)

    def get_voice_names(self):
        return self._v.get_voice_names()

    def set_voice(self, name):
        self._v.set_voice(name)

    def get_voice_name(self):
        return self._v.get_voice_name()

    def shutdown(self):
        try:
            self._v.shutdown()
        except Exception:
            pass


def make_voice_backend():
    try:
        v = _Win32Voice()
        if v.available():
            return _VoiceAdapter(v)
    except Exception:
        pass
    v = _PSVoice()
    if v.available():
        return _VoiceAdapter(v)
    return None


# ---------------------------------------------------------------- plugins

def load_plugin(path):
    """Extract a .scrugn, instantiate its SynthPlugin, return the instance."""
    if not os.path.exists(path):
        raise RuntimeError(f"plugin not found: {path}")
    tmp = tempfile.mkdtemp(prefix="scrugn_bridge_")
    with zipfile.ZipFile(path, "r") as z:
        names = z.namelist()
        manifest = json.loads(z.read("manifest.json"))
        entry = manifest.get("entry", "__init__.py")
        if entry not in names:
            raise RuntimeError(f"plugin entry {entry} missing")
        z.extractall(tmp)
    sys.path.insert(0, APP_ROOT)
    sys.path.insert(0, tmp)
    spec = importlib.util.spec_from_file_location(
        "scrugn_bridge_plugin", os.path.join(tmp, entry))
    if not spec or not spec.loader:
        raise RuntimeError("could not build module spec")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from core.plugin_base import SynthPlugin
    for attr_name in dir(mod):
        attr = getattr(mod, attr_name)
        if (isinstance(attr, type) and issubclass(attr, SynthPlugin)
                and attr is not SynthPlugin):
            instance = attr()
            instance.initialize()
            return instance
    raise RuntimeError("no SynthPlugin subclass found in plugin")


# ------------------------------------------------------------------ server

class BridgeServer:
    def __init__(self, backend, port=0):
        self.backend = backend
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", port))
        self._sock.listen(1)
        self._port = self._sock.getsockname()[1]
        self._write_lock = threading.Lock()
        self._speak_lock = threading.Lock()  # one utterance at a time
        self._stop = False

    def run(self):
        print(f"LISTENING {self._port}", flush=True)
        while not self._stop:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                break
            threading.Thread(target=self._handle, args=(conn,),
                             daemon=True).start()

    def _handle(self, conn):
        with conn:
            f = conn.makefile("rw", encoding="utf-8", errors="replace")
            while not self._stop:
                line = f.readline()
                if not line:
                    break
                try:
                    msg = json.loads(line)
                except Exception:
                    continue
                reply = self._dispatch(msg)
                if reply is None:
                    break  # shutdown
                with self._write_lock:
                    try:
                        f.write(json.dumps(reply) + "\n")
                        f.flush()
                    except Exception:
                        break
        try:
            conn.close()
        except Exception:
            pass

    def _dispatch(self, msg):
        cmd = msg.get("cmd")
        if cmd == "ping":
            return {"ok": True}
        if cmd == "shutdown":
            self._stop = True
            try:
                self.backend.shutdown()
            except Exception:
                pass
            return {"ok": True}  # ack so the client's read completes cleanly
        if cmd == "speak":
            with self._speak_lock:
                try:
                    self.backend.speak(msg.get("text", ""),
                                       msg.get("interrupt", True))
                except Exception as e:
                    return {"ok": False,
                            "error": f"{type(e).__name__}: {e}"}
            return {"ok": True}
        if cmd == "stop":
            with self._speak_lock:
                try:
                    self.backend.stop()
                except Exception as e:
                    return {"ok": False, "error": f"{type(e).__name__}: {e}"}
            return {"ok": True}
        if cmd == "call":
            method = msg.get("method")
            args = msg.get("args") or []
            kwargs = msg.get("kwargs") or {}
            fn = getattr(self.backend, method, None)
            if fn is None or not callable(fn):
                return {"ok": False, "error": f"no such method: {method}"}
            try:
                result = fn(*args, **kwargs)
            except Exception as e:
                return {"ok": False, "error": f"{type(e).__name__}: {e}"}
            return {"ok": True, "result": result}
        # Convenience verbs (voice-style) shared by both backends.
        if cmd == "rate":
            return self._call_result("set_rate", msg.get("value", 0))
        if cmd == "get_rate":
            return self._call_result("get_rate")
        if cmd == "volume":
            return self._call_result("set_volume", msg.get("value", 100))
        if cmd == "get_volume":
            return self._call_result("get_volume")
        if cmd == "pitch":
            return self._call_result("set_pitch", msg.get("value", 50))
        if cmd == "get_pitch":
            return self._call_result("get_pitch")
        if cmd == "voice":
            return self._call_result("set_voice", msg.get("name", ""))
        if cmd == "voices":
            return self._call_result("get_voice_names")
        if cmd == "get_voice":
            return self._call_result("get_voice_name")
        return {"ok": False, "error": f"unknown command: {cmd}"}

    def _call_result(self, method, *args):
        try:
            result = getattr(self.backend, method)(*args)
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}
        return {"ok": True, "result": result}


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: bridge_main.py <tts|plugin <plugin.scrugn>> [port]",
              file=sys.stderr, flush=True)
        return 1
    mode = args[0]
    port = 0
    if mode == "tts":
        backend = make_voice_backend()
        if backend is None:
            print("ERROR no usable TTS backend (need pywin32 or 32-bit PowerShell)",
                  file=sys.stderr, flush=True)
            return 1
        if len(args) > 1:
            port = _to_port(args[1])
    elif mode == "plugin":
        if len(args) < 2:
            print("ERROR plugin mode needs a .scrugn path",
                  file=sys.stderr, flush=True)
            return 1
        try:
            backend = load_plugin(args[1])
        except Exception as e:
            print(f"ERROR loading plugin: {type(e).__name__}: {e}",
                  file=sys.stderr, flush=True)
            return 1
        if len(args) > 2:
            port = _to_port(args[2])
    else:
        print(f"ERROR unknown mode: {mode}", file=sys.stderr, flush=True)
        return 1
    server = BridgeServer(backend, port=port)
    server.run()
    return 0


def _to_port(value):
    try:
        return int(value)
    except ValueError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
