import win32con
from core.app_base import SoftApp
from core.audio_player import AudioPlayer


class FMRadioApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.player = AudioPlayer()
        self.stations = [
            ("BBC World Service", "https://stream.live.vc.bbcmedia.co.uk/bbc_world_service"),
            ("Classic FM", "https://icecast.thisisdax.com/ClassicFMMP3"),
            ("KEXP 90.3 FM", "https://kexp-mp3-128.streamguys1.com/kexp128.mp3"),
            ("NTS Radio", "https://stream-relay-geo.ntslive.net/stream"),
            ("Absolute Radio", "https://edge-bauerall-01-gos2.sharp-stream.com/absoluteradiohigh"),
            ("Smooth Radio", "https://media-ssl.musicradio.com/SmoothUK"),
        ]
        self.index = 0

    def on_focus(self):
        name = self.stations[self.index][0]
        self.speak("FM Radio. " + name)
        self.window.update_text("Radio: " + name)

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.player.stop()
            self.exit_app()
        elif vk == win32con.VK_BACK or vk == win32con.VK_UP:
            self.player.stop()
            self.index = (self.index - 1) % len(self.stations)
            self._announce()
        elif vk == win32con.VK_SPACE or vk == win32con.VK_DOWN:
            self.player.stop()
            self.index = (self.index + 1) % len(self.stations)
            self._announce()
        elif vk == win32con.VK_RETURN:
            self._tune()
        elif vk == win32con.VK_F1:
            self.player.stop()
            self.speak("Stopped")

    def _tune(self):
        name, url = self.stations[self.index]
        self.speak("Tuning to " + name)
        ok = self.player.play_url(url)
        if ok:
            self.speak("Now playing " + name)
            self.window.update_text("Now Playing: " + name)
        else:
            self.speak("Playback failed. Check internet connection.")

    def _announce(self):
        name = self.stations[self.index][0]
        self.speak(name)
        self.window.update_text("Radio: " + name)
