import win32con
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.background_audio import background_audio


class AudioControlPanel(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._build_menu()

    def _build_menu(self):
        root = MenuNode("Audio Control")
        root.add_child(MenuNode("Now Playing: " + background_audio.now_playing, None))
        root.add_child(MenuNode("Stop", lambda: self._cmd_stop()))
        root.add_child(MenuNode("Volume Up", lambda: self._cmd_volume(10)))
        root.add_child(MenuNode("Volume Down", lambda: self._cmd_volume(-10)))
        self.menu = MenuSystem(root, self.speak)

    def _cmd_stop(self):
        background_audio.stop()
        self._rebuild()

    def _cmd_volume(self, delta):
        current = self.manager.synth.get_volume()
        new_vol = max(0, min(100, current + delta))
        self.manager.synth.set_volume(new_vol)
        self.speak(f"Volume {new_vol}")

    def _rebuild(self):
        self._build_menu()
        self.menu.announce_current()

    def on_focus(self):
        self._rebuild()

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        self._update_display()

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            self._update_display()

    def _update_display(self):
        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Audio: " + item.title)
