import importlib
import os
import subprocess
import tempfile


class AudioPlayer:
    def __init__(self):
        self._ffplay_proc = None
        self.playing = False
        self._sd = None
        self._sf = None

    def _ensure_audio(self):
        if self._sd is None:
            self._sd = importlib.import_module('sounddevice')
        if self._sf is None:
            self._sf = importlib.import_module('soundfile')

    def play_file(self, path):
        self.stop()
        if not os.path.exists(path):
            return False
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.wav', '.flac', '.ogg'):
            try:
                self._ensure_audio()
                data, sr = self._sf.read(path, dtype='float32')
                if data.ndim == 1:
                    data = data.reshape(-1, 1)
                self._sd.play(data, sr, blocking=False)
                self.playing = True
                return True
            except Exception:
                return False
        try:
            fd, tmp = tempfile.mkstemp(suffix='.wav')
            os.close(fd)
            subprocess.run(
                ['ffmpeg', '-y', '-i', path, '-acodec', 'pcm_f32le', '-ar', '44100', '-ac', '1', tmp],
                capture_output=True, timeout=30
            )
            self._ensure_audio()
            data, sr = self._sf.read(tmp, dtype='float32')
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            self._sd.play(data, sr, blocking=False)
            self.playing = True
            return True
        except Exception:
            return False
        finally:
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
                self._ensure_audio()
                data, sr = self._sf.read(path, dtype='float32')
                if data.ndim == 1:
                    data = data.reshape(-1, 1)
                self._sd.play(data, sr, blocking=True)
            except Exception:
                pass
        else:
            try:
                fd, tmp = tempfile.mkstemp(suffix='.wav')
                os.close(fd)
                subprocess.run(
                    ['ffmpeg', '-y', '-i', path, '-acodec', 'pcm_f32le', '-ar', '44100', '-ac', '1', tmp],
                    capture_output=True, timeout=30
                )
                self._ensure_audio()
                data, sr = self._sf.read(tmp, dtype='float32')
                if data.ndim == 1:
                    data = data.reshape(-1, 1)
                self._sd.play(data, sr, blocking=True)
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
        if self._sd:
            self._sd.stop()
        if self._ffplay_proc:
            try:
                self._ffplay_proc.kill()
            except Exception:
                pass
            self._ffplay_proc = None
        self.playing = False
