import os
from core.audio_player import AudioPlayer


class BackgroundAudioService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._player = AudioPlayer()
        self._track_name = ""
        self._source_type = None  # 'file' or 'url'
        self._source_path = ""

    @property
    def is_playing(self):
        return self._player.playing

    @property
    def now_playing(self):
        return self._track_name or "No media playing"

    def play_file(self, path):
        self._player.stop()
        name = os.path.basename(path)
        ok = self._player.play_file(path)
        if ok:
            self._track_name = name
            self._source_type = 'file'
            self._source_path = path
        return ok

    def play_file_background(self, path):
        name = os.path.basename(path)
        self._player.play_file_background(path)
        self._track_name = name
        self._source_type = 'file'
        self._source_path = path

    def play_url(self, url, name="Stream"):
        self._player.stop()
        ok = self._player.play_url(url)
        if ok:
            self._track_name = name
            self._source_type = 'url'
            self._source_path = url
        return ok

    def stop(self):
        self._player.stop()
        self._track_name = ""

    def fade_out(self, duration_ms=1000):
        self._player.fade_out(duration_ms)


background_audio = BackgroundAudioService()
