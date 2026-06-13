import os
import json
import subprocess
import sys
import shutil
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
        self.settings = {
            "theme": "Dark", "bg_color": "Black", "font_size": "Medium",
            "time_format": "12h", "startup_sound": "On",
            "keyboard_layout": "US", "update_channel": "stable"
        }
        self.load_settings()
        self.adjust_mode = None
        self.pin_mode = None
        self.confirm_mode = None
        self.text_input = None
        self.account_menu = None
        self._in_sub_menu = False
        self._build_main_menu()

    def _build_main_menu(self):
        self.account_menu = None
        self.adjust_mode = None
        self._in_sub_menu = False
        root = MenuNode("Settings")
        root.add_child(MenuNode("Account Management", self._enter_account_menu))
        root.add_child(MenuNode("Display Settings", self._enter_display_menu))
        root.add_child(MenuNode("System Settings", self._enter_system_menu))
        root.add_child(MenuNode("Check for Updates", self._check_for_updates))
        root.add_child(MenuNode("About Tech-Note", self._about))
        root.add_child(MenuNode("Reset TechNote", self._reset_technote))
        self.menu = MenuSystem(root, self.speak)

    def _enter_display_menu(self):
        self._in_sub_menu = True
        root = MenuNode("Display Settings")
        root.add_child(MenuNode("Theme", lambda: self._enter_adjust("theme")))
        root.add_child(MenuNode("Background Color", lambda: self._enter_adjust("bg_color")))
        root.add_child(MenuNode("Font Size", lambda: self._enter_adjust("font_size")))
        root.add_child(MenuNode("Back", self._back_to_main_menu))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _enter_system_menu(self):
        self._in_sub_menu = True
        root = MenuNode("System Settings")
        root.add_child(MenuNode("Time Format", lambda: self._enter_adjust("time_format")))
        root.add_child(MenuNode("Startup Sound", lambda: self._enter_adjust("startup_sound")))
        root.add_child(MenuNode("Keyboard Layout", lambda: self._enter_adjust("keyboard_layout")))
        root.add_child(MenuNode("Update Channel", lambda: self._enter_adjust("update_channel")))
        root.add_child(MenuNode("Back", self._back_to_main_menu))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _back_to_main_menu(self):
        self._build_main_menu()
        self._announce_main()

    def _about(self):
        self.speak("Tech-Note. A self voicing keyboard driven interface for Windows.")
        self.window.update_text("Tech-Note v1.0")

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    loaded = json.load(f)
                self.settings.update(loaded)
            except (json.JSONDecodeError, IOError):
                pass

    def save_settings(self):
        try:
            full_settings = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    full_settings = json.load(f)
            full_settings.update(self.settings)
            with open(self.settings_file, 'w') as f:
                json.dump(full_settings, f)
        except Exception:
            pass

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

    def on_key(self, vk):
        if self.adjust_mode:
            self._handle_adjust(vk)
            return

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
            if self._in_sub_menu:
                self._back_to_main_menu()
            else:
                self.exit_app()
            return

        if vk in (win32con.VK_BACK, win32con.VK_UP):
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

    def _build_account_menu(self):
        account = self._load_account()
        self._current_lock_type = account.get("lock_type", "pin")
        lt = "PIN" if self._current_lock_type == "pin" else "Password"

        root = MenuNode("Account")
        root.add_child(MenuNode("Change Username", lambda: self._start_text_input("username", "Enter new username.")))

        if self._current_lock_type == "pin":
            root.add_child(MenuNode("Change PIN", self._start_pin_reset))
        else:
            root.add_child(MenuNode("Change Password", lambda: self._start_text_input("password", "Enter new password.")))

        root.add_child(MenuNode(f"Lock Type ({lt})", self._toggle_lock_type))
        root.add_child(MenuNode("Back", self._back_from_account))
        self.account_menu = MenuSystem(root, self.speak)

    def _toggle_lock_type(self):
        account = self._load_account()
        current = account.get("lock_type", "pin")
        new_type = "password" if current == "pin" else "pin"
        account["lock_type"] = new_type
        self._save_account(account)
        self._current_lock_type = new_type

        lt_name = "PIN" if new_type == "pin" else "Password"
        self.speak(f"Lock type set to {lt_name}.")

        if new_type == "pin":
            self._start_pin_reset()
        else:
            self._start_text_input("password", "Enter new password.")

    def _enter_adjust(self, key):
        self.adjust_mode = key
        val = self.settings.get(key)
        self.speak(f"{key.replace('_', ' ').title()}. Current: {val}.")
        self.window.update_text(key.replace('_', ' ').title() + ": " + str(val))

    def _handle_adjust(self, vk):
        if vk == win32con.VK_BACK or vk == win32con.VK_ESCAPE:
            self.adjust_mode = None
            self._in_sub_menu = True
            item = self.menu.get_current_item()
            title = item.title if item else "Display Settings"
            self.window.update_text("Settings: " + title)
            self.menu.announce_current()
            return
        elif vk == 0xBB:
            self._adjust_value(1)
        elif vk == 0xBD:
            self._adjust_value(-1)
        elif vk == win32con.VK_RETURN:
            self.adjust_mode = None
            item = self.menu.get_current_item()
            title = item.title if item else "Display Settings"
            self.window.update_text("Settings: " + title)
            self.speak("Set.")

    def _adjust_value(self, direction):
        key = self.adjust_mode
        if not key: return

        if key == "time_format":
            opts = ["12h", "24h"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % 2]
            self.speak(self.settings[key])
        elif key == "startup_sound":
            opts = ["On", "Off"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % 2]
            self.speak(self.settings[key])
        elif key == "keyboard_layout":
            opts = ["US", "UK"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % 2]
            self.speak(self.settings[key])
            self._apply_keyboard_layout()
        elif key == "update_channel":
            opts = ["stable", "unstable"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % 2]
            self.speak(self.settings[key])
            self._switch_branch()
        elif key == "theme":
            opts = ["Dark", "Light"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % 2]
            self.speak(self.settings[key])
        elif key == "bg_color":
            opts = ["Black", "Blue", "Gray"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % 3]
            self.speak(self.settings[key])
            self._apply_display_settings()
        elif key == "font_size":
            opts = ["Small", "Medium", "Large"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % 3]
            self.speak(self.settings[key])
            self._apply_display_settings()

        self.window.update_text(key.replace('_', ' ').title() + ": " + str(self.settings[key]))
        self.save_settings()

    def _apply_display_settings(self):
        colors = {"Black": (0,0,0), "Blue": (0,0,128), "Gray": (64,64,64)}
        bg = colors.get(self.settings.get("bg_color", "Black"), (0,0,0))
        fs = self.settings.get("font_size", "Medium")
        self.window.set_display_settings(bg_color=bg, font_size=fs)

    def _apply_keyboard_layout(self):
        self.speak("Restart to apply keyboard layout.")

    def _start_text_input(self, field, prompt):
        self.text_input_field = field
        self.text_input = ""
        self.speak(prompt)
        self.window.update_text(f"{field.capitalize()}: ")

    def _handle_text_input(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.text_input = None
            self._enter_account_menu()
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
            self._enter_account_menu()
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

    def _switch_branch(self):
        branch = "main" if self.settings.get("update_channel") == "stable" else "testing"
        try:
            result = subprocess.run(
                ["git", "checkout", branch], cwd=BASE_DIR,
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                self.speak(f"Switched to {branch} channel.")
            else:
                self.speak(f"Failed to switch to {branch}.")
        except Exception:
            self.speak("Could not switch branch.")

    def _check_for_updates(self):
        self.speak("Checking for updates. Please wait.")
        self.window.update_text("Updating...")
        try:
            branch = "main" if self.settings.get("update_channel") == "stable" else "testing"
            subprocess.run(
                ["git", "checkout", branch], cwd=BASE_DIR,
                capture_output=True, text=True, timeout=30
            )
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
        self.speak("Resetting TechNote.")
        if os.path.exists(TECH_SOFT):
            try:
                shutil.rmtree(TECH_SOFT)
            except:
                pass
        if self.on_reset_account:
            self.on_reset_account()
        self.exit_app()

    def get_help_text(self):
        if self.adjust_mode:
            return f"Adjusting {self.adjust_mode.replace('_', ' ')}. Use Plus and Minus to change value, Enter to save, Escape to cancel."
        if self.account_menu:
            return "Account Management. Use arrows to navigate options. Enter to select. Escape to go back."
        return "Settings App. Use arrows to navigate. Enter to select. Escape to exit."
