import os
import json
import subprocess
import sys
import win32con
from core.app_base import SoftApp

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TECH_SOFT = os.path.join(os.environ['USERPROFILE'], '.tech-soft')
ACCOUNT_PATH = os.path.join(TECH_SOFT, 'account.json')

class SettingsApp(SoftApp):
    def __init__(self, manager, window, on_reset_account=None):
        super().__init__(manager, window)
        self.on_reset_account = on_reset_account
        self.settings_file = os.path.join(TECH_SOFT, 'settings.json')
        self.settings = {"voice_speed": 100, "theme": "Dark"}
        self.load_settings()
        self.options = ["Theme", "About Tech-Note", "Check for Updates", "Reset PIN", "Reset TechNote"]
        self.index = 0
        self.pin_mode = None
        self.confirm_mode = None
        self.new_pin = ""

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r') as f:
                self.settings = json.load(f)

    def save_settings(self):
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f)

    def on_focus(self):
        self.speak(f"Settings. {self.options[self.index]}")
        self.window.update_text("Settings: " + self.options[self.index])

    def on_key(self, vk):
        if self.pin_mode:
            self._handle_pin_input(vk)
            return

        if self.confirm_mode:
            if vk == win32con.VK_RETURN:
                self._do_reset_technote()
            elif vk == win32con.VK_ESCAPE:
                self.confirm_mode = None
                self.speak("Cancelled.")
                self.window.update_text("Settings: " + self.options[self.index])
            return

        if vk == win32con.VK_ESCAPE:
            self.exit_app()
        elif vk == win32con.VK_BACK or vk == win32con.VK_UP:
            self.index = (self.index - 1) % len(self.options)
            self.speak(self.options[self.index])
            self.window.update_text("Settings: " + self.options[self.index])
        elif vk == win32con.VK_DOWN or vk == win32con.VK_SPACE:
            self.index = (self.index + 1) % len(self.options)
            self.speak(self.options[self.index])
            self.window.update_text("Settings: " + self.options[self.index])
        elif vk == win32con.VK_RETURN:
            self._select_current()

    def _select_current(self):
        key = self.options[self.index].lower().replace(' ', '_')
        if key == "theme":
            current = self.settings.get("theme", "Dark")
            self.settings["theme"] = "Light" if current == "Dark" else "Dark"
            self.save_settings()
            self.speak(f"Theme set to {self.settings['theme']}")
        elif key == "about_tech-note":
            self.speak("Tech-Note. A self voicing keyboard driven interface for Windows.")
            self.window.update_text("Tech-Note v1.0")
        elif key == "check_for_updates":
            self._check_for_updates()
        elif key == "reset_pin":
            self._start_pin_reset()
        elif key == "reset_technote":
            self._reset_technote()

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
                self.window.update_text("Settings: " + self.options[self.index])
        elif vk == win32con.VK_ESCAPE:
            self.pin_mode = None
            self.speak("Cancelled.")
            self.window.update_text("Settings: " + self.options[self.index])

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
                self.window.update_text("Settings: " + self.options[self.index])
        except Exception:
            self.speak("Failed to read account.")
            self.pin_mode = None
            self.window.update_text("Settings: " + self.options[self.index])

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
                self.window.update_text("Settings: " + self.options[self.index])
        elif vk == win32con.VK_ESCAPE:
            self.pin_mode = None
            self.speak("Cancelled.")
            self.window.update_text("Settings: " + self.options[self.index])

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