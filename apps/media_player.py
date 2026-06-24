import os
import win32con
from core.app_base import SoftApp
from core.audio_player import AudioPlayer
from core.config import TECH_SOFT
from core.menu import MenuNode, MenuSystem

class MediaPlayerApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.media_path = os.path.join(TECH_SOFT, 'media')
        os.makedirs(self.media_path, exist_ok=True)
        self.player = AudioPlayer()
        self.menu = None
        self.tracks = []

    def _build_menu(self):
        try:
            self.tracks = sorted([f for f in os.listdir(self.media_path)
                          if f.lower().endswith(('.mp3', '.wav', '.flac', '.ogg', '.wma', '.m4a', '.aac'))])
        except OSError:
            self.tracks = []
            
        root = MenuNode("Media Player")
        for track in self.tracks:
            root.add_child(MenuNode(track, lambda t=track: self._play_track(t)))
        
        if not self.tracks:
            root.add_child(MenuNode("No media found"))
            
        self.menu = MenuSystem(root, self.speak)

    def _play_track(self, filename):
        file_path = os.path.join(self.media_path, filename)
        if not os.path.exists(file_path):
            self.speak("File not found.")
            return
        self.player.stop()
        ok = self.player.play_file(file_path)
        if ok:
            self.speak("Playing " + filename)
            self.window.update_text("Playing: " + filename)
        else:
            self.speak("Playback failed.")

    def on_focus(self):
        self._build_menu()
        item = self.menu.get_current_item()
        self.speak("Media Player. " + item.title)
        self.window.update_text("Media: " + item.title)

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
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))

        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Media: " + item.title)

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text("Media: " + item.title)
            
    def get_help_text(self):
        return "Media Player. Space for next, Backspace for previous. Enter to play. F1 to stop. Press Escape to exit."

    def load_file(self, path):
        filename = os.path.basename(path)
        self.player.stop()
        ok = self.player.play_file(path)
        if ok:
            self.speak("Playing " + filename)
            self.window.update_text("Playing: " + filename)
        else:
            self.speak("Playback failed.")
