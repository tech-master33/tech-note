import os
import win32con
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem

class PowerApp(SoftApp):
    def __init__(self, manager, window, on_restart=None, on_exit=None):
        super().__init__(manager, window)
        self.on_restart = on_restart
        self.on_exit = on_exit
        root = MenuNode("Power Menu")
        root.add_child(MenuNode("Restart Tech-Note", self._do_restart))
        root.add_child(MenuNode("Shutdown Tech-Note", self._do_shutdown))
        self.menu = MenuSystem(root, self.speak)

    def on_focus(self):
        item = self.menu.get_current_item()
        title = item.title if item else "Power Menu"
        self.speak("Power Menu. " + title)
        self.window.update_text("Power: " + title)

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            char = chr(vk)
            self.menu.first_letter_nav(char)

        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Power: " + item.title)

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if self.manager.space_used_in_chord:
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text("Power: " + item.title)

    def _do_restart(self):
        self.speak("Restarting Tech-Note.")
        self.window.update_text("Restarting Tech-Note...")
        self.exit_app()
        if self.on_restart:
            self.on_restart()

    def _do_shutdown(self):
        self.speak("Shutting down Tech-Note.")
        self.window.update_text("Shutting down Tech-Note...")
        self.exit_app()
        if self.on_exit:
            self.on_exit()