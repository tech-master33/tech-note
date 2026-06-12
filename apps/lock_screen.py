import json
import os
import datetime
import win32con
import psutil
from core.app_base import SoftApp
from core.audio_player import AudioPlayer
from core.menu import MenuNode, MenuSystem

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNLOCK_SOUND = os.path.join(BASE, 'sounds', 'unlock.mp3')

STATE_MENU = 0
STATE_PIN = 1

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
        self.state = STATE_MENU
        self.menu = None
        self._build_menu()

    def _build_menu(self):
        root = MenuNode("Locked")
        root.add_child(MenuNode("Time and Date", self._announce_time))
        root.add_child(MenuNode("Battery Level", self._announce_battery))
        root.add_child(MenuNode("Unlock", self._start_pin_entry))
        self.menu = MenuSystem(root, self.speak)

    def _announce_time(self):
        self.speak(self._time_info())

    def _announce_battery(self):
        info = self._battery_info()
        self.speak(info if info else "Battery information unavailable.")

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
        self.state = STATE_MENU
        self.window.update_text("Locked")
        self.speak("Lock Screen. " + self.menu.get_current_item().title)

    def _start_pin_entry(self):
        self.state = STATE_PIN
        self.input_pin = ""
        self.speak("Enter PIN.")
        self.window.update_text("PIN:")

    def on_key(self, vk):
        if self.state == STATE_MENU:
            if vk == win32con.VK_ESCAPE:
                self.exit_app()
                return

            if vk in (win32con.VK_SPACE, win32con.VK_DOWN):
                self.menu.next()
            elif vk in (win32con.VK_BACK, win32con.VK_UP):
                self.menu.previous()
            elif vk == win32con.VK_RETURN:
                self.menu.select()
            elif 0x41 <= vk <= 0x5A:
                self.menu.first_letter_nav(chr(vk))
            
            if self.menu:
                item = self.menu.get_current_item()
                title = item.title if item else self.menu.current_node.title
                self.window.update_text(title)

        elif self.state == STATE_PIN:
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
                self.state = STATE_MENU
                self.speak("Cancelled.")
                self.window.update_text("Locked")
                if self.menu:
                    self.menu.announce_current()
        elif vk == win32con.VK_ESCAPE:
            self.state = STATE_MENU
            self.speak("Cancelled.")
            self.window.update_text("Locked")
            if self.menu:
                self.menu.announce_current()

    def _play_unlock(self):
        if os.path.exists(UNLOCK_SOUND):
            AudioPlayer().play_sound_blocking(UNLOCK_SOUND)
        self.speak("Unlocked.")
