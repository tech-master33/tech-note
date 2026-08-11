import importlib
import math
import os
import queue
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


class _StreamPlayer:
    """One stream (live URL or local file). ffmpeg decodes it to a pipe; a
    reader thread keeps draining it (so ffmpeg never stalls and stays
    current); an sd.OutputStream callback plays the audio. pause() silences
    the output while ffmpeg keeps decoding, so resume() continues where it
    left off — a click pauses the radio/track instead of killing it.

    live=True (radio): audio arriving while paused is discarded so resume
    returns to the live stream. live=False (local tracks): audio is buffered
    while paused (position preserved), and the buffered tail keeps playing
    after ffmpeg finishes decoding, so the end of a track isn't truncated.
    This replaces the old ffplay subprocess, which could only be killed."""

    def __init__(self, owner, source, live=True):
        self.owner = owner          # AudioPlayer (for volume/EQ)
        self.source = source
        self.live = live
        self._proc = None
        self._reader = None
        self._out = None            # sd.OutputStream
        self._queue = queue.Queue(maxsize=32)
        self._buf = b""
        self._paused = False
        self._fade_ms = 0
        self._fade_start = 0.0
        self._eof = False
        self._stop = False

    def start(self):
        self.owner._ensure_audio()
        try:
            self._proc = subprocess.Popen(
                ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', self.source,
                 '-vn', '-acodec', 'pcm_f32le', '-ar', '44100', '-ac', '1',
                 '-f', 'f32le', '-'],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
            )
        except Exception:
            return False
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        try:
            sd = AudioPlayer._sd
            self._out = sd.OutputStream(
                samplerate=44100, channels=1, dtype='float32',
                callback=self._callback,
            )
            self._out.start()
        except Exception:
            self.stop()
            return False
        self.owner.playing = True
        return True

    def _read_loop(self):
        try:
            while not self._stop:
                chunk = self._proc.stdout.read(16384)
                if not chunk:
                    break
                chunk = chunk[:len(chunk) - (len(chunk) % 4)]
                if not chunk:
                    continue
                if self._paused and self.live:
                    continue  # live: discard while paused (stay current)
                try:
                    self._queue.put_nowait(chunk)
                except queue.Full:
                    pass  # drop when the buffer is saturated (stay live)
        except Exception:
            pass
        self._eof = True
        # ffmpeg may finish decoding while audio is still buffered — play
        # the tail out before finishing (avoids truncating the track/stream).
        while not self._stop:
            if self._queue.empty() and not self._buf:
                time.sleep(0.05)
                if self._queue.empty() and not self._buf:
                    break
            elif self._paused:
                time.sleep(0.05)
            else:
                time.sleep(0.02)
        self.stop()

    def _callback(self, outdata, frames, time_info, status):
        np = AudioPlayer._np
        need = frames * 4  # f32 mono bytes
        while len(self._buf) < need and not self._paused:
            try:
                self._buf += self._queue.get_nowait()
            except queue.Empty:
                break
        vol = self.owner.get_volume()
        if self._fade_ms:
            elapsed = time.time() - self._fade_start
            total = self._fade_ms / 1000.0
            if elapsed >= total:
                vol = 0.0
            else:
                vol *= 1.0 - elapsed / total
        if self._paused or len(self._buf) < need or vol <= 0.0:
            if self._paused and self.live:
                self._buf = b""  # live: drop stale audio so resume is current
            if (not self._paused and self._eof and len(self._buf) >= 4
                    and len(self._buf) < need):
                # End of input: play the final partial block, zero-padded.
                n = len(self._buf) // 4
                chunk = self._buf[:n * 4]
                self._buf = b""
                arr = np.frombuffer(chunk, dtype=np.float32)
                arr = self._apply_eq(arr)
                outdata[:len(arr), 0] = arr * vol
                if len(arr) < frames:
                    outdata[len(arr):, 0] = 0
                return
            outdata.fill(0)
            return
        chunk = self._buf[:need]
        self._buf = self._buf[need:]
        arr = np.frombuffer(chunk, dtype=np.float32)
        arr = self._apply_eq(arr)
        outdata[:, 0] = arr * vol

    def _apply_eq(self, arr):
        """Apply the player's EQ preset to one callback chunk (mono).
        Skipped when Flat so the realtime path stays cheap."""
        preset = self.owner.get_eq_preset()
        if preset == "Flat" or len(arr) < 512 or len(arr) % 2:
            return arr
        np = AudioPlayer._np
        gains = EQ_PRESETS.get(preset, EQ_PRESETS["Flat"])
        freqs = np.fft.rfftfreq(len(arr), 1.0 / 44100)
        spectrum = np.fft.rfft(arr)
        band_idx = 0
        for i, f in enumerate(freqs):
            while band_idx < len(EQ_BANDS_HZ) - 1 and f > EQ_BANDS_HZ[band_idx + 1]:
                band_idx += 1
            if band_idx < len(gains):
                spectrum[i] *= 10.0 ** (gains[band_idx] / 20.0)
        return np.fft.irfft(spectrum)

    def pause(self):
        self._paused = True
        self._buf = b""

    def resume(self):
        self._paused = False

    def fade_out(self, ms=1000):
        self._fade_ms = ms
        self._fade_start = time.time()

        def _finish():
            time.sleep(ms / 1000.0 + 0.3)
            self.stop()

        threading.Thread(target=_finish, daemon=True).start()

    def is_alive(self):
        if self._proc is not None and self._proc.poll() is None:
            return True
        # ffmpeg exited: still alive while buffered audio remains to play.
        if self._eof:
            return not (self._queue.empty() and not self._buf)
        return True  # decoding in progress (or between checks)

    def stop(self):
        self._stop = True
        if self._proc:
            try:
                self._proc.kill()
            except Exception:
                pass
            self._proc = None
        if self._out:
            try:
                self._out.stop()
            except Exception:
                pass
            try:
                self._out.close()
            except Exception:
                pass
            self._out = None
        self._buf = b""
        self.owner.playing = False


class AudioPlayer:
    _sd = None
    _sf = None
    _np = None

    def __init__(self):
        self._stream = None
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
                self.play_file_blocking(path, fade_in_ms, fade_out_ms)
            except Exception:
                pass
            finally:
                self.playing = False
        t = threading.Thread(target=_play, daemon=True)
        t.start()

    def play_file_blocking(self, path, fade_in_ms=0, fade_out_ms=0):
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
        """Start streaming a URL through the app's own audio pipeline.
        The stream stays alive across pause()/resume(), so radio preempted
        by a click resumes instantly instead of rebuffering."""
        return self.play_stream(url, live=True)

    def play_stream_file(self, path):
        """Stream a local audio file through the streaming engine so it can
        true-pause and resume mid-track instead of restarting after a click."""
        if not os.path.exists(path):
            return False
        return self.play_stream(path, live=False)

    def play_stream(self, source, live=True):
        self.stop()
        stream = _StreamPlayer(self, source, live=live)
        if not stream.start():
            return False
        self._stream = stream
        self.playing = True
        return True

    def pause(self):
        """Silence the current stream (if any) without killing it; a file
        being played simply stops (the caller replays it on resume)."""
        if self._stream:
            self._stream.pause()
        elif AudioPlayer._sd:
            AudioPlayer._sd.stop()

    def resume(self):
        """Un-silence a paused stream (radio returns to live audio)."""
        if self._stream:
            self._stream.resume()

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream = None
        if AudioPlayer._sd:
            AudioPlayer._sd.stop()
        self.playing = False

    def is_url_playing(self):
        """True while a URL stream is still decoding."""
        return self._stream is not None and self._stream.is_alive()

    def fade_out(self, duration_ms=1000):
        if self._stream:
            self._stream.fade_out(duration_ms)
            return
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
