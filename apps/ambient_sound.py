import threading
import time
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode
from core.audio_player import AudioPlayer

SOUNDS = {
    "Rain": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
    "Ocean Waves": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
    "White Noise": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
    "Forest": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3",
    "Creek": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3",
    "Thunder": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3",
    "Wind": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-7.mp3",
    "Fire": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3",
}


class AmbientSound(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.player = AudioPlayer()
        self._playing = None
        self._volume = 50
        self._build_menu()

    def _build_menu(self):
        root = MenuNode("Ambient Sounds")
        for name in SOUNDS:
            indicator = " *" if self._playing == name else ""
            root.add_child(MenuNode(f"{name}{indicator}", lambda n=name: self._play(n)))
        root.add_child(MenuNode("Stop", self._stop))
        root.add_child(MenuNode(f"Volume: {self._volume}%", self._adjust_volume))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _play(self, name):
        self._stop()
        url = SOUNDS[name]
        self.player.play_url(url)
        self._playing = name
        self.player.set_volume(self._volume / 100.0) if hasattr(self.player, 'set_volume') else None
        self.speak(f"Playing {name}.")
        self._build_menu()
        self.menu.announce_current()

    def _stop(self):
        self.player.stop()
        self._playing = None
        self.speak("Stopped.")

    def _adjust_volume(self):
        self._input_mode = "volume"
        self._input_text = str(self._volume)
        self.speak(f"Current volume {self._volume}. Enter new volume 0-100.")
        self.window.update_text(f"Volume ({self._volume}): ")

    def on_focus(self):
        if self._playing:
            self.speak(f"Ambient Sounds. Playing {self._playing}.")
        else:
            self._build_menu()
            item = self.menu.get_current_item()
            self.speak("Ambient Sounds. " + (item.title if item else ""))

    def on_key(self, vk):
        if getattr(self, '_input_mode', None):
            if vk == win32con.VK_ESCAPE:
                self._input_mode = None
                self._build_menu()
                self.menu.announce_current()
                return
            if vk == win32con.VK_RETURN:
                try:
                    v = int(self._input_text.strip())
                    self._volume = max(0, min(100, v))
                    if self._playing:
                        self.player.set_volume(self._volume / 100.0) if hasattr(self.player, 'set_volume') else None
                    self.speak(f"Volume set to {self._volume}.")
                except:
                    self.speak("Invalid.")
                self._input_mode = None
                self._build_menu()
                self.menu.announce_current()
                return
            if vk == win32con.VK_BACK:
                self._input_text = self._input_text[:-1]
                self.window.update_text(f"Volume: {self._input_text}")
                return
            if 0x30 <= vk <= 0x39:
                self._input_text += chr(vk)
                self.window.update_text(f"Volume: {self._input_text}")
            return
        if vk == win32con.VK_ESCAPE:
            self.player.stop()
            self.exit_app()
            return
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        else:
            self._handle_first_letter_nav(vk, self.menu)
        item = self.menu.get_current_item()
        if item:
            self.window.update_text(item.title)

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text(item.title)

    def get_help_text(self):
        return "Ambient Sounds. Play rain, ocean, white noise, and more. Space next, Backspace previous. Enter to play. Escape exit."
