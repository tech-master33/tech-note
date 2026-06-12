import os
import win32con
from core.app_base import SoftApp

class MediaPlayerApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.media_path = os.path.join(os.environ['USERPROFILE'], '.tech-soft', 'media')
        if not os.path.exists(self.media_path):
            os.makedirs(self.media_path)
        self.refresh_tracks()
        self.index = 0

    def refresh_tracks(self):
        self.tracks = [f for f in os.listdir(self.media_path) if f.lower().endswith(('.mp3', '.wav', '.flac'))]
        if self.index >= len(self.tracks):
            self.index = 0

    def on_focus(self):
        self.refresh_tracks()
        self.speak("Media Player. " + (self.tracks[self.index] if self.tracks else "No media found"))
        self.window.update_text("Media: " + (self.tracks[self.index] if self.tracks else "Empty"))

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        if not self.tracks:
            self.speak("No media found in media folder")
            return

        if vk == win32con.VK_SPACE or vk == win32con.VK_DOWN:
            self.index = (self.index + 1) % len(self.tracks)
            self.announce()
        elif vk == win32con.VK_BACK or vk == win32con.VK_UP:
            self.index = (self.index - 1) % len(self.tracks)
            self.announce()
        elif vk == win32con.VK_RETURN:
            file_path = os.path.join(self.media_path, self.tracks[self.index])
            self.speak("Playing " + self.tracks[self.index])
            os.startfile(file_path)

    def announce(self):
        item = self.tracks[self.index]
        self.speak(item)
        self.window.update_text(item)
