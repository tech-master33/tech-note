import os
import win32con
from core.app_base import SoftApp
from core.systmanau import get_audio_manager
from core.config import TECH_SOFT
from core.menu import MenuNode, MenuSystem


class MediaPlayerApp(SoftApp):
    app_id = "media_player"
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.media_path = os.path.join(TECH_SOFT, 'media')
        os.makedirs(self.media_path, exist_ok=True)
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
            
        self.menu = MenuSystem(root, self.speak, stop_func=self.stop)

    def _play_track(self, filename):
        file_path = os.path.join(self.media_path, filename)
        if not os.path.exists(file_path):
            self.speak("File not found.")
            return
        ok = get_audio_manager().play(
            "media", file_path, kind="track", desc=filename, resumable=True, wait=True
        )
        if ok:
            self._announce("Playing " + filename)
        else:
            self.speak("Playback failed.")

    def on_focus(self):
        self._build_menu()
        item = self.menu.get_current_item()
        self._announce("Media Player. " + item.title)

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            get_audio_manager().stop_channel("media")
            self.exit_app()
            return
        if vk == win32con.VK_F1:
            get_audio_manager().stop_channel("media")
            self.speak("Stopped")
            return
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        else:
            self._handle_first_letter_nav(vk, self.menu)
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
        ok = get_audio_manager().play(
            "media", path, kind="track", desc=filename, resumable=True, wait=True
        )
        if ok:
            self._announce("Playing " + filename)
        else:
            self.speak("Playback failed.")
