import importlib
import os
import subprocess
import tempfile


class AudioPlayer:
    _sd = None
    _sf = None

    def __init__(self):
        self._ffplay_proc = None
        self.playing = False

    def _ensure_audio(self):
        if AudioPlayer._sd is None:
            AudioPlayer._sd = importlib.import_module('sounddevice')
        if AudioPlayer._sf is None:
            AudioPlayer._sf = importlib.import_module('soundfile')

    def play_file(self, path):
        self.stop()
        if not os.path.exists(path):
            return False
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.wav', '.flac', '.ogg'):
            try:
                self._ensure_audio()
                data, sr = AudioPlayer._sf.read(path, dtype='float32')
                if data.ndim == 1:
                    data = data.reshape(-1, 1)
                AudioPlayer._sd.play(data, sr, blocking=False)
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
            data, sr = AudioPlayer._sf.read(tmp, dtype='float32')
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            AudioPlayer._sd.play(data, sr, blocking=False)
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
                data, sr = AudioPlayer._sf.read(path, dtype='float32')
                if data.ndim == 1:
                    data = data.reshape(-1, 1)
                AudioPlayer._sd.play(data, sr, blocking=True)
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
                data, sr = AudioPlayer._sf.read(tmp, dtype='float32')
                if data.ndim == 1:
                    data = data.reshape(-1, 1)
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
        # Placeholder for actual volume fading logic
        # For now, we stop immediately to ensure shutdown isn't delayed indefinitely
        self.stop()
