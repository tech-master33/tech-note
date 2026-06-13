import win32con
import win32api
from core.menu import MenuNode, MenuSystem
from apps.dora.dora_config import load_settings, save_settings

class DoraSetup:
    def __init__(self, assistant, speak_func):
        self.assistant = assistant
        self.speak = speak_func
        self.username = ""
        self.ai_enabled = False
        self.current_step = 0
        self.active = True

    def run(self):
        self.speak("Welcome to Dora setup. Press Enter to begin.")
        self.current_step = 0

    def on_key(self, vk):
        if self.current_step == 0:
            if vk == win32con.VK_RETURN:
                self.current_step = 1
                self.speak("Enter your name.")
            return

        if self.current_step == 1:
            if vk == win32con.VK_RETURN:
                if self.username:
                    self.current_step = 2
                    self.speak("Enable AI chat? Use arrows to select Yes or No.")
                else:
                    self.speak("Name cannot be empty.")
            elif vk == win32con.VK_BACK:
                if self.username:
                    self.username = self.username[:-1]
            else:
                ch = self._vk_to_char(vk)
                if ch:
                    self.username += ch
            return

        if self.current_step == 2:
            if vk in (win32con.VK_SPACE, win32con.VK_DOWN):
                self.ai_enabled = not self.ai_enabled
                self.speak("Yes" if self.ai_enabled else "No")
            elif vk in (win32con.VK_BACK, win32con.VK_UP):
                self.ai_enabled = not self.ai_enabled
                self.speak("Yes" if self.ai_enabled else "No")
            elif vk == win32con.VK_RETURN:
                self._finish()
            return

    def _vk_to_char(self, vk):
        shift = win32api.GetAsyncKeyState(win32con.VK_SHIFT) & 0x8000
        if 0x41 <= vk <= 0x5A:
            return chr(vk).upper() if shift else chr(vk).lower()
        if 0x30 <= vk <= 0x39:
            return chr(vk)
        if vk == win32con.VK_SPACE:
            return ' '
        return None

    def _finish(self):
        settings = load_settings()
        settings['username'] = self.username if self.username else "User"
        settings['ai_enabled'] = self.ai_enabled
        save_settings(settings)
        self.speak("Setup complete. Dora is ready.")
        self.active = False
