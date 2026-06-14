import json
import os
import win32con
import win32api
from core.app_base import SoftApp
from core.config import ACCOUNT_PATH
from synths.registry import get_available_synths, create_synth

class TechNoteSetup(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.finish_callback = None
        self.available_synths = get_available_synths()
        self.synth_index = 0
        self.synth_module = "sapi_synth"
        self.voices = []
        self.voice_index = 0
        self.current_step = 0
        self.username = ""
        self.password = ""
        self.pin = ""
        self.lock_type = "pin"
        self.keyboard_layout = "US"
        self.active = True

    def _load_voices_for_synth(self):
        inst = create_synth(self.synth_module)
        if inst and hasattr(inst, 'get_voice_names'):
            self.voices = inst.get_voice_names()
            self.voice_index = 0
        else:
            self.voices = []

    def run_setup(self):
        self.window.update_text("TechNote Setup")
        self.speak("Welcome to TechNote. Press Enter to begin.")

    def on_key(self, vk):
        if self.current_step == 0:
            if vk == win32con.VK_RETURN:
                self.current_step += 1
                self.speak("Enter username.")
                self.window.update_text("Username:")

        elif self.current_step == 1:
            if vk == win32con.VK_RETURN:
                if self.username:
                    self.current_step += 1
                    self.speak("Select Lock Type. Use arrows. PIN or Password.")
                    self.window.update_text("Lock Type: PIN")
            elif self._handle_input(vk, 'username'):
                pass

        elif self.current_step == 2:
            lock_options = ["PIN", "Password"]
            current_lock = 0 if self.lock_type == "pin" else 1
            if vk in (win32con.VK_SPACE):
                current_lock = (current_lock + 1) % 2
                self.lock_type = "pin" if current_lock == 0 else "password"
                self.window.update_text("Lock Type: " + lock_options[current_lock])
                self.speak(lock_options[current_lock])
            elif vk in (win32con.VK_BACK): # Allow backspace if empty? No, keep it simple.
                current_lock = (current_lock - 1) % 2
                self.lock_type = "pin" if current_lock == 0 else "password"
                self.window.update_text("Lock Type: " + lock_options[current_lock])
                self.speak(lock_options[current_lock])
            elif vk == win32con.VK_RETURN:
                self.current_step += 1
                if self.lock_type == "pin":
                    self.speak("Enter 4 digit PIN.")
                    self.window.update_text("PIN:")
                else:
                    self.speak("Enter login password.")
                    self.window.update_text("Password:")

        elif self.current_step == 3:
            if self.lock_type == "pin":
                if 0x30 <= vk <= 0x39:
                    self.pin += chr(vk)
                    self.window.update_text("*" * len(self.pin))
                    if len(self.pin) == 4:
                        self.current_step += 1
                        self._enter_synth_step()
                elif vk == win32con.VK_BACK:
                    if self.pin:
                        self.pin = self.pin[:-1]
                        self.window.update_text("*" * len(self.pin) if self.pin else "PIN:")
            else:
                if vk == win32con.VK_RETURN:
                    if self.password:
                        self.current_step += 1
                        self._enter_synth_step()
                elif self._handle_input(vk, 'password', hidden=True):
                    pass

        elif self.current_step == 4:
            if not self.available_synths:
                return
            if vk in (win32con.VK_SPACE):
                self.synth_index = (self.synth_index + 1) % len(self.available_synths)
                self.window.update_text(self.available_synths[self.synth_index][0])
                self.speak(self.available_synths[self.synth_index][0])
            elif vk in (win32con.VK_BACK):
                self.synth_index = (self.synth_index - 1) % len(self.available_synths)
                self.window.update_text(self.available_synths[self.synth_index][0])
                self.speak(self.available_synths[self.synth_index][0])
            elif vk == win32con.VK_RETURN:
                self.synth_module = self.available_synths[self.synth_index][1]
                self._load_voices_for_synth()
                self.current_step += 1
                if self.voices:
                    self.speak("Voice selection. Use arrows.")
                    self.window.update_text(self.voices[self.voice_index])
                else:
                    self._complete_setup()

        elif self.current_step == 5:
            if not self.voices:
                self._enter_layout_step()
                return
            if vk in (win32con.VK_SPACE):
                self.voice_index = (self.voice_index + 1) % len(self.voices)
                self.window.update_text(self.voices[self.voice_index])
                self.speak(self.voices[self.voice_index])
            elif vk in (win32con.VK_BACK):
                if self.voices:
                    self.voice_index = (self.voice_index - 1) % len(self.voices)
                    self.window.update_text(self.voices[self.voice_index])
                    self.speak(self.voices[self.voice_index])
            elif vk == win32con.VK_RETURN:
                self._enter_layout_step()

        elif self.current_step == 6:
            layout_options = ["US", "UK"]
            current = 0 if self.keyboard_layout == "US" else 1
            if vk in (win32con.VK_SPACE):
                current = (current + 1) % 2
                self.keyboard_layout = layout_options[current]
                self.window.update_text("Keyboard Layout: " + self.keyboard_layout)
                self.speak(self.keyboard_layout)
            elif vk in (win32con.VK_BACK):
                current = (current - 1) % 2
                self.keyboard_layout = layout_options[current]
                self.window.update_text("Keyboard Layout: " + self.keyboard_layout)
                self.speak(self.keyboard_layout)
            elif vk == win32con.VK_RETURN:
                self._complete_setup()

        elif self.current_step == 7:
            if vk == win32con.VK_RETURN:
                self.active = False
                if self.finish_callback:
                    self.finish_callback()

    def _enter_synth_step(self):
        self.speak("TTS engine. Use arrows to select.")
        if self.available_synths:
            self.window.update_text(self.available_synths[self.synth_index][0])

    def _enter_layout_step(self):
        self.current_step = 6
        self.speak("Keyboard layout. Use arrows to select. US or UK.")
        self.window.update_text("Keyboard Layout: " + self.keyboard_layout)

    def _complete_setup(self):
        self.save_account()
        self.current_step = 7
        self.speak("Setup complete. Press Enter to start.")
        self.window.update_text("Setup Complete")

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

    def _vk_to_char(self, vk):
        shift = win32api.GetAsyncKeyState(win32con.VK_SHIFT) & 0x8000
        if 0x41 <= vk <= 0x5A:
            return chr(vk).upper() if shift else chr(vk).lower()
        if 0x30 <= vk <= 0x39:
            return chr(vk)
        if vk == win32con.VK_SPACE:
            return ' '
        return None

    def save_account(self):
        config = {
            "username": self.username,
            "password": self.password,
            "pin": self.pin,
            "lock_type": self.lock_type,
            "synth_module": self.synth_module,
            "default_synth": self.voices[self.voice_index] if self.voices else "Default"
        }
        os.makedirs(os.path.dirname(ACCOUNT_PATH), exist_ok=True)
        with open(ACCOUNT_PATH, 'w') as f:
            json.dump(config, f)
        self._save_keyboard_layout()
        self.speak("Account saved.")

    def _save_keyboard_layout(self):
        settings_path = os.path.join(os.path.dirname(ACCOUNT_PATH), 'settings.json')
        try:
            s = {}
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    s = json.load(f)
            s["keyboard_layout"] = self.keyboard_layout
            with open(settings_path, 'w') as f:
                json.dump(s, f)
        except Exception:
            pass
