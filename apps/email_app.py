import win32con
from core.app_base import SoftApp

class EmailApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        # Placeholder for encrypted credential handling
        self.speak("Email app loaded.")

    def on_focus(self):
        self.speak("Email. Press Escape to exit.")

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
