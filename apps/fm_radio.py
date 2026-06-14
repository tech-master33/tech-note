import win32con
from core.app_base import SoftApp
from core.audio_player import AudioPlayer
from core.menu import MenuNode, MenuSystem

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
        self.menu = None

    def _build_menu(self):
        root = MenuNode("Radio")
        for name, url in self.stations:
            root.add_child(MenuNode(name, lambda n=name, u=url: self._tune(n, u)))
        self.menu = MenuSystem(root, self.speak)

    def on_focus(self):
        self._build_menu()
        name = self.menu.get_current_item().title
        self.speak("FM Radio. " + name)
        self.window.update_text("Radio: " + name)

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.player.stop()
            self.exit_app()
            return
        
        if vk == win32con.VK_F1:
            self.player.stop()
            self.speak("Stopped")
            return

        if vk in (win32con.VK_BACK):
            self.player.stop()
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))

        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Radio: " + item.title)

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text("Radio: " + item.title)

    def _tune(self, name, url):
        self.speak("Tuning to " + name)
        ok = self.player.play_url(url)
        if ok:
            self.speak("Now playing " + name)
            self.window.update_text("Now Playing: " + name)
        else:
            self.speak("Playback failed. Check internet connection.")
