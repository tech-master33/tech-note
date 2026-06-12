import win32con
from core.app_base import SoftApp

class PowerApp(SoftApp):
    def __init__(self, manager, window, on_restart=None, on_exit=None):
        super().__init__(manager, window)
        self.on_restart = on_restart
        self.on_exit = on_exit
        self.options = ["Restart Tech-Note", "Shutdown Tech-Note"]
        self.index = 0

    def on_focus(self):
        self.speak("Power Menu. " + self.options[self.index])
        self.window.update_text("Power: " + self.options[self.index])

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
        elif vk == win32con.VK_BACK or vk == win32con.VK_UP:
            self.index = (self.index - 1) % len(self.options)
            self.speak(self.options[self.index])
            self.window.update_text("Power: " + self.options[self.index])
        elif vk == win32con.VK_DOWN or vk == win32con.VK_SPACE:
            self.index = (self.index + 1) % len(self.options)
            self.speak(self.options[self.index])
            self.window.update_text("Power: " + self.options[self.index])
        elif vk == win32con.VK_RETURN:
            self._select_current()

    def _select_current(self):
        key = self.options[self.index].lower().replace(' ', '_')
        if key == "restart_tech-note":
            self.speak("Restarting Tech-Note.")
            self.exit_app()
            if self.on_restart:
                self.on_restart()
        elif key == "shutdown_tech-note":
            self.speak("Shutting down Tech-Note.")
            self.exit_app()
            if self.on_exit:
                self.on_exit()