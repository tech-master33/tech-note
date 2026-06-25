import ctypes
import ctypes.wintypes
from pathlib import Path

from core.plugin_base import SynthPlugin

UINT = ctypes.wintypes.UINT
DWORD = ctypes.wintypes.DWORD
LPDWORD = ctypes.POINTER(DWORD)
LONG = ctypes.wintypes.LONG
LPVOID = ctypes.wintypes.LPVOID
LPSTR = ctypes.wintypes.LPSTR
BOOL = ctypes.wintypes.BOOL
MMRESULT = ctypes.c_long

MMSYSERR_NOERROR = 0
VOLUME_MAIN = 1
TTS_NORMAL = 0
TTS_FORCE = 1

DTCALLBACK = ctypes.CFUNCTYPE(None, LONG, LONG, DWORD, UINT)

VOICES = {
    "Paul": 0, "Betty": 1, "Harry": 2, "Frank": 3,
    "Dennis": 4, "Kit": 5, "Ursula": 6, "Rita": 7, "Wendy": 8,
}


def _load_dectalk():
    dll_path = Path(__file__).parent / "bin" / "DECtalk.dll"
    if not dll_path.exists():
        raise RuntimeError(f"DECtalk.dll not found at {dll_path}")
    dll = ctypes.WinDLL(str(dll_path))

    dll.TextToSpeechStartupExFonix.argtypes = [
        ctypes.POINTER(LPVOID), UINT, DWORD, DTCALLBACK, LONG, LPSTR,
    ]
    dll.TextToSpeechStartupExFonix.restype = MMRESULT
    dll.TextToSpeechShutdown.argtypes = [LPVOID]
    dll.TextToSpeechShutdown.restype = MMRESULT
    dll.TextToSpeechSpeak.argtypes = [LPVOID, LPSTR, DWORD]
    dll.TextToSpeechSpeak.restype = MMRESULT
    dll.TextToSpeechReset.argtypes = [LPVOID, BOOL]
    dll.TextToSpeechReset.restype = MMRESULT
    dll.TextToSpeechSync.argtypes = [LPVOID]
    dll.TextToSpeechSync.restype = MMRESULT
    dll.TextToSpeechGetRate.argtypes = [LPVOID, LPDWORD]
    dll.TextToSpeechGetRate.restype = MMRESULT
    dll.TextToSpeechSetRate.argtypes = [LPVOID, DWORD]
    dll.TextToSpeechSetRate.restype = MMRESULT
    dll.TextToSpeechGetVolume.argtypes = [LPVOID, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    dll.TextToSpeechGetVolume.restype = MMRESULT
    dll.TextToSpeechSetVolume.argtypes = [LPVOID, ctypes.c_int, ctypes.c_int]
    dll.TextToSpeechSetVolume.restype = MMRESULT
    dll.TextToSpeechGetSpeaker.argtypes = [LPVOID, LPDWORD]
    dll.TextToSpeechGetSpeaker.restype = MMRESULT
    dll.TextToSpeechSetSpeaker.argtypes = [LPVOID, DWORD]
    dll.TextToSpeechSetSpeaker.restype = MMRESULT

    return dll


_dummy_cb = DTCALLBACK(lambda l1, l2, d, u: None)


class DectalkSynth(SynthPlugin):
    plugin_name = "DECtalk Synthesizer"
    plugin_version = "4.64.0"

    def initialize(self):
        self._dll = _load_dectalk()
        self._handle = LPVOID()
        dic_path = Path(__file__).parent / "bin" / "dtalk_us.dic"
        dic_arg = LPSTR(str(dic_path).encode("utf-8")) if dic_path.exists() else LPSTR()
        mmr = self._dll.TextToSpeechStartupExFonix(
            ctypes.byref(self._handle),
            UINT(0), DWORD(0), _dummy_cb, LONG(0), dic_arg,
        )
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"Dectalk startup failed: error {mmr}")
        self._history_max = 50
        return True

    def shutdown(self):
        if hasattr(self, "_handle") and self._handle:
            try:
                self._dll.TextToSpeechShutdown(self._handle)
            except Exception:
                pass
            self._handle = None

    def speak(self, text, interrupt=True):
        if interrupt:
            self.stop()
        encoded = (text + "\0").encode("ascii", errors="replace")
        buf = ctypes.create_string_buffer(encoded)
        self._dll.TextToSpeechSpeak(self._handle, buf, DWORD(TTS_FORCE))
        if not hasattr(self, '_speech_history'):
            self._speech_history = []
        self._speech_history.append(text)
        if len(self._speech_history) > self._history_max:
            self._speech_history.pop(0)

    def stop(self):
        self._dll.TextToSpeechReset(self._handle, BOOL(True))

    def get_rate(self):
        val = DWORD()
        self._dll.TextToSpeechGetRate(self._handle, ctypes.byref(val))
        return val.value

    def set_rate(self, value):
        self._dll.TextToSpeechSetRate(self._handle, DWORD(int(value)))

    def get_volume(self):
        val = ctypes.c_int()
        self._dll.TextToSpeechGetVolume(
            self._handle, ctypes.c_int(VOLUME_MAIN), ctypes.byref(val)
        )
        return val.value

    def set_volume(self, value):
        self._dll.TextToSpeechSetVolume(
            self._handle, ctypes.c_int(VOLUME_MAIN), ctypes.c_int(int(value))
        )

    def get_pitch(self):
        return 50

    def set_pitch(self, value):
        pass

    def get_voice_names(self):
        return list(VOICES.keys())

    def get_current_voice_name(self):
        val = DWORD()
        self._dll.TextToSpeechGetSpeaker(self._handle, ctypes.byref(val))
        for name, sid in VOICES.items():
            if sid == val.value:
                return name
        return ""

    def set_voice(self, name):
        sid = VOICES.get(name)
        if sid is not None:
            self._dll.TextToSpeechSetSpeaker(self._handle, DWORD(sid))

    def get_voice_index(self):
        cur = self.get_current_voice_name()
        names = self.get_voice_names()
        return names.index(cur) if cur in names else 0

    def set_voice_by_index(self, index):
        names = self.get_voice_names()
        if 0 <= index < len(names):
            self.set_voice(names[index])

    def save_defaults(self):
        self._default_rate = self.get_rate()
        self._default_volume = self.get_volume()
        self._default_pitch = self.get_pitch()
        self._default_voice_index = self.get_voice_index()
        if not hasattr(self, '_history_max'):
            self._history_max = 50
        self._speech_history = []

    def reset_temp_params(self):
        if hasattr(self, '_default_voice_index'):
            self.set_voice_by_index(self._default_voice_index)
        if hasattr(self, '_default_rate'):
            self.set_rate(self._default_rate)
        if hasattr(self, '_default_pitch'):
            self.set_pitch(self._default_pitch)

    def set_temp_params(self, rate=None, pitch=None, voice_index=None):
        if voice_index is not None:
            self.set_voice_by_index(voice_index)
        if rate is not None:
            self.set_rate(rate)
        if pitch is not None:
            self.set_pitch(pitch)

    def apply_profile(self, voice_index=None, rate=None, pitch=None):
        if voice_index is not None:
            self.set_voice_by_index(voice_index)
        if rate is not None:
            self.set_rate(rate)
        if pitch is not None:
            self.set_pitch(pitch)

    def set_punctuation_level(self, level):
        pass

    def get_punctuation_level(self):
        return "Some"

    def set_capital_pitch_change(self, value):
        pass

    def get_capital_pitch_change(self):
        return "Off"

    def set_volume_ducking(self, enabled):
        pass

    def get_volume_ducking(self):
        return False

    def wait_until_done(self, timeout_ms=5000):
        self._dll.TextToSpeechSync(self._handle)

    def repeat_last(self):
        if hasattr(self, '_speech_history') and self._speech_history:
            self.speak(self._speech_history[-1])
