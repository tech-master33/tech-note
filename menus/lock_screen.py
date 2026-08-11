import json
import os
import time
import datetime
import threading
import win32con
import win32api
import psutil
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem, _get_sound_path, SOUNDS_DIR
from core.systmanau import get_audio_manager
from core.config import ACCOUNT_PATH, SETTINGS_PATH, TECH_SOFT

# A failed attempt within this many seconds is announced on focus. The
# attempt time itself is kept in memory only — it is deliberately NOT
# persisted to disk.
RECENT_ATTEMPT_WINDOW = 3600

class LockScreenApp(SoftApp):
    def __init__(self, manager, window, success_callback):
        super().__init__(manager, window)
        self.success_callback = success_callback
        self._load_account()
        self.input_buf = ""
        self.pin_mode = False
        self._attempts = 0
        self._max_attempts = 3
        self._locked_until = 0
        self._lockout_announced = True  # False only while a lockout is active
        self._clock_timer = None
        self._last_failed_attempt = 0  # in-memory only, never persisted
        self._load_time_format()
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
        self.lock_message = self.account.get("lock_message", "")

    def _load_time_format(self):
        self._time_format = "12h"
        if os.path.exists(SETTINGS_PATH):
            try:
                with open(SETTINGS_PATH, 'r') as f:
                    s = json.load(f)
                self._time_format = s.get("time_format", "12h")
            except Exception:
                pass

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

    def _record_failed_attempt(self):
        """Remember the time of this failed unlock attempt (in memory only,
        never written to disk) so the lock screen can surface it."""
        self._last_failed_attempt = time.time()

    def _format_attempt_time(self, ts):
        try:
            dt = datetime.datetime.fromtimestamp(ts)
            if self._time_format == "24h":
                time_str = dt.strftime("%H:%M")
            else:
                time_str = dt.strftime("%I:%M %p").lstrip("0")
            if dt.date() == datetime.datetime.now().date():
                return time_str
            return f"{dt.strftime('%b %d')}, {time_str}"
        except Exception:
            return ""

    def _build_menu(self):
        now = datetime.datetime.now()
        if self._time_format == "24h":
            time_str = now.strftime("%H:%M")
        else:
            time_str = now.strftime("%I:%M %p").lstrip("0")
        date_str = now.strftime("%A, %B %d, %Y")
        root = MenuNode("Lock Screen")
        root.add_child(MenuNode(f"Time: {time_str}"))
        root.add_child(MenuNode(f"Date: {date_str}"))
        if self.lock_message:
            root.add_child(MenuNode(self.lock_message))
        bat = self._battery_text()
        if bat:
            root.add_child(MenuNode(bat))
        if self._last_failed_attempt:
            root.add_child(MenuNode(f"Last failed unlock: {self._format_attempt_time(self._last_failed_attempt)}"))
        if time.time() < self._locked_until:
            remaining = int(self._locked_until - time.time())
            root.add_child(MenuNode(f"Unlock (locked {remaining}s)", lambda: self._locked_warn()))
        else:
            root.add_child(MenuNode("Unlock", self._start_entry))
        self.menu = MenuSystem(root, self.speak)

    def _locked_warn(self):
        remaining = int(self._locked_until - time.time())
        if remaining > 0:
            self.speak(f"Locked for {remaining} more seconds.")
        else:
            self._start_entry()

    def _schedule_clock_update(self):
        if self._clock_timer:
            self._clock_timer.cancel()
        # While locked out, tick once a second so the countdown actually
        # counts down; otherwise refresh the clock once a minute.
        delay = 1.0 if time.time() < self._locked_until else 60.0
        self._clock_timer = threading.Timer(delay, self._clock_tick)
        self._clock_timer.daemon = True
        self._clock_timer.start()

    def _clock_tick(self):
        if time.time() < self._locked_until:
            # Count down in place so the menu keeps its position; rebuild only
            # once the lockout has expired.
            remaining = int(self._locked_until - time.time())
            for child in self.menu.current_node.children:
                if child.title.startswith("Unlock (locked"):
                    child.title = f"Unlock (locked {remaining}s)"
                    break
            self.window.update_text(self._display_text())
        else:
            # Lockout expired (or there never was one): refresh the menu.
            # Announce the end of a lockout exactly once.
            if not self._lockout_announced:
                self._lockout_announced = True
                self.speak("You can now unlock your system.")
            self._build_menu()
            self.window.update_text(self._display_text())
        self._schedule_clock_update()

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
        prefix = ""
        if self._last_failed_attempt and time.time() - self._last_failed_attempt < RECENT_ATTEMPT_WINDOW:
            prefix = (f"Warning: last failed unlock attempt at "
                      f"{self._format_attempt_time(self._last_failed_attempt)}. ")
        self.speak(prefix + "Locked. " + title)
        self._schedule_clock_update()

    def on_key(self, vk):
        if self.pin_mode:
            self._handle_input(vk)
            return

        if vk == win32con.VK_ESCAPE:
            self.speak("Locked.")
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif vk == win32con.VK_BACK:
            self.menu.previous()
            self.window.update_text(self._display_text())

    def on_key_up(self, vk):
        if self.pin_mode:
            return
        if getattr(self.manager, 'space_used_in_chord', False):
            return
        if vk == win32con.VK_SPACE:
            self.menu.next()
            self.window.update_text(self._display_text())

    def _start_entry(self):
        if time.time() < self._locked_until:
            remaining = int(self._locked_until - time.time())
            self.speak(f"Too many attempts. Try again in {remaining} seconds.")
            return
        self.pin_mode = True
        self.input_buf = ""

        # Caps Lock warning
        if win32api.GetKeyState(win32con.VK_CAPITAL) & 1:
            self.speak("Warning: Caps Lock is on.")

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
                char = chr(vk)
                self.input_buf += char
                self.speak("star")
                self.window.update_text("*" * len(self.input_buf))
                if len(self.input_buf) == 4:
                    self._check_pin()
        elif vk == win32con.VK_BACK:
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                self.speak("Deleted")
                text = "*" * len(self.input_buf) if self.input_buf else "PIN:"
                self.window.update_text(text)
            else:
                self._cancel_entry(empty=True)
        elif vk == win32con.VK_SPACE:
            self.speak("Space")
        elif vk == win32con.VK_ESCAPE:
            self._cancel_entry()

    def _check_pin(self):
        if self.input_buf == self.account.get("pin"):
            self._attempts = 0
            self._unlock()
        else:
            self._attempts += 1
            self._record_failed_attempt()
            if self._attempts >= self._max_attempts:
                self._locked_until = time.time() + 30
                self.speak("Too many attempts. Locked for 30 seconds.")
                self.pin_mode = False
                self._build_menu()
                self.window.update_text(self._display_text())
                self._lockout_announced = False
                self._schedule_clock_update()
            else:
                remaining = self._max_attempts - self._attempts
                self.speak(f"Wrong PIN. {remaining} attempt{'s' if remaining != 1 else ''} left.")
                self.input_buf = ""
                self.window.update_text("PIN:")

    def _handle_password(self, vk):
        if vk == win32con.VK_RETURN:
            if self.input_buf == self.account.get("password"):
                self._attempts = 0
                self._unlock()
            else:
                self._attempts += 1
                self._record_failed_attempt()
                if self._attempts >= self._max_attempts:
                    self._locked_until = time.time() + 30
                    self.speak("Too many attempts. Locked for 30 seconds.")
                    self.pin_mode = False
                    self._build_menu()
                    self.window.update_text(self._display_text())
                else:
                    remaining = self._max_attempts - self._attempts
                    self.speak(f"Wrong password. {remaining} attempt{'s' if remaining != 1 else ''} left.")
                    self.input_buf = ""
                    self.window.update_text("Password:")
            return
        if vk == win32con.VK_BACK:
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                self.speak("Deleted")
                self.window.update_text("*" * len(self.input_buf) if self.input_buf else "Password:")
            else:
                self._cancel_entry(empty=True)
            return
        if vk == win32con.VK_ESCAPE:
            self._cancel_entry()
            return
        if vk == win32con.VK_SPACE:
            self.input_buf += " "
            self.speak("Space")
            self.window.update_text("*" * len(self.input_buf))
            return
        ch = self._vk_to_char(vk)
        if ch is not None:
            self.input_buf += ch
            self.speak("star")
            self.window.update_text("*" * len(self.input_buf))

    def _cancel_entry(self, empty=False):
        self.pin_mode = False
        if empty:
            self.speak("Cancelled. Field was empty.")
        else:
            self.speak("Cancelled.")
        self._build_menu()
        self.window.update_text(self._display_text())

    def _unlock(self):
        if self._clock_timer:
            self._clock_timer.cancel()
        # NOTE: resume.json is deliberately NOT deleted here. It carries the
        # crash-recovery / hibernate session state, and load_main_menu reads
        # it after unlock — deleting it here silently discarded that state
        # for every user with a PIN/password.
        self._play_unlock()
        self.success_callback()
        self.exit_app()

    def _play_unlock(self):
        unlock_sound = _get_sound_path('unlock.mp3')
        if not os.path.exists(unlock_sound):
            unlock_sound = os.path.join(SOUNDS_DIR, 'unlock.mp3')
        if os.path.exists(unlock_sound):
            get_audio_manager().play_blocking("ui", unlock_sound)
        self.speak("Unlocked.")
