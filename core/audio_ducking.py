import ctypes
import threading

winmm = ctypes.windll.winmm

class AudioDucker:
    def __init__(self):
        self._enabled = False
        self._duck_level = 0.15
        self._saved_volume = None
        self._timer = None

    def set_enabled(self, enabled):
        self._enabled = enabled
        if not enabled:
            self.unduck()

    def duck(self):
        if not self._enabled:
            return
        if self._timer:
            self._timer.cancel()
            self._timer = None
        if self._saved_volume is None:
            try:
                vol = ctypes.c_uint(0)
                winmm.waveOutGetVolume(0, ctypes.byref(vol))
                self._saved_volume = vol.value
                new_l = int(self._duck_level * 65535)
                new_r = int(self._duck_level * 65535)
                winmm.waveOutSetVolume(0, new_l | (new_r << 16))
            except Exception:
                pass

    def unduck(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None
        if self._saved_volume is not None:
            try:
                winmm.waveOutSetVolume(0, self._saved_volume)
            except Exception:
                pass
            self._saved_volume = None

    def schedule_unduck(self, text, rate=0):
        est_chars_per_sec = max(3, 15 + rate * 1.5)
        delay = max(0.3, len(text) / est_chars_per_sec + 0.5)
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(delay, self.unduck)
        self._timer.daemon = True
        self._timer.start()
