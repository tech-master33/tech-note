import json
import os
import win32con
import win32api
from core.app_base import SoftApp
from core.config import ACCOUNT_PATH

TOTAL_STEPS = 9

class TechNoteSetup(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.finish_callback = None
        self.current_step = 0
        self.username = ""
        self.password = ""
        self.pin = ""
        self._pin_original = ""
        self._pw_original = ""
        self.lock_type = "pin"
        self.keyboard_layout = self._detect_windows_layout()
        self.time_format = "12-hour"
        self.voice_index = 0
        self.voice_names = []
        self._load_voices()
        self.active = True

    def _load_voices(self):
        try:
            from synths.sapi_synth import SapiSynthBase
            tmp = SapiSynthBase()
            self.voice_names = tmp.get_voice_names()
        except Exception:
            self.voice_names = ["Default"]

    def _detect_windows_layout(self):
        try:
            hkl = win32api.GetKeyboardLayout(0)
            lang_id = hkl & 0xFFFF
            primary_lang = lang_id & 0x3FF
            if primary_lang == 0x01:
                return "Arabic"
            elif lang_id == 0x0809:
                return "UK"
            return "US"
        except Exception:
            return "US"

    def _step_label(self, step_name):
        return f"Step {self.current_step + 1} of {TOTAL_STEPS}. {step_name}"

    def run_setup(self):
        self.window.update_text("TechNote Setup")
        lines = [
            "Welcome to TechNote",
            "",
            "A self-voicing keyboard interface for Windows.",
            "",
            "Navigation: Space = next, Backspace = previous",
            "Enter = select, Escape = back or exit",
            "",
            "Press Enter to begin setup."
        ]
        self.window.update_text("\n".join(lines))
        self.speak("Welcome to TechNote. A self voicing keyboard interface for Windows. Use Space and Backspace to navigate, Enter to select. Press Enter to begin setup.")

    def on_key(self, vk):
        if self.current_step == 0:
            if vk == win32con.VK_RETURN:
                self.current_step += 1
                self.speak(self._step_label("Enter username."))
                self.window.update_text("Username:")

        elif self.current_step == 1:
            if vk == win32con.VK_ESCAPE:
                self.current_step = 0
                self.run_setup()
                return
            if vk == win32con.VK_RETURN:
                if self.username:
                    self.current_step += 1
                    self.speak(self._step_label("Select Lock Type. Use Space or Backspace. PIN or Password."))
                    self.window.update_text("Lock Type: PIN")
            elif self._handle_input(vk, 'username'):
                pass

        elif self.current_step == 2:
            if vk == win32con.VK_ESCAPE:
                self.current_step = 1
                self.speak(self._step_label("Enter username."))
                self.window.update_text(f"Username: {self.username}")
                return
            lock_options = ["PIN", "Password"]
            current_lock = 0 if self.lock_type == "pin" else 1
            if vk in (win32con.VK_SPACE,):
                current_lock = (current_lock + 1) % 2
                self.lock_type = "pin" if current_lock == 0 else "password"
                self.window.update_text("Lock Type: " + lock_options[current_lock])
                self.speak(lock_options[current_lock])
            elif vk in (win32con.VK_BACK,):
                current_lock = (current_lock - 1) % 2
                self.lock_type = "pin" if current_lock == 0 else "password"
                self.window.update_text("Lock Type: " + lock_options[current_lock])
                self.speak(lock_options[current_lock])
            elif vk == win32con.VK_RETURN:
                self.current_step += 1
                if self.lock_type == "pin":
                    self.speak(self._step_label("Enter 4 digit PIN."))
                    self.window.update_text("PIN:")
                else:
                    self.speak(self._step_label("Enter login password."))
                    self.window.update_text("Password:")

        elif self.current_step == 3:
            if vk == win32con.VK_ESCAPE:
                self.current_step = 2
                lock_options = ["PIN", "Password"]
                current_lock = 0 if self.lock_type == "pin" else 1
                self.speak(self._step_label("Select Lock Type."))
                self.window.update_text("Lock Type: " + lock_options[current_lock])
                return
            if self.lock_type == "pin":
                if 0x30 <= vk <= 0x39:
                    self.pin += chr(vk)
                    self.window.update_text("*" * len(self.pin))
                    if len(self.pin) == 4:
                        self._pin_original = self.pin
                        self.pin = ""
                        self.current_step = 4
                        self.speak(self._step_label("Confirm your PIN."))
                        self.window.update_text("Confirm PIN:")
                elif vk == win32con.VK_BACK:
                    if self.pin:
                        self.pin = self.pin[:-1]
                        self.window.update_text("*" * len(self.pin) if self.pin else "PIN:")
            else:
                if vk == win32con.VK_RETURN:
                    if self.password:
                        self._pw_original = self.password
                        self.password = ""
                        self.current_step = 4
                        self.speak(self._step_label("Confirm your password."))
                        self.window.update_text("Confirm Password:")
                elif self._handle_input(vk, 'password', hidden=True):
                    pass

        elif self.current_step == 4:
            if vk == win32con.VK_ESCAPE:
                self.current_step = 3
                self.pin = ""
                self.password = ""
                if self.lock_type == "pin":
                    self.speak(self._step_label("Enter 4 digit PIN."))
                    self.window.update_text("PIN:")
                else:
                    self.speak(self._step_label("Enter login password."))
                    self.window.update_text("Password:")
                return
            if self.lock_type == "pin":
                if 0x30 <= vk <= 0x39:
                    self.pin += chr(vk)
                    self.window.update_text("*" * len(self.pin))
                    if len(self.pin) == 4:
                        if self.pin == self._pin_original:
                            self.pin = self._pin_original
                            self._enter_layout_step()
                        else:
                            self.speak("PINs don't match. Try again.")
                            self.pin = ""
                            self.current_step = 3
                            if self.lock_type == "pin":
                                self.window.update_text("PIN:")
                            else:
                                self.window.update_text("Password:")
                elif vk == win32con.VK_BACK:
                    if self.pin:
                        self.pin = self.pin[:-1]
                        self.window.update_text("*" * len(self.pin) if self.pin else "Confirm PIN:")
            else:
                if vk == win32con.VK_RETURN:
                    if self.password:
                        if self.password == self._pw_original:
                            self.password = self._pw_original
                            self._enter_layout_step()
                        else:
                            self.speak("Passwords don't match. Try again.")
                            self.password = ""
                            self.current_step = 3
                            self.window.update_text("Password:")
                elif self._handle_input(vk, 'password', hidden=True):
                    pass

        elif self.current_step == 5:
            if vk == win32con.VK_ESCAPE:
                self.current_step = 4
                self.pin = ""
                self.password = ""
                if self.lock_type == "pin":
                    self.speak(self._step_label("Confirm your PIN."))
                    self.window.update_text("Confirm PIN:")
                else:
                    self.speak(self._step_label("Confirm your password."))
                    self.window.update_text("Confirm Password:")
                return
            if vk == win32con.VK_SPACE:
                self._layout_index = (self._layout_index + 1) % len(self._layout_options)
                self.keyboard_layout = self._layout_options[self._layout_index]
                self.window.update_text("Keyboard Layout: " + self.keyboard_layout)
                self.speak(self.keyboard_layout)
            elif vk == win32con.VK_BACK:
                self._layout_index = (self._layout_index - 1) % len(self._layout_options)
                self.keyboard_layout = self._layout_options[self._layout_index]
                self.window.update_text("Keyboard Layout: " + self.keyboard_layout)
                self.speak(self.keyboard_layout)
            elif vk == win32con.VK_RETURN:
                self._enter_time_format_step()

        elif self.current_step == 6:
            if vk == win32con.VK_ESCAPE:
                self.current_step = 5
                self.speak(self._step_label("Keyboard layout. Use Space or Backspace."))
                self.window.update_text("Keyboard Layout: " + self.keyboard_layout)
                return
            if vk == win32con.VK_SPACE:
                self.time_format = "24-hour" if self.time_format == "12-hour" else "12-hour"
                self.window.update_text("Time Format: " + self.time_format)
                self.speak(self.time_format)
            elif vk == win32con.VK_BACK:
                self.time_format = "24-hour" if self.time_format == "12-hour" else "12-hour"
                self.window.update_text("Time Format: " + self.time_format)
                self.speak(self.time_format)
            elif vk == win32con.VK_RETURN:
                self._enter_voice_step()

        elif self.current_step == 7:
            if vk == win32con.VK_ESCAPE:
                self.current_step = 6
                self.speak(self._step_label("Time format. Use Space or Backspace to change."))
                self.window.update_text("Time Format: " + self.time_format)
                return
            if vk == win32con.VK_SPACE:
                self.voice_index = (self.voice_index + 1) % len(self.voice_names)
                self._preview_voice()
            elif vk == win32con.VK_BACK:
                self.voice_index = (self.voice_index - 1) % len(self.voice_names)
                self._preview_voice()
            elif vk == win32con.VK_RETURN:
                self._complete_setup()

        elif self.current_step in (8, 9):
            if vk == win32con.VK_RETURN:
                self.active = False
                if self.finish_callback:
                    self.finish_callback()

    def _enter_layout_step(self):
        self._layout_options = ["US", "UK", "Arabic"]
        self._layout_index = self._layout_options.index(self.keyboard_layout) if self.keyboard_layout in self._layout_options else 0
        self.current_step = 5
        self.speak(self._step_label(f"Keyboard layout detected: {self.keyboard_layout}. Use Space or Backspace to change."))
        self.window.update_text("Keyboard Layout: " + self.keyboard_layout)

    def _enter_time_format_step(self):
        self.current_step = 6
        self.speak(self._step_label(f"Time format. Current: {self.time_format}. Use Space or Backspace to change."))
        self.window.update_text("Time Format: " + self.time_format)

    def _enter_voice_step(self):
        self.current_step = 7
        if self.voice_names:
            name = self.voice_names[self.voice_index] if self.voice_index < len(self.voice_names) else "Default"
            self.speak(self._step_label(f"Voice: {name}. Use Space or Backspace to change, Enter to preview."))
            self.window.update_text("Voice: " + name)
        else:
            self.speak(self._step_label("No voices found. Press Enter to continue."))
            self.window.update_text("Voice: none")

    def _preview_voice(self):
        if not self.voice_names:
            return
        idx = min(self.voice_index, len(self.voice_names) - 1)
        try:
            if hasattr(self.manager.synth, 'set_voice_by_index'):
                self.manager.synth.set_voice_by_index(idx)
        except Exception:
            pass
        total = len(self.voice_names)
        name = self.voice_names[idx]
        self.speak(f"Voice {idx + 1} of {total}: {name}.")
        self.window.update_text("Voice: " + name)
        try:
            self.manager.synth.speak(f"Preview.")
        except Exception:
            pass

    def _complete_setup(self):
        self._save_settings()
        self.save_account()
        self.current_step = 9
        voice_name = self.voice_names[self.voice_index] if self.voice_names else "Default"
        lines = [
            "Setup Complete!",
            "",
            f"Username: {self.username}",
            f"Lock: {self.lock_type.upper()}",
            f"Layout: {self.keyboard_layout}",
            f"Time: {self.time_format}",
            f"Voice: {voice_name}",
            "",
            "Press Enter to start TechNote."
        ]
        self.window.update_text("\n".join(lines))
        summary_parts = [f"Username {self.username}", f"lock type {self.lock_type}", f"keyboard {self.keyboard_layout}", f"time {self.time_format}", f"voice {voice_name}"]
        self.speak(f"Setup complete. {', '.join(summary_parts)}. Press Enter to start.")

    def _handle_input(self, vk, attr, hidden=False):
        val = getattr(self, attr)
        if vk == win32con.VK_BACK:
            if val:
                val = val[:-1]
                setattr(self, attr, val)
                display = "*" * len(val) if hidden else val
                self.window.update_text(display if display else attr.capitalize() + ":")
            return True
        ch = self._vk_to_char(vk)
        if ch:
            val += ch
            setattr(self, attr, val)
            display = "*" * len(val) if hidden else val
            self.window.update_text(display)
            if not hidden: self.speak(ch)
            return True
        return False

    def save_account(self):
        config = {
            "username": self.username,
            "password": self.password,
            "pin": self.pin,
            "lock_type": self.lock_type,
        }
        os.makedirs(os.path.dirname(ACCOUNT_PATH), exist_ok=True)
        with open(ACCOUNT_PATH, 'w') as f:
            json.dump(config, f)
        self.speak("Account saved.")

    def _save_settings(self):
        settings_path = os.path.join(os.path.dirname(ACCOUNT_PATH), 'settings.json')
        try:
            s = {}
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    s = json.load(f)
            s["keyboard_layout"] = self.keyboard_layout
            s["time_format"] = self.time_format
            s["voice_index"] = self.voice_index
            with open(settings_path, 'w') as f:
                json.dump(s, f)
        except Exception:
            pass
