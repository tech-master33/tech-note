import importlib
import math
import os
import subprocess
import tempfile
import threading
import time

EQ_PRESETS = {
    "Flat": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "Bass Boost": [6.0, 5.0, 3.0, 1.0, 0.0, -1.0, -2.0, -3.0, -4.0, -5.0],
    "Treble Boost": [-5.0, -4.0, -3.0, -2.0, -1.0, 0.0, 1.0, 3.0, 5.0, 6.0],
    "Loudness": [5.0, 4.0, 3.0, 1.5, 0.0, 0.0, 1.5, 3.0, 4.0, 5.0],
    "Vocal": [-3.0, -2.0, -1.0, 1.0, 3.0, 4.0, 5.0, 3.0, 1.0, -1.0],
    "Classical": [4.0, 3.0, 2.0, 0.0, -1.0, -1.0, 0.0, 2.0, 3.0, 4.0],
    "Rock": [5.0, 4.0, 2.0, -1.0, -2.0, -1.0, 2.0, 4.0, 5.0, 5.0],
    "Jazz": [3.0, 2.0, 1.0, 0.0, -1.0, -1.0, 0.0, 1.0, 2.0, 3.0],
}
EQ_BANDS_HZ = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]


class AudioPlayer:
    _sd = None
    _sf = None
    _np = None

    def __init__(self):
        self._ffplay_proc = None
        self.playing = False
        self._eq_preset = "Flat"
        self._volume = 1.0

    def _ensure_audio(self):
        if AudioPlayer._sd is None:
            AudioPlayer._sd = importlib.import_module('sounddevice')
        if AudioPlayer._sf is None:
            AudioPlayer._sf = importlib.import_module('soundfile')
        if AudioPlayer._np is None:
            AudioPlayer._np = importlib.import_module('numpy')

    def get_eq_presets(self):
        return list(EQ_PRESETS.keys())

    def get_eq_preset(self):
        return self._eq_preset

    def set_eq_preset(self, name):
        if name in EQ_PRESETS:
            self._eq_preset = name

    def set_volume(self, vol):
        self._volume = max(0.0, min(2.0, vol))

    def get_volume(self):
        return self._volume

    def _apply_eq(self, data, sr):
        if self._eq_preset == "Flat":
            return data
        gains = EQ_PRESETS.get(self._eq_preset, EQ_PRESETS["Flat"])
        self._ensure_audio()
        np = AudioPlayer._np
        freqs = np.fft.rfftfreq(len(data), 1.0 / sr)
        spectrum = np.fft.rfft(data[:, 0])
        band_idx = 0
        for i, f in enumerate(freqs):
            while band_idx < len(EQ_BANDS_HZ) - 1 and f > EQ_BANDS_HZ[band_idx + 1]:
                band_idx += 1
            if band_idx < len(gains):
                db = gains[band_idx]
                spectrum[i] *= 10.0 ** (db / 20.0)
        result = np.fft.irfft(spectrum)
        if data.ndim == 1:
            return result
        out = np.zeros_like(data)
        out[:, 0] = result
        if data.shape[1] > 1:
            spectrum2 = np.fft.rfft(data[:, 1])
            band_idx = 0
            for i, f in enumerate(freqs):
                while band_idx < len(EQ_BANDS_HZ) - 1 and f > EQ_BANDS_HZ[band_idx + 1]:
                    band_idx += 1
                if band_idx < len(gains):
                    db = gains[band_idx]
                    spectrum2[i] *= 10.0 ** (db / 20.0)
            out[:, 1] = np.fft.irfft(spectrum2)
        return out

    def _apply_fade(self, data, sr, fade_in_ms=0, fade_out_ms=0):
        if fade_in_ms <= 0 and fade_out_ms <= 0:
            return data
        self._ensure_audio()
        np = AudioPlayer._np
        result = data.copy()
        if fade_in_ms > 0:
            n = int(sr * fade_in_ms / 1000)
            if n > 0 and n < len(result):
                for c in range(result.shape[1]):
                    result[:n, c] *= np.linspace(0.0, 1.0, n)
        if fade_out_ms > 0:
            n = int(sr * fade_out_ms / 1000)
            if n > 0 and n < len(result):
                for c in range(result.shape[1]):
                    result[-n:, c] *= np.linspace(1.0, 0.0, n)
        return result

    def _read_and_process(self, path, fade_in_ms=0, fade_out_ms=0):
        self._ensure_audio()
        sf = AudioPlayer._sf
        data, sr = sf.read(path, dtype='float32')
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        data = self._apply_fade(data, sr, fade_in_ms, fade_out_ms)
        data = self._apply_eq(data, sr)
        data *= self._volume
        return data, sr

    def play_file(self, path, fade_in_ms=0, fade_out_ms=0):
        self.stop()
        if not os.path.exists(path):
            return False
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.wav', '.flac', '.ogg'):
            try:
                data, sr = self._read_and_process(path, fade_in_ms, fade_out_ms)
                AudioPlayer._sd.play(data, sr, blocking=False)
                self.playing = True
                return True
            except Exception:
                return False
        tmp = None
        try:
            fd, tmp = tempfile.mkstemp(suffix='.wav')
            os.close(fd)
            subprocess.run(
                ['ffmpeg', '-y', '-i', path, '-acodec', 'pcm_f32le', '-ar', '44100', '-ac', '1', tmp],
                capture_output=True, timeout=30
            )
            data, sr = self._read_and_process(tmp, fade_in_ms, fade_out_ms)
            AudioPlayer._sd.play(data, sr, blocking=False)
            self.playing = True
            return True
        except Exception:
            return False
        finally:
            if tmp is not None:
                try:
                    os.unlink(tmp)
                except Exception:
                    pass

    def play_file_background(self, path, fade_in_ms=0, fade_out_ms=0):
        def _play():
            self.playing = True
            try:
                self._play_file_blocking(path, fade_in_ms, fade_out_ms)
            except Exception:
                pass
            finally:
                self.playing = False
        t = threading.Thread(target=_play, daemon=True)
        t.start()

    def _play_file_blocking(self, path, fade_in_ms=0, fade_out_ms=0):
        if not os.path.exists(path):
            return
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.wav', '.flac', '.ogg'):
            try:
                data, sr = self._read_and_process(path, fade_in_ms, fade_out_ms)
                AudioPlayer._sd.play(data, sr, blocking=True)
            except Exception:
                pass
        else:
            tmp = None
            try:
                fd, tmp = tempfile.mkstemp(suffix='.wav')
                os.close(fd)
                subprocess.run(
                    ['ffmpeg', '-y', '-i', path, '-acodec', 'pcm_f32le', '-ar', '44100', '-ac', '1', tmp],
                    capture_output=True, timeout=30
                )
                data, sr = self._read_and_process(tmp, fade_in_ms, fade_out_ms)
                AudioPlayer._sd.play(data, sr, blocking=True)
            except Exception:
                pass
            finally:
                if tmp:
                    try:
                        os.unlink(tmp)
                    except Exception:
                        pass

    def play_sound_blocking(self, path):
        if not os.path.exists(path):
            return
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.wav', '.flac', '.ogg'):
            try:
                data, sr = self._read_and_process(path)
                AudioPlayer._sd.play(data, sr, blocking=True)
            except Exception:
                pass
        else:
            tmp = None
            try:
                fd, tmp = tempfile.mkstemp(suffix='.wav')
                os.close(fd)
                subprocess.run(
                    ['ffmpeg', '-y', '-i', path, '-acodec', 'pcm_f32le', '-ar', '44100', '-ac', '1', tmp],
                    capture_output=True, timeout=30
                )
                data, sr = self._read_and_process(tmp)
                AudioPlayer._sd.play(data, sr, blocking=True)
            except Exception:
                pass
            finally:
                try:
                    os.unlink(tmp)
                except Exception:
                    pass

    def play_url(self, url):
        self.stop()
        try:
            self._ffplay_proc = subprocess.Popen(
                ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', url],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            self.playing = True
            return True
        except Exception:
            return False

    def stop(self):
        if AudioPlayer._sd:
            AudioPlayer._sd.stop()
        if self._ffplay_proc:
            try:
                self._ffplay_proc.kill()
            except Exception:
                pass
            self._ffplay_proc = None
        self.playing = False

    def fade_out(self, duration_ms=1000):
        if not self.playing:
            return
        try:
            self._ensure_audio()
            np = AudioPlayer._np
            sd = AudioPlayer._sd
            if sd is None:
                return
            current_data = sd.get_stream().read(sd.query_streams()['samplerate'] * duration_ms // 1000) if sd.query_streams() else None
            if current_data is not None and len(current_data) > 0:
                ramp = np.linspace(1.0, 0.0, len(current_data))
                for c in range(current_data.shape[1]):
                    current_data[:, c] *= ramp
                sd.play(current_data, blocking=True)
        except Exception:
            pass
        self.stop()

    def fade_in(self, duration_ms=1000):
        if not self.playing:
            return
        try:
            self._ensure_audio()
            np = AudioPlayer._np
            sd = AudioPlayer._sd
            if sd is None:
                return
            current_data = sd.get_stream().read(sd.query_streams()['samplerate'] * duration_ms // 1000) if sd.query_streams() else None
            if current_data is not None and len(current_data) > 0:
                ramp = np.linspace(0.0, 1.0, len(current_data))
                for c in range(current_data.shape[1]):
                    current_data[:, c] *= ramp
                sd.play(current_data, blocking=True)
        except Exception:
            pass
