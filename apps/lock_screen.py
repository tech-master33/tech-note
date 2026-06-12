import json
import os
import datetime
import win32con
import psutil
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
        self.state = "locked_info"

    def _battery_info(self):
        try:
            bat = psutil.sensors_battery()
            if bat is None:
                return ""
            pct = int(bat.percent)
            status = "charging" if bat.power_plugged else "on battery"
            return f"Battery {pct} percent, {status}. "
        except Exception:
            return ""

    def _time_info(self):
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip("0")
        date_str = now.strftime("%A, %B %d")
        return f"{time_str}. {date_str}. "

    def on_focus(self):
        info = self._time_info() + self._battery_info() + "Press Enter to unlock."
        self.window.update_text("Locked")
        self.speak(info)

    def on_key(self, vk):
        if self.state == "locked_info":
            if vk == win32con.VK_RETURN:
                self.state = "pin_entry"
                self.speak("Enter PIN.")
                self.window.update_text("PIN:")
            elif vk == win32con.VK_ESCAPE:
                self.exit_app()
            return

        if self.state == "pin_entry":
            self._handle_pin(vk)

    def _handle_pin(self, vk):
        if 0x30 <= vk <= 0x39:
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
                        self.window.update_text("PIN:")
        elif vk == win32con.VK_BACK:
            if self.input_pin:
                self.input_pin = self.input_pin[:-1]
                text = "*" * len(self.input_pin) if self.input_pin else "PIN:"
                self.window.update_text(text)
            else:
                self.state = "locked_info"
                self.speak("Cancelled.")
                self.window.update_text("Locked")
        elif vk == win32con.VK_ESCAPE:
            self.state = "locked_info"
            self.speak("Cancelled.")
            self.window.update_text("Locked")

    def _play_unlock(self):
        if os.path.exists(UNLOCK_SOUND):
            AudioPlayer().play_sound_blocking(UNLOCK_SOUND)
        self.speak("Unlocked.")
