import json
import os
import datetime
import win32con
import win32api
import psutil
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.audio_player import AudioPlayer
from core.config import ACCOUNT_PATH

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNLOCK_SOUND = os.path.join(BASE, 'sounds', 'unlock.mp3')

class LockScreenApp(SoftApp):
    def __init__(self, manager, window, success_callback):
        super().__init__(manager, window)
        self.success_callback = success_callback
        self._load_account()
        self.input_buf = ""
        self.pin_mode = False
        self._build_menu()

    def _load_account(self):
        if os.path.exists(ACCOUNT_PATH):
            try:
                with open(ACCOUNT_PATH, 'r') as f:
                    self.account = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.account = {}
        else:
            self.account = {}
        self.lock_type = self.account.get("lock_type", "pin")

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

    def _build_menu(self):
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip("0")
        date_str = now.strftime("%A, %B %d, %Y")
        root = MenuNode("Lock Screen")
        root.add_child(MenuNode(f"Time: {time_str}"))
        root.add_child(MenuNode(f"Date: {date_str}"))
        bat = self._battery_text()
        if bat:
            root.add_child(MenuNode(bat))
        root.add_child(MenuNode("Unlock", self._start_entry))
        self.menu = MenuSystem(root, self.speak)

    def _display_text(self):
        children = self.menu.current_node.children
        items = [c.title for c in children]
        idx = self.menu.current_index
        parts = items[:-1]
        parts.append("---")
        parts.append("> " + items[idx])
        return "\n".join(parts)

    def on_focus(self):
        self.pin_mode = False
        self._build_menu()
        item = self.menu.get_current_item()
        title = item.title if item else "Lock Screen"
        self.window.update_text(self._display_text())
        self.speak("Locked. " + title)

    def on_key(self, vk):
        if self.pin_mode:
            self._handle_input(vk)
            return

        if vk == win32con.VK_F5:
            self._build_menu()
            titles = [c.title for c in self.menu.current_node.children[:-2]]
            self.speak(" ".join(titles))
            self.window.update_text(self._display_text())
        elif vk == win32con.VK_ESCAPE:
            self.speak("Locked.")
        elif vk in (win32con.VK_SPACE, win32con.VK_DOWN):
            self.menu.next()
            self.window.update_text(self._display_text())
        elif vk in (win32con.VK_BACK, win32con.VK_UP):
            self.menu.previous()
            self.window.update_text(self._display_text())
        elif vk == win32con.VK_RETURN:
            self.menu.select()

    def _start_entry(self):
        self.pin_mode = True
        self.input_buf = ""
        if self.lock_type == "pin":
            self.speak("Enter PIN.")
            self.window.update_text("PIN:")
        else:
            self.speak("Enter password.")
            self.window.update_text("Password:")

    def _handle_input(self, vk):
        if self.lock_type == "pin":
            self._handle_pin(vk)
        else:
            self._handle_password(vk)

    def _handle_pin(self, vk):
        if 0x30 <= vk <= 0x39:
            if len(self.input_buf) < 4:
                self.input_buf += chr(vk)
                self.window.update_text("*" * len(self.input_buf))
                if len(self.input_buf) == 4:
                    self._check_pin()
        elif vk == win32con.VK_BACK:
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                text = "*" * len(self.input_buf) if self.input_buf else "PIN:"
                self.window.update_text(text)
            else:
                self._cancel_entry()
        elif vk == win32con.VK_ESCAPE:
            self._cancel_entry()

    def _check_pin(self):
        if self.input_buf == self.account.get("pin"):
            self._unlock()
        else:
            self.speak("Wrong PIN.")
            self.input_buf = ""
            self.window.update_text("PIN:")

    def _handle_password(self, vk):
        if vk == win32con.VK_RETURN:
            if self.input_buf == self.account.get("password"):
                self._unlock()
            else:
                self.speak("Wrong password.")
                self.input_buf = ""
                self.window.update_text("Password:")
            return
        if vk == win32con.VK_BACK:
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                self.window.update_text("*" * len(self.input_buf) if self.input_buf else "Password:")
            else:
                self._cancel_entry()
            return
        if vk == win32con.VK_ESCAPE:
            self._cancel_entry()
            return
        ch = self._vk_to_char(vk)
        if ch is not None:
            self.input_buf += ch
            self.window.update_text("*" * len(self.input_buf))

    def _vk_to_char(self, vk):
        shift = win32api.GetAsyncKeyState(win32con.VK_SHIFT) & 0x8000
        caps = win32api.GetAsyncKeyState(win32con.VK_CAPITAL) & 1
        if 0x41 <= vk <= 0x5A:
            upper = shift ^ caps
            return chr(vk).upper() if upper else chr(vk).lower()
        if 0x30 <= vk <= 0x39:
            return chr(vk) if not shift else chr(vk)
        if vk == win32con.VK_SPACE:
            return ' '
        sym_map = {
            0xBD: '-', 0xBB: '=', 0xC0: '`',
            0xDB: '[', 0xDD: ']', 0xDC: '\\', 0xBA: ';', 0xDE: "'",
            0xBC: ',', 0xBE: '.', 0xBF: '/',
        }
        if vk in sym_map:
            return sym_map[vk] if not shift else sym_map.get(vk, '')
        return None

    def _cancel_entry(self):
        self.pin_mode = False
        self.speak("Cancelled.")
        self._build_menu()
        self.menu.current_index = 0
        self.window.update_text(self._display_text())

    def _unlock(self):
        self._play_unlock()
        self.success_callback()
        self.exit_app()

    def _play_unlock(self):
        if os.path.exists(UNLOCK_SOUND):
            AudioPlayer().play_sound_blocking(UNLOCK_SOUND)
        self.speak("Unlocked.")
