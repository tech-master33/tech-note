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
        if vk in (win32con.VK_BACK, win32con.VK_UP):
            self.menu.previous()
        elif vk in (win32con.VK_DOWN, win32con.VK_SPACE):
            self.menu.next()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Power: " + item.title)

    def _do_restart(self):
        self.speak("Restarting Tech-Note.")
        self.exit_app()
        if self.on_restart:
            self.on_restart()

    def _do_shutdown(self):
        self.speak("Shutting down Tech-Note.")
        self.exit_app()
        if self.on_exit:
            self.on_exit()