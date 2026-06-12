import json
import os
import win32con
from core.app_base import SoftApp
from core.audio_player import AudioPlayer

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNLOCK_SOUND = os.path.join(BASE, 'sounds', 'unlock.mp3')

class LockScreenApp(SoftApp):
    def __init__(self, manager, window, success_callback):
        super().__init__(manager, window)
        self.success_callback = success_callback
        tech_soft = os.path.join(os.environ['USERPROFILE'], '.tech-soft')
        account_path = os.path.join(tech_soft, 'account.json')
        if os.path.exists(account_path):
            with open(account_path, 'r') as f:
                self.account = json.load(f)
        else:
            self.account = {}
        self.input_pin = ""

    def on_focus(self):
        self.window.update_text("Locked")
        self.speak("Enter PIN to unlock.")

    def _play_unlock(self):
        if os.path.exists(UNLOCK_SOUND):
            AudioPlayer().play_sound_blocking(UNLOCK_SOUND)
        self.speak("Unlocked.")

    def on_key(self, vk):
        if 0x30 <= vk <= 0x39: # Digits
            if len(self.input_pin) < 4:
                self.input_pin += chr(vk)
                self.window.update_text("*" * len(self.input_pin))
                if len(self.input_pin) == 4:
                    if self.input_pin == self.account.get("pin"):
                        self._play_unlock()
                        self.success_callback()
                        self.exit_app()
                    else:
                        self.speak("Wrong PIN.")
                        self.input_pin = ""
                        self.window.update_text("Locked")
        elif vk == win32con.VK_BACK:
            if self.input_pin:
                self.input_pin = self.input_pin[:-1]
                text = "*" * len(self.input_pin) if self.input_pin else "Locked"
                self.window.update_text(text)
