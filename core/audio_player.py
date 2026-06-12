import os
import subprocess
import tempfile
import sounddevice as sd
import soundfile as sf


class AudioPlayer:
    def __init__(self):
        self._ffplay_proc = None
        self.playing = False

    def play_file(self, path):
        self.stop()
        if not os.path.exists(path):
            return False
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.wav', '.flac', '.ogg'):
            data, sr = sf.read(path, dtype='float32')
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            sd.play(data, sr, blocking=False)
            self.playing = True
            return True
        # Decode MP3 etc. to temp WAV with ffmpeg, then play
        try:
            fd, tmp = tempfile.mkstemp(suffix='.wav')
            os.close(fd)
            subprocess.run(
                ['ffmpeg', '-y', '-i', path, '-acodec', 'pcm_f32le', '-ar', '44100', '-ac', '1', tmp],
                capture_output=True, timeout=30
            )
            data, sr = sf.read(tmp, dtype='float32')
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            sd.play(data, sr, blocking=False)
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
            data, sr = sf.read(path, dtype='float32')
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            sd.play(data, sr, blocking=True)
        else:
            try:
                fd, tmp = tempfile.mkstemp(suffix='.wav')
                os.close(fd)
                subprocess.run(
                    ['ffmpeg', '-y', '-i', path, '-acodec', 'pcm_f32le', '-ar', '44100', '-ac', '1', tmp],
                    capture_output=True, timeout=30
                )
                data, sr = sf.read(tmp, dtype='float32')
                if data.ndim == 1:
                    data = data.reshape(-1, 1)
                sd.play(data, sr, blocking=True)
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
        sd.stop()
        if self._ffplay_proc:
            try:
                self._ffplay_proc.kill()
            except Exception:
                pass
            self._ffplay_proc = None
        self.playing = False
