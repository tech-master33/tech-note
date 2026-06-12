import json
import os
import datetime
import win32con
import psutil
from core.app_base import SoftApp
from core.audio_player import AudioPlayer
from core.config import ACCOUNT_PATH

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNLOCK_SOUND = os.path.join(BASE, 'sounds', 'unlock.mp3')
CLICK_SOUND = os.path.join(BASE, 'sounds', 'clicked.ogg')

class LockScreenApp(SoftApp):
    def __init__(self, manager, window, success_callback):
        super().__init__(manager, window)
        self.success_callback = success_callback
        if os.path.exists(ACCOUNT_PATH):
            try:
                with open(ACCOUNT_PATH, 'r') as f:
                    self.account = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.account = {}
        else:
            self.account = {}
        self.input_pin = ""
        self.pin_mode = False
        self.items = []
        self.index = 0
        self._refresh_items()

    def _battery_text(self):
        try:
            bat = psutil.sensors_battery()
            if bat is None:
                return ""
            pct = int(bat.percent)
            status = "charging" if bat.power_plugged else "on battery"
            return f"Battery {pct}%, {status}"
        except Exception:
            return ""

    def _refresh_items(self):
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip("0")
        date_str = now.strftime("%A, %B %d, %Y")
        self.items = [f"Time: {time_str}", f"Date: {date_str}"]
        bat = self._battery_text()
        if bat:
            self.items.append(bat)
        self.items.append("Unlock")

    def _display_text(self):
        parts = []
        for item in self.items[:-1]:
            parts.append(item)
        if self.items:
            parts.append("---")
            parts.append("> " + self.items[self.index])
        return "\n".join(parts)

    def on_focus(self):
        self.pin_mode = False
        self._refresh_items()
        self.index = 0
        self.window.update_text(self._display_text())
        self.speak("Locked. " + self.items[self.index])

    def on_key(self, vk):
        if self.pin_mode:
            self._handle_pin(vk)
            return

        if vk == win32con.VK_F5:
            self._refresh_items()
            self.speak(" ".join(self.items[:-1]))
        elif vk == win32con.VK_ESCAPE:
            self.speak("Locked.")
        elif vk in (win32con.VK_SPACE, win32con.VK_DOWN):
            self.index = (self.index + 1) % len(self.items)
            self.window.update_text(self._display_text())
            self.speak(self.items[self.index])
        elif vk in (win32con.VK_BACK, win32con.VK_UP):
            self.index = (self.index - 1) % len(self.items)
            self.window.update_text(self._display_text())
            self.speak(self.items[self.index])
        elif vk == win32con.VK_RETURN:
            if os.path.exists(CLICK_SOUND):
                AudioPlayer().play_file(CLICK_SOUND)
            if self.items[self.index] == "Unlock":
                self._start_pin_entry()

    def _start_pin_entry(self):
        self.pin_mode = True
        self.input_pin = ""
        self.speak("Enter PIN.")
        self.window.update_text("PIN:")

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
                self.pin_mode = False
                self.speak("Cancelled.")
                self.index = 0
                self._refresh_items()
                self.window.update_text(self._display_text())
        elif vk == win32con.VK_ESCAPE:
            self.pin_mode = False
            self.speak("Cancelled.")
            self.index = 0
            self._refresh_items()
            self.window.update_text(self._display_text())

    def _play_unlock(self):
        if os.path.exists(UNLOCK_SOUND):
            AudioPlayer().play_sound_blocking(UNLOCK_SOUND)
        self.speak("Unlocked.")
