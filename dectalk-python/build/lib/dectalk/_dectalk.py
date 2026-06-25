import ctypes
import ctypes.wintypes
import os
import atexit
import tempfile
import struct
from pathlib import Path

# Windows types
HWND = ctypes.wintypes.HWND
UINT = ctypes.wintypes.UINT
DWORD = ctypes.wintypes.DWORD
LPDWORD = ctypes.POINTER(DWORD)
LONG = ctypes.wintypes.LONG
LPVOID = ctypes.wintypes.LPVOID
LPSTR = ctypes.wintypes.LPSTR
LPTSTR = ctypes.wintypes.LPWSTR
BOOL = ctypes.wintypes.BOOL
WORD = ctypes.wintypes.WORD
MMRESULT = ctypes.c_long

# Error codes
MMSYSERR_NOERROR = 0

# Speaker constants
PAUL, BETTY, HARRY, FRANK, DENNIS, KIT, URSULA, RITA, WENDY = range(9)

voices = {
    "Paul": PAUL, "Betty": BETTY, "Harry": HARRY,
    "Frank": FRANK, "Dennis": DENNIS, "Kit": KIT,
    "Ursula": URSULA, "Rita": RITA, "Wendy": WENDY,
}

class Speaker:
    Paul = 0; Betty = 1; Harry = 2; Frank = 3
    Dennis = 4; Kit = 5; Ursula = 6; Rita = 7; Wendy = 8

# TTS flags
TTS_NORMAL = 0
TTS_FORCE = 1

# Status identifiers
INPUT_CHARACTER_COUNT = 0
STATUS_SPEAKING = 1

# Output states
STATE_OUTPUT_AUDIO = 0
STATE_OUTPUT_MEMORY = 1
STATE_OUTPUT_WAVE_FILE = 2
STATE_OUTPUT_NULL = 4

# Volume types
VOLUME_MAIN = 1
VOLUME_ATTENUATION = 2

# Language
TTS_AMERICAN_ENGLISH = 1

# SPDEFS parameter indices
SP_SEX = 0
SP_SMOOTHNESS = 1
SP_ASSERTIVENESS = 2
SP_AVERAGE_PITCH = 3
SP_PITCH_RANGE = 4
SP_BREATHINESS = 5
SP_RICHNESS = 6
SP_HEAD_SIZE = 9

class TTS_BUFFER(ctypes.Structure):
    _fields_ = [
        ("lpData", LPVOID),
        ("lpPhonemeArray", LPVOID),
        ("lpIndexArray", LPVOID),
        ("dwMaximumBufferLength", DWORD),
        ("dwMaximumNumberOfPhonemeChanges", DWORD),
        ("dwMaximumNumberOfIndexMarks", DWORD),
        ("dwBufferLength", DWORD),
        ("dwNumberOfPhonemeChanges", DWORD),
        ("dwNumberOfIndexMarks", DWORD),
        ("dwReserved", DWORD),
    ]

class TTS_CAPS(ctypes.Structure):
    _fields_ = [
        ("dwNumberOfLanguages", DWORD),
        ("lpLanguageParamsArray", LPVOID),
        ("dwSampleRate", DWORD),
        ("dwMinimumSpeakingRate", DWORD),
        ("dwMaximumSpeakingRate", DWORD),
        ("dwNumberOfPredefinedSpeakers", DWORD),
        ("dwCharacterSet", DWORD),
        ("Version", DWORD),
    ]


DTCALLBACK = ctypes.CFUNCTYPE(None, LONG, LONG, DWORD, UINT)


class _DectalkLib:
    def __init__(self):
        lib_path = self._find_lib()
        self._dll = ctypes.WinDLL(lib_path)
        self._setup_functions()
        self._dictionary_loaded = False

    def _find_lib(self):
        search_dirs = [
            Path(__file__).parent / "bin",
            Path.cwd(),
            Path(os.environ.get("DECTALK_DIR", ".")),
        ]
        for d in search_dirs:
            p = d / "DECtalk.dll"
            if p.exists():
                return str(p)
        raise FileNotFoundError(
            "DECtalk.dll not found. Place it in one of: "
            + ", ".join(str(d) for d in search_dirs)
        )

    def _setup_functions(self):
        dll = self._dll

        # Startup/Shutdown
        dll.TextToSpeechStartupExFonix.argtypes = [
            ctypes.POINTER(LPVOID), UINT, DWORD, DTCALLBACK, LONG, LPSTR
        ]
        dll.TextToSpeechStartupExFonix.restype = MMRESULT

        dll.TextToSpeechShutdown.argtypes = [LPVOID]
        dll.TextToSpeechShutdown.restype = MMRESULT

        # Speaking
        dll.TextToSpeechSpeak.argtypes = [LPVOID, LPSTR, DWORD]
        dll.TextToSpeechSpeak.restype = MMRESULT

        dll.TextToSpeechPause.argtypes = [LPVOID]
        dll.TextToSpeechPause.restype = MMRESULT

        dll.TextToSpeechResume.argtypes = [LPVOID]
        dll.TextToSpeechResume.restype = MMRESULT

        dll.TextToSpeechReset.argtypes = [LPVOID, BOOL]
        dll.TextToSpeechReset.restype = MMRESULT

        dll.TextToSpeechSync.argtypes = [LPVOID]
        dll.TextToSpeechSync.restype = MMRESULT

        dll.TextToSpeechGetStatus.argtypes = [LPVOID, LPDWORD, LPDWORD, DWORD]
        dll.TextToSpeechGetStatus.restype = MMRESULT

        # Rate
        dll.TextToSpeechGetRate.argtypes = [LPVOID, LPDWORD]
        dll.TextToSpeechGetRate.restype = MMRESULT

        dll.TextToSpeechSetRate.argtypes = [LPVOID, DWORD]
        dll.TextToSpeechSetRate.restype = MMRESULT

        # Speaker
        dll.TextToSpeechGetSpeaker.argtypes = [LPVOID, LPDWORD]
        dll.TextToSpeechGetSpeaker.restype = MMRESULT

        dll.TextToSpeechSetSpeaker.argtypes = [LPVOID, DWORD]
        dll.TextToSpeechSetSpeaker.restype = MMRESULT

        # Language
        dll.TextToSpeechGetLanguage.argtypes = [LPVOID, LPDWORD]
        dll.TextToSpeechGetLanguage.restype = MMRESULT

        dll.TextToSpeechSetLanguage.argtypes = [LPVOID, DWORD]
        dll.TextToSpeechSetLanguage.restype = MMRESULT

        dll.TextToSpeechStartLang.argtypes = [LPSTR]
        dll.TextToSpeechStartLang.restype = UINT

        dll.TextToSpeechSelectLang.argtypes = [LPVOID, UINT]
        dll.TextToSpeechSelectLang.restype = BOOL

        dll.TextToSpeechCloseLang.argtypes = [LPSTR]
        dll.TextToSpeechCloseLang.restype = BOOL

        # Volume
        dll.TextToSpeechSetVolume.argtypes = [LPVOID, ctypes.c_int, ctypes.c_int]
        dll.TextToSpeechSetVolume.restype = MMRESULT

        dll.TextToSpeechGetVolume.argtypes = [LPVOID, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        dll.TextToSpeechGetVolume.restype = MMRESULT

        # Wave file
        dll.TextToSpeechOpenWaveOutFile.argtypes = [LPVOID, LPSTR, DWORD]
        dll.TextToSpeechOpenWaveOutFile.restype = MMRESULT

        dll.TextToSpeechCloseWaveOutFile.argtypes = [LPVOID]
        dll.TextToSpeechCloseWaveOutFile.restype = MMRESULT

        # Memory output
        dll.TextToSpeechOpenInMemory.argtypes = [LPVOID, DWORD]
        dll.TextToSpeechOpenInMemory.restype = MMRESULT

        dll.TextToSpeechCloseInMemory.argtypes = [LPVOID]
        dll.TextToSpeechCloseInMemory.restype = MMRESULT

        dll.TextToSpeechAddBuffer.argtypes = [LPVOID, ctypes.POINTER(TTS_BUFFER)]
        dll.TextToSpeechAddBuffer.restype = MMRESULT

        dll.TextToSpeechReturnBuffer.argtypes = [LPVOID, ctypes.POINTER(LPVOID)]
        dll.TextToSpeechReturnBuffer.restype = MMRESULT

        # Dictionary
        dll.TextToSpeechLoadUserDictionary.argtypes = [LPVOID, LPSTR]
        dll.TextToSpeechLoadUserDictionary.restype = MMRESULT

        dll.TextToSpeechUnloadUserDictionary.argtypes = [LPVOID]
        dll.TextToSpeechUnloadUserDictionary.restype = MMRESULT

        # Version
        dll.TextToSpeechVersion.argtypes = [ctypes.POINTER(LPSTR)]
        dll.TextToSpeechVersion.restype = DWORD

        dll.TextToSpeechVersionEx.argtypes = [LPVOID]
        dll.TextToSpeechVersionEx.restype = DWORD

        # Caps
        dll.TextToSpeechGetCaps.argtypes = [ctypes.POINTER(TTS_CAPS)]
        dll.TextToSpeechGetCaps.restype = MMRESULT

        # Features
        dll.TextToSpeechGetFeatures.restype = DWORD

        # Log file
        dll.TextToSpeechOpenLogFile.argtypes = [LPVOID, LPSTR, DWORD]
        dll.TextToSpeechOpenLogFile.restype = MMRESULT

        dll.TextToSpeechCloseLogFile.argtypes = [LPVOID]
        dll.TextToSpeechCloseLogFile.restype = MMRESULT

        # Speaker params
        dll.TextToSpeechGetSpeakerParams.argtypes = [
            LPVOID, UINT,
            ctypes.POINTER(LPVOID), ctypes.POINTER(LPVOID),
            ctypes.POINTER(LPVOID), ctypes.POINTER(LPVOID),
        ]
        dll.TextToSpeechGetSpeakerParams.restype = MMRESULT

        dll.TextToSpeechSetSpeakerParams.argtypes = [LPVOID, LPVOID]
        dll.TextToSpeechSetSpeakerParams.restype = MMRESULT

        dll.TextToSpeechGetPhVdefParams.argtypes = [LPVOID, UINT]
        dll.TextToSpeechGetPhVdefParams.restype = ctypes.POINTER(ctypes.c_short)

        # Dictionary management
        dll.TextToSpeechDumpDictionary.argtypes = [LPVOID, LPSTR]
        dll.TextToSpeechDumpDictionary.restype = MMRESULT

        dll.TextToSpeechConvertToPhonemes.argtypes = [
            LPVOID, LPSTR, LPDWORD, DWORD, LPSTR, DWORD, DWORD
        ]
        dll.TextToSpeechConvertToPhonemes.restype = MMRESULT

        self._dll = dll


_lib = None


def _get_lib():
    global _lib
    if _lib is None:
        _lib = _DectalkLib()
    return _lib


_dummy_callback = DTCALLBACK(lambda l1, l2, d, u: None)


class Dectalk:
    def __init__(self, device_options=0, hwnd=None):
        self._lib = _get_lib()
        self._handle = LPVOID()
        self._owns_dic = False

        dic_path = Path(__file__).parent / "bin" / "dtalk_us.dic"
        dic_arg = LPSTR(str(dic_path).encode("utf-8")) if dic_path.exists() else LPSTR()
        mmr = self._lib._dll.TextToSpeechStartupExFonix(
            ctypes.byref(self._handle),
            UINT(0),
            DWORD(device_options),
            _dummy_callback,
            LONG(hwnd if hwnd is not None else 0),
            dic_arg,
        )
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"Dectalk startup failed: error {mmr}")

        atexit.register(self._cleanup)

    def _cleanup(self):
        if self._handle:
            try:
                if self._owns_dic:
                    self._cleanup_dic_dir()
                self._lib._dll.TextToSpeechShutdown(self._handle)
            except Exception:
                pass
            self._handle = None

    def load_dictionary(self, dic_path=None):
        if dic_path is None:
            dic_path = Path(__file__).parent / "bin" / "dtalk_us.dic"
        if not Path(dic_path).exists():
            raise FileNotFoundError(f"Dictionary not found: {dic_path}")

        mmr = self._lib._dll.TextToSpeechLoadUserDictionary(
            self._handle, LPSTR(str(dic_path).encode("utf-8"))
        )
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"TextToSpeechLoadUserDictionary failed: error {mmr}")

    def speak(self, text, flags=TTS_NORMAL):
        encoded = (text + "\0").encode("ascii", errors="replace")
        buf = ctypes.create_string_buffer(encoded)
        mmr = self._lib._dll.TextToSpeechSpeak(self._handle, buf, DWORD(flags))
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"TextToSpeechSpeak failed: error {mmr}")

    def speak_async(self, text):
        return self.speak(text, TTS_FORCE)

    def pause(self):
        mmr = self._lib._dll.TextToSpeechPause(self._handle)
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"TextToSpeechPause failed: error {mmr}")

    def resume(self):
        mmr = self._lib._dll.TextToSpeechResume(self._handle)
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"TextToSpeechResume failed: error {mmr}")

    def reset(self):
        mmr = self._lib._dll.TextToSpeechReset(self._handle, BOOL(True))
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"TextToSpeechReset failed: error {mmr}")

    def sync(self):
        mmr = self._lib._dll.TextToSpeechSync(self._handle)
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"TextToSpeechSync failed: error {mmr}")

    @property
    def rate(self):
        val = DWORD()
        mmr = self._lib._dll.TextToSpeechGetRate(self._handle, ctypes.byref(val))
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"TextToSpeechGetRate failed: error {mmr}")
        return val.value

    @rate.setter
    def rate(self, value):
        mmr = self._lib._dll.TextToSpeechSetRate(self._handle, DWORD(value))
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"TextToSpeechSetRate failed: error {mmr}")

    @property
    def speaker(self):
        val = DWORD()
        mmr = self._lib._dll.TextToSpeechGetSpeaker(self._handle, ctypes.byref(val))
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"TextToSpeechGetSpeaker failed: error {mmr}")
        return val.value

    @speaker.setter
    def speaker(self, value):
        mmr = self._lib._dll.TextToSpeechSetSpeaker(self._handle, DWORD(value))
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"TextToSpeechSetSpeaker failed: error {mmr}")

    @property
    def is_speaking(self):
        chars = DWORD()
        speaking = DWORD()
        mmr = self._lib._dll.TextToSpeechGetStatus(
            self._handle, ctypes.byref(chars), ctypes.byref(speaking), DWORD(STATUS_SPEAKING)
        )
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"TextToSpeechGetStatus failed: error {mmr}")
        return speaking.value != 0

    @property
    def volume(self):
        val = ctypes.c_int()
        mmr = self._lib._dll.TextToSpeechGetVolume(
            self._handle, ctypes.c_int(VOLUME_MAIN), ctypes.byref(val)
        )
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"TextToSpeechGetVolume failed: error {mmr}")
        return val.value

    @volume.setter
    def volume(self, value):
        mmr = self._lib._dll.TextToSpeechSetVolume(
            self._handle, ctypes.c_int(VOLUME_MAIN), ctypes.c_int(value)
        )
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"TextToSpeechSetVolume failed: error {mmr}")

    @property
    def version(self):
        ver_str = LPSTR()
        ver = self._lib._dll.TextToSpeechVersion(ctypes.byref(ver_str))
        return ver, ver_str.value.decode("ascii") if ver_str else str(ver)

    @property
    def caps(self):
        caps = TTS_CAPS()
        mmr = self._lib._dll.TextToSpeechGetCaps(ctypes.byref(caps))
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"TextToSpeechGetCaps failed: error {mmr}")
        return caps

    def open_wave_file(self, path):
        encoded = (str(path) + "\0").encode("utf-8")
        buf = ctypes.create_string_buffer(encoded)
        mmr = self._lib._dll.TextToSpeechOpenWaveOutFile(self._handle, buf, DWORD(0))
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"TextToSpeechOpenWaveOutFile failed: error {mmr}")

    def close_wave_file(self):
        mmr = self._lib._dll.TextToSpeechCloseWaveOutFile(self._handle)
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"TextToSpeechCloseWaveOutFile failed: error {mmr}")

    @property
    def language(self):
        val = DWORD()
        mmr = self._lib._dll.TextToSpeechGetLanguage(self._handle, ctypes.byref(val))
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"TextToSpeechGetLanguage failed: error {mmr}")
        return val.value

    @language.setter
    def language(self, value):
        mmr = self._lib._dll.TextToSpeechSetLanguage(self._handle, DWORD(value))
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"TextToSpeechSetLanguage failed: error {mmr}")

    def open_in_memory(self, max_buffer=65536):
        mmr = self._lib._dll.TextToSpeechOpenInMemory(self._handle, DWORD(max_buffer))
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"TextToSpeechOpenInMemory failed: error {mmr}")

    def close_in_memory(self):
        mmr = self._lib._dll.TextToSpeechCloseInMemory(self._handle)
        if mmr != MMSYSERR_NOERROR:
            raise RuntimeError(f"TextToSpeechCloseInMemory failed: error {mmr}")

    def synthesize_to_wav(self, text, output_path):
        self.open_wave_file(output_path)
        try:
            self.speak(text)
            self.sync()
        finally:
            self.close_wave_file()

    def synthesize_to_memory(self, text):
        import io
        data = []
        self.open_in_memory()
        try:
            self.speak(text)
            self.sync()
            while True:
                buf_ptr = LPVOID()
                mmr = self._lib._dll.TextToSpeechReturnBuffer(
                    self._handle, ctypes.byref(buf_ptr)
                )
                if mmr != MMSYSERR_NOERROR or not buf_ptr:
                    break
                buf = ctypes.cast(buf_ptr, ctypes.POINTER(TTS_BUFFER))
                if buf.contents.dwBufferLength == 0:
                    break
                segment = ctypes.string_at(buf.contents.lpData, buf.contents.dwBufferLength)
                data.append(segment)
        finally:
            self.close_in_memory()
        return b"".join(data)

    def close(self):
        self._cleanup()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
