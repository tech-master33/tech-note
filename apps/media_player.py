import os
import win32con
from core.app_base import SoftApp
from core.audio_player import AudioPlayer
from core.config import TECH_SOFT


class MediaPlayerApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.media_path = os.path.join(TECH_SOFT, 'media')
        os.makedirs(self.media_path, exist_ok=True)
        self.player = AudioPlayer()
        self.index = 0
        self.refresh_tracks()

    def refresh_tracks(self):
        try:
            self.tracks = [f for f in os.listdir(self.media_path)
                          if f.lower().endswith(('.mp3', '.wav', '.flac', '.ogg', '.wma', '.m4a', '.aac'))]
        except OSError:
            self.tracks = []
        if self.index >= len(self.tracks):
            self.index = 0

    def on_focus(self):
        self.refresh_tracks()
        msg = self.tracks[self.index] if self.tracks else "No media found"
        self.speak("Media Player. " + msg)
        self.window.update_text("Media: " + msg)

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.player.stop()
            self.exit_app()
            return

        if not self.tracks:
            self.speak("No media found in media folder")
            return

        if vk == win32con.VK_SPACE or vk == win32con.VK_DOWN:
            self.player.stop()
            self.index = (self.index + 1) % len(self.tracks)
            self.announce()
        elif vk == win32con.VK_BACK or vk == win32con.VK_UP:
            self.player.stop()
            self.index = (self.index - 1) % len(self.tracks)
            self.announce()
        elif vk == win32con.VK_RETURN:
            self._play_current()
        elif vk == 0xBB:
            vol = min(1.0, self.player.volume + 0.1)
            self.player.set_volume(vol)
            self.speak(f"Volume {int(vol * 100)}")
        elif vk == 0xBD:
            vol = max(0.0, self.player.volume - 0.1)
            self.player.set_volume(vol)
            self.speak(f"Volume {int(vol * 100)}")

    def _play_current(self):
        if not self.tracks:
            return
        file_path = os.path.join(self.media_path, self.tracks[self.index])
        if not os.path.exists(file_path):
            self.speak("File not found.")
            return
        ok = self.player.play_file(file_path)
        if ok:
            self.speak("Playing " + self.tracks[self.index])
            self.window.update_text("Now Playing: " + self.tracks[self.index])
        else:
            self.speak("Playback failed.")

    def announce(self):
        item = self.tracks[self.index]
        self.speak(item)
        self.window.update_text(item)
