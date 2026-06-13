import os
import json
import subprocess
import sys
import win32con
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.config import TECH_SOFT, ACCOUNT_PATH, SETTINGS_PATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class SettingsApp(SoftApp):
    def __init__(self, manager, window, on_reset_account=None):
        super().__init__(manager, window)
        self.on_reset_account = on_reset_account
        self.settings_file = SETTINGS_PATH
        self.settings = {"rate": 0, "volume": 100, "theme": "Dark"}
        self.load_settings()
        self.pin_mode = None
        self.confirm_mode = None
        self.text_input = None
        self.account_menu = None
        self._build_main_menu()

    def _build_main_menu(self):
        self.account_menu = None
        root = MenuNode("Settings")
        root.add_child(MenuNode("Account Management", self._enter_account_menu))
        root.add_child(MenuNode("System Info and Updates", self._enter_info_menu))
        root.add_child(MenuNode("Reset TechNote", self._reset_technote))
        self.menu = MenuSystem(root, self.speak)

    def _enter_info_menu(self):
        root = MenuNode("System Info")
        root.add_child(MenuNode("Check for Updates", self._check_for_updates))
        root.add_child(MenuNode("About Tech-Note", self._about))
        root.add_child(MenuNode("Back", self._build_main_menu))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _build_account_menu(self):
        account = self._load_account()
        self._current_lock_type = account.get("lock_type", "pin")
        lt = "PIN" if self._current_lock_type == "pin" else "Password"
        
        root = MenuNode("Account")
        root.add_child(MenuNode("Change Username", lambda: self._start_text_input("username", "Enter new username.")))
        
        # Action depends on current lock type
        if self._current_lock_type == "pin":
            root.add_child(MenuNode("Change PIN", self._start_pin_reset))
        else:
            root.add_child(MenuNode("Change Password", lambda: self._start_text_input("password", "Enter new password.")))
            
        root.add_child(MenuNode(f"Lock Type ({lt})", self._toggle_lock_type))
        root.add_child(MenuNode("Back", self._back_from_account))
        self.account_menu = MenuSystem(root, self.speak)

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
        item = self.menu.get_current_item()
        title = item.title if item else "Settings"
        self.speak("Settings. " + title)
        self.window.update_text("Settings: " + title)

    def _toggle_theme(self):
        current = self.settings.get("theme", "Dark")
        self.settings["theme"] = "Light" if current == "Dark" else "Dark"
        self.save_settings()
        self.speak(f"Theme set to {self.settings['theme']}")

    def _about(self):
        self.speak("Tech-Note. A self voicing keyboard driven interface for Windows.")
        self.window.update_text("Tech-Note v1.0")

    def on_key(self, vk):
        if self.pin_mode:
            self._handle_pin_input(vk)
            return

        if self.text_input is not None:
            self._handle_text_input(vk)
            return

        if self.confirm_mode:
            if vk == win32con.VK_RETURN:
                self._do_reset_technote()
            elif vk == win32con.VK_ESCAPE:
                self.confirm_mode = None
                self.speak("Cancelled.")
                self._announce_main()
            return

        if self.account_menu:
            if vk == win32con.VK_ESCAPE:
                self._back_from_account()
                return
            if vk in (win32con.VK_BACK, win32con.VK_UP):
                self.account_menu.previous()
            elif vk in (win32con.VK_DOWN, win32con.VK_SPACE):
                self.account_menu.next()
            elif vk == win32con.VK_RETURN:
                self.account_menu.select()
            item = self.account_menu.get_current_item()
            if item:
                self.window.update_text("Account: " + item.title)
            return

        if vk == win32con.VK_ESCAPE:
            self.exit_app()
        elif vk in (win32con.VK_BACK, win32con.VK_UP):
            self.menu.previous()
        elif vk in (win32con.VK_DOWN, win32con.VK_SPACE):
            self.menu.next()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Settings: " + item.title)

    def _announce_main(self):
        item = self.menu.get_current_item()
        title = item.title if item else "Settings"
        self.speak(title)
        self.window.update_text("Settings: " + title)

    def _enter_account_menu(self):
        self._build_account_menu()
        item = self.account_menu.get_current_item()
        title = item.title if item else "Account"
        self.speak("Account. " + title)
        self.window.update_text("Account: " + title)

    def _back_from_account(self):
        self.account_menu = None
        self._announce_main()

    def _toggle_lock_type(self):
        account = self._load_account()
        current = account.get("lock_type", "pin")
        new_type = "password" if current == "pin" else "pin"
        account["lock_type"] = new_type
        self._save_account(account)
        self._current_lock_type = new_type
        
        lt_name = "PIN" if new_type == "pin" else "Password"
        self.speak(f"Lock type set to {lt_name}.")
        
        # Immediately enter the corresponding reset/input mode
        if new_type == "pin":
            self._start_pin_reset()
        else:
            self._start_text_input("password", "Enter new password.")

    def _start_text_input(self, field, prompt):
        self.text_input_field = field
        self.text_input = ""
        self.speak(prompt)
        self.window.update_text(f"{field.capitalize()}: ")

    def _handle_text_input(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.text_input = None
            item = self.account_menu.get_current_item()
            title = item.title if item else "Account"
            self.speak(title)
            self.window.update_text("Account: " + title)
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
            self.text_input = None
            item = self.account_menu.get_current_item()
            title = item.title if item else "Account"
            self.speak(title)
            self.window.update_text("Account: " + title)
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
        self._announce_main()

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
        if self.account_menu:
            self._build_account_menu()
            item = self.account_menu.get_current_item()
            title = item.title if item else "Account"
            self.speak(title)
            self.window.update_text("Account: " + title)
        else:
            self._announce_main()

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