import os
import json
import subprocess
import sys
import win32con
from core.app_base import SoftApp
from core.config import TECH_SOFT, ACCOUNT_PATH, SETTINGS_PATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class SettingsApp(SoftApp):
    def __init__(self, manager, window, on_reset_account=None):
        super().__init__(manager, window)
        self.on_reset_account = on_reset_account
        self.settings_file = SETTINGS_PATH
        self.settings = {"voice_speed": 100, "theme": "Dark"}
        self.load_settings()
        self.options = ["Account", "Theme", "Check for Updates", "About Tech-Note", "Reset TechNote"]
        self.index = 0
        self.pin_mode = None
        self.confirm_mode = None
        self.account_mode = None
        self.account_index = 0
        self.account_options = ["Change Username", "Change Password", "Change PIN", "Back"]
        self.text_input = ""
        self.text_input_label = ""

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    self.settings = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.settings = {"voice_speed": 100, "theme": "Dark"}

    def save_settings(self):
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f)

    def _load_account(self):
        if os.path.exists(ACCOUNT_PATH):
            try:
                with open(ACCOUNT_PATH, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_account(self, account):
        with open(ACCOUNT_PATH, 'w') as f:
            json.dump(account, f)

    def on_focus(self):
        self.speak(f"Settings. {self.options[self.index]}")
        self.window.update_text("Settings: " + self.options[self.index])

    def on_key(self, vk):
        if self.pin_mode:
            self._handle_pin_input(vk)
            return

        if self.account_mode == "input":
            self._handle_text_input(vk)
            return

        if self.confirm_mode:
            if vk == win32con.VK_RETURN:
                self._do_reset_technote()
            elif vk == win32con.VK_ESCAPE:
                self.confirm_mode = None
                self.speak("Cancelled.")
                self.window.update_text("Settings: " + self.options[self.index])
            return

        if self.account_mode == "menu":
            self._handle_account_menu(vk)
            return

        if vk == win32con.VK_ESCAPE:
            self.exit_app()
        elif vk in (win32con.VK_BACK, win32con.VK_UP):
            self.index = (self.index - 1) % len(self.options)
            self.speak(self.options[self.index])
            self.window.update_text("Settings: " + self.options[self.index])
        elif vk in (win32con.VK_DOWN, win32con.VK_SPACE):
            self.index = (self.index + 1) % len(self.options)
            self.speak(self.options[self.index])
            self.window.update_text("Settings: " + self.options[self.index])
        elif vk == win32con.VK_RETURN:
            self._select_current()

    def _select_current(self):
        key = self.options[self.index].lower().replace(' ', '_')
        if key == "account":
            self._enter_account_menu()
        elif key == "theme":
            current = self.settings.get("theme", "Dark")
            self.settings["theme"] = "Light" if current == "Dark" else "Dark"
            self.save_settings()
            self.speak(f"Theme set to {self.settings['theme']}")
        elif key == "about_tech-note":
            self.speak("Tech-Note. A self voicing keyboard driven interface for Windows.")
            self.window.update_text("Tech-Note v1.0")
        elif key == "check_for_updates":
            self._check_for_updates()
        elif key == "reset_technote":
            self._reset_technote()

    def _enter_account_menu(self):
        self.account_mode = "menu"
        self.account_index = 0
        self.speak("Account: " + self.account_options[self.account_index])
        self.window.update_text("Account: " + self.account_options[self.account_index])

    def _handle_account_menu(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.account_mode = None
            self.speak(self.options[self.index])
            self.window.update_text("Settings: " + self.options[self.index])
            return
        if vk in (win32con.VK_BACK, win32con.VK_UP):
            self.account_index = (self.account_index - 1) % len(self.account_options)
            self.speak(self.account_options[self.account_index])
            self.window.update_text("Account: " + self.account_options[self.account_index])
        elif vk in (win32con.VK_DOWN, win32con.VK_SPACE):
            self.account_index = (self.account_index + 1) % len(self.account_options)
            self.speak(self.account_options[self.account_index])
            self.window.update_text("Account: " + self.account_options[self.account_index])
        elif vk == win32con.VK_RETURN:
            self._select_account_option()

    def _select_account_option(self):
        option = self.account_options[self.account_index]
        if option == "Back":
            self.account_mode = None
            self.speak(self.options[self.index])
            self.window.update_text("Settings: " + self.options[self.index])
        elif option == "Change Username":
            self._start_text_input("username", "Enter new username.")
        elif option == "Change Password":
            self._start_text_input("password", "Enter new password.")
        elif option == "Change PIN":
            self._start_pin_reset()

    def _start_text_input(self, field, prompt):
        self.account_mode = "input"
        self.text_input_field = field
        self.text_input = ""
        self.text_input_label = field.capitalize()
        self.speak(prompt)
        self.window.update_text(f"{self.text_input_label}: ")

    def _handle_text_input(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.account_mode = "menu"
            self.speak(self.account_options[self.account_index])
            self.window.update_text("Account: " + self.account_options[self.account_index])
            return
        if vk == win32con.VK_RETURN:
            val = self.text_input.strip()
            if not val:
                self.speak("Cannot be empty.")
                return
            account = self._load_account()
            if self.text_input_field == "username":
                account["username"] = val
                self._save_account(account)
                self.speak(f"Username changed to {val}.")
            elif self.text_input_field == "password":
                account["password"] = val
                self._save_account(account)
                self.speak("Password updated.")
            self.text_input = ""
            self.account_mode = "menu"
            self.speak(self.account_options[self.account_index])
            self.window.update_text("Account: " + self.account_options[self.account_index])
            return
        if vk == win32con.VK_BACK:
            if self.text_input:
                self.text_input = self.text_input[:-1]
                self.window.update_text(self.text_input if self.text_input else " ")
            return
        ch = self._vk_to_char(vk)
        if ch is not None:
            self.text_input += ch
            self.window.update_text(self.text_input)

    def _vk_to_char(self, vk):
        import win32api
        shift = win32api.GetAsyncKeyState(win32con.VK_SHIFT) & 0x8000
        caps = win32api.GetAsyncKeyState(win32con.VK_CAPITAL) & 1
        if 0x41 <= vk <= 0x5A:
            upper = shift ^ caps
            return chr(vk).upper() if upper else chr(vk).lower()
        if 0x30 <= vk <= 0x39:
            shift_syms = {0x30: ')', 0x31: '!', 0x32: '@', 0x33: '#',
                          0x34: '$', 0x35: '%', 0x36: '^', 0x37: '&',
                          0x38: '*', 0x39: '('}
            return shift_syms[vk] if shift else chr(vk)
        if vk == win32con.VK_SPACE:
            return ' '
        sym_map = {
            0xBD: ('-', '_'), 0xBB: ('=', '+'), 0xC0: ('`', '~'),
            0xDB: ('[', '{'), 0xDD: (']', '}'), 0xDC: ('\\', '|'),
            0xBA: (';', ':'), 0xDE: ("'", '"'),
            0xBC: (',', '<'), 0xBE: ('.', '>'), 0xBF: ('/', '?'),
        }
        if vk in sym_map:
            return sym_map[vk][1] if shift else sym_map[vk][0]
        return None

    def _check_for_updates(self):
        self.speak("Checking for updates. Please wait.")
        self.window.update_text("Updating...")
        try:
            result = subprocess.run(
                ["git", "pull"], cwd=BASE_DIR,
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                out = result.stdout.strip()
                if "Already up to date" in out:
                    self.speak("Already up to date.")
                else:
                    self.speak("Update downloaded.")
                    self._install_requirements()
            else:
                self.speak("Update failed. Check your internet.")
        except subprocess.TimeoutExpired:
            self.speak("Update timed out.")
        except FileNotFoundError:
            self.speak("Git not found.")
        except Exception:
            self.speak("Update error.")
        self.window.update_text("Settings: " + self.options[self.index])

    def _install_requirements(self):
        req_path = os.path.join(BASE_DIR, 'requirements.txt')
        if not os.path.exists(req_path):
            return
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", req_path],
                cwd=BASE_DIR, capture_output=True, text=True, timeout=120
            )
            self.speak("Requirements updated.")
        except Exception:
            self.speak("Failed to update requirements.")

    def _start_pin_reset(self):
        if not os.path.exists(ACCOUNT_PATH):
            self.speak("No account found. Nothing to reset.")
            return
        self.pin_mode = "confirm_pin"
        self.new_pin = ""
        self.speak("Enter current PIN.")
        self.window.update_text("Current PIN: ")

    def _handle_pin_input(self, vk):
        if self.pin_mode == "confirm_pin":
            self._handle_confirm_pin(vk)
        elif self.pin_mode == "reset_pin":
            self._handle_new_pin(vk)

    def _handle_confirm_pin(self, vk):
        if 0x30 <= vk <= 0x39:
            self.new_pin += chr(vk)
            self.window.update_text("*" * len(self.new_pin))
            if len(self.new_pin) == 4:
                self._verify_old_pin()
        elif vk == win32con.VK_BACK:
            if self.new_pin:
                self.new_pin = self.new_pin[:-1]
                self.window.update_text("*" * len(self.new_pin) if self.new_pin else "Current PIN: ")
            else:
                self.pin_mode = None
                self.speak("Cancelled.")
                self._return_from_pin()
        elif vk == win32con.VK_ESCAPE:
            self.pin_mode = None
            self.speak("Cancelled.")
            self._return_from_pin()

    def _verify_old_pin(self):
        try:
            with open(ACCOUNT_PATH, 'r') as f:
                account = json.load(f)
            if self.new_pin == account.get("pin", ""):
                self.pin_mode = "reset_pin"
                self.new_pin = ""
                self.speak("Enter new 4 digit PIN.")
                self.window.update_text("New PIN: ")
            else:
                self.speak("Wrong PIN.")
                self.pin_mode = None
                self._return_from_pin()
        except Exception:
            self.speak("Failed to read account.")
            self.pin_mode = None
            self._return_from_pin()

    def _handle_new_pin(self, vk):
        if 0x30 <= vk <= 0x39:
            self.new_pin += chr(vk)
            self.window.update_text("*" * len(self.new_pin))
            if len(self.new_pin) == 4:
                self._save_new_pin()
        elif vk == win32con.VK_BACK:
            if self.new_pin:
                self.new_pin = self.new_pin[:-1]
                self.window.update_text("*" * len(self.new_pin) if self.new_pin else "New PIN: ")
            else:
                self.pin_mode = None
                self.speak("Cancelled.")
                self._return_from_pin()
        elif vk == win32con.VK_ESCAPE:
            self.pin_mode = None
            self.speak("Cancelled.")
            self._return_from_pin()

    def _save_new_pin(self):
        try:
            with open(ACCOUNT_PATH, 'r') as f:
                account = json.load(f)
            account["pin"] = self.new_pin
            with open(ACCOUNT_PATH, 'w') as f:
                json.dump(account, f)
            self.speak("PIN updated.")
        except Exception:
            self.speak("Failed to update PIN.")
        self.pin_mode = None
        self.new_pin = ""
        self._return_from_pin()

    def _return_from_pin(self):
        if self.account_mode == "menu":
            self.speak(self.account_options[self.account_index])
            self.window.update_text("Account: " + self.account_options[self.account_index])
        else:
            self.speak(self.options[self.index])
            self.window.update_text("Settings: " + self.options[self.index])

    def _reset_technote(self):
        self.confirm_mode = "confirm_reset"
        self.speak("Are you sure you want to reset TechNote? Press Enter to confirm or Escape to cancel.")
        self.window.update_text("Confirm Reset TechNote?")

    def _do_reset_technote(self):
        self.confirm_mode = None
        self.speak("Resetting TechNote. Deleting account.")
        if os.path.exists(ACCOUNT_PATH):
            try:
                os.remove(ACCOUNT_PATH)
            except:
                pass
        if self.on_reset_account:
            self.on_reset_account()
        self.exit_app()