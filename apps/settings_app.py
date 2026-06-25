import os
import json
import subprocess
import sys
import shutil
import datetime
import win32con
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.config import TECH_SOFT, ACCOUNT_PATH, SETTINGS_PATH
import core.error_handler
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class SettingsApp(SoftApp):
    def __init__(self, manager, window, on_reset_account=None):
        super().__init__(manager, window)
        self.on_reset_account = on_reset_account
        self.settings_file = SETTINGS_PATH
        self.settings = {
            "theme": "Dark", "bg_color": "Black", "font_size": "Medium",
            "time_format": "12h", "startup_sound": "On",
            "keyboard_layout": "US", "update_channel": "stable",
            "auto_update_on_startup": False,
            "custom_goodbye": "Goodbye.",
            "shutdown_pin": False,
            "night_mode_filter": False,
            "auto_resume_apps": True,
            "smooth_shutdown_audio": True,
            "app_sleep_hibernate": True,
            "shutdown_key_protection": True,
            "log_level": "WARN"
        }
        self.load_settings()
        self.pin_mode = None
        self.confirm_mode = None
        self.text_input = None
        self.account_menu = None
        self._in_sub_menu = False
        self._find_setting_mode = False
        self._find_setting_buf = ""
        self._current_parent_back = None
        self._numeric_key = None
        self._numeric_min = None
        self._numeric_max = None
        self.adjust_mode = None
        self._text_input_buf = ""
        self._build_main_menu()

    def _build_main_menu(self):
        self.account_menu = None
        self._in_sub_menu = False
        root = MenuNode("Settings")
        root.add_child(MenuNode("Account Management", self._enter_account_menu))
        root.add_child(MenuNode("Display Settings", self._enter_display_menu))
        root.add_child(MenuNode("System Settings", self._enter_system_menu))
        root.add_child(MenuNode("Find Setting", self._enter_find_setting))
        root.add_child(MenuNode("Backup Settings", self._do_backup))
        root.add_child(MenuNode("Restore Settings", self._enter_restore))
        root.add_child(MenuNode("Check for Updates", self._check_for_updates))
        root.add_child(MenuNode("About Tech-Note", self._about))
        root.add_child(MenuNode("Reset TechNote", self._reset_technote))
        self.menu = MenuSystem(root, self.speak)

    def _enter_display_menu(self):
        self._in_sub_menu = True
        self._current_parent_back = self._back_to_main_menu
        root = MenuNode("Display Settings")
        root.add_child(MenuNode("Theme", lambda: self._enter_list_setting("theme", ["Dark", "Light"], side_effect=None)))
        root.add_child(MenuNode("Background Color", lambda: self._enter_list_setting("bg_color", ["Black", "Blue", "Gray", "Green", "Purple", "Red", "Teal", "White"], side_effect=self._bg_side_effect)))
        root.add_child(MenuNode("Font Size", lambda: self._enter_list_setting("font_size", ["Small", "Medium", "Large"], side_effect=self._font_side_effect)))
        root.add_child(MenuNode("Night Mode Filter", lambda: self._enter_list_setting("night_mode_filter", [False, True], display_map={False: "Off", True: "On"})))
        root.add_child(MenuNode("Back", self._back_to_main_menu))
        self._switch_to_submenu(root, "Display Settings")

    def _enter_system_menu(self):
        self._in_sub_menu = True
        self._current_parent_back = self._back_to_main_menu
        root = MenuNode("System Settings")
        root.add_child(MenuNode("Time Format", lambda: self._enter_list_setting("time_format", ["12h", "24h"])))
        root.add_child(MenuNode("Startup Sound", lambda: self._enter_list_setting("startup_sound", ["On", "Off"])))
        root.add_child(MenuNode("Keyboard Layout", lambda: self._enter_list_setting("keyboard_layout", ["US", "UK", "Arabic"], side_effect=self._kbd_side_effect)))
        root.add_child(MenuNode("Update Channel", lambda: self._enter_list_setting("update_channel", ["stable", "unstable"], side_effect=self._update_side_effect)))
        root.add_child(MenuNode("Auto-Update on Startup", lambda: self._enter_list_setting("auto_update_on_startup", [False, True], display_map={False: "Off", True: "On"})))
        root.add_child(MenuNode("Remember Last App", lambda: self._enter_list_setting("auto_resume_apps", [False, True], display_map={False: "Off", True: "On"})))
        root.add_child(MenuNode("Fade Audio on Shutdown", lambda: self._enter_list_setting("smooth_shutdown_audio", [False, True], display_map={False: "Off", True: "On"})))
        root.add_child(MenuNode("Sleep/Hibernate Options", lambda: self._enter_list_setting("app_sleep_hibernate", [False, True], display_map={False: "Off", True: "On"})))
        root.add_child(MenuNode("Block Keys During Shutdown", lambda: self._enter_list_setting("shutdown_key_protection", [False, True], display_map={False: "Off", True: "On"})))
        root.add_child(MenuNode("Log Level", lambda: self._enter_list_setting("log_level", ["SILENT", "ERROR", "WARN", "INFO", "DEBUG", "ALL"], side_effect=self._log_level_side_effect)))
        root.add_child(MenuNode("Do Not Disturb", lambda: self._enter_list_setting("dnd_enabled", [False, True], display_map={False: "Off", True: "On"}, side_effect=self._dnd_side_effect)))
        root.add_child(MenuNode("Back", self._back_to_main_menu))
        self._switch_to_submenu(root, "System Settings")

    def _enter_list_setting(self, key, options, display_map=None, side_effect=None):
        root = MenuNode(key.replace('_', ' ').title())
        current = self.settings.get(key)
        display = display_map or {}
        for opt in options:
            label = display.get(opt, str(opt))
            if opt == current:
                label = f"{label} (current)"
            root.add_child(MenuNode(label, lambda v=opt: self._set_setting_and_back(key, v, side_effect)))
        root.add_child(MenuNode("Back", self._current_parent_back or self._back_to_main_menu))
        self._switch_to_submenu(root, key.replace('_', ' ').title())

    def _set_setting_and_back(self, key, value, side_effect=None):
        self.settings[key] = value
        self.save_settings()
        if side_effect:
            side_effect(key, value)
        display = {False: "Off", True: "On"}.get(value, str(value))
        self.speak(f"{key.replace('_', ' ').title()} set to {display}.")
        if self._current_parent_back:
            self._current_parent_back()

    def _bg_side_effect(self, key, value):
        self._apply_display_settings()

    def _font_side_effect(self, key, value):
        self._apply_display_settings()

    def _dnd_side_effect(self, key, value):
        from core.notification_center import get_center
        get_center().set_dnd(value)

    def _kbd_side_effect(self, key, value):
        self._apply_keyboard_layout()

    def _update_side_effect(self, key, value):
        self._switch_branch()

    def _log_level_side_effect(self, key, value):
        name_map = {"SILENT": 0, "ERROR": 1, "WARN": 2, "INFO": 3, "DEBUG": 4, "ALL": 5}
        core.error_handler.set_level(name_map.get(value, 2))
        core.error_handler.log(None, f"Log level set to {value}", level=core.error_handler.LEVEL_INFO)

    def _switch_to_submenu(self, root, title):
        self.menu = MenuSystem(root, self.speak)
        self.window.update_text(title + ": " + self.menu.get_current_item().title)

    def _back_to_main_menu(self):
        self._build_main_menu()
        self._announce_main()

    def _about(self):
        from core.version import VERSION
        self.speak(f"Tech-Note version {VERSION}. A self voicing keyboard driven interface for Windows.")
        self.window.update_text(f"Tech-Note v{VERSION}")

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
        if getattr(self, '_find_setting_mode', False):
            self._handle_find_setting(vk)
            return

        if self.pin_mode:
            self._handle_pin_input(vk)
            return

        if self.text_input is not None:
            if self.adjust_mode == "text_input":
                self._handle_text_input(vk)
                return
            self._handle_account_text_input(vk)
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
            if vk == win32con.VK_BACK:
                self.account_menu.previous()
            elif vk == win32con.VK_RETURN:
                self.account_menu.select()
            elif 0x41 <= vk <= 0x5A:
                char = chr(vk)
                self.account_menu.first_letter_nav(char)

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

        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            char = chr(vk)
            self.menu.first_letter_nav(char)

        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Settings: " + item.title)

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if self.manager.space_used_in_chord:
                return
            if self.pin_mode or self.text_input is not None or self.confirm_mode:
                return

            if self.account_menu:
                self.account_menu.next()
                item = self.account_menu.get_current_item()
                if item:
                    self.window.update_text("Account: " + item.title)
            else:
                self.menu.next()
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
        root.add_child(MenuNode("Change Username", lambda: self._start_account_text_input("username", "Enter new username.")))
        root.add_child(MenuNode("Change Custom Goodbye", lambda: self._start_account_text_input("custom_goodbye", "Enter new goodbye message.")))

        if self._current_lock_type == "pin":
            root.add_child(MenuNode("Change PIN", self._start_pin_reset))
        else:
            root.add_child(MenuNode("Change Password", lambda: self._start_account_text_input("password", "Enter new password.")))

        root.add_child(MenuNode(f"Lock Type ({lt})", self._toggle_lock_type))
        root.add_child(MenuNode("Shutdown PIN (" + ("On" if self.settings.get("shutdown_pin") else "Off") + ")", lambda: self._toggle_shutdown_pin()))
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
            self._start_account_text_input("password", "Enter new password.")

    def _toggle_shutdown_pin(self):
        self.settings["shutdown_pin"] = not self.settings["shutdown_pin"]
        self.save_settings()
        self.speak(f"Shutdown PIN {'On' if self.settings['shutdown_pin'] else 'Off'}.")
        self._enter_account_menu()

    def _apply_display_settings(self):
        colors = {"Black": (0,0,0), "Blue": (0,0,128), "Gray": (64,64,64), "Green": (0,64,0), "Purple": (64,0,64), "Red": (64,0,0), "Teal": (0,64,64), "White": (200,200,200)}
        bg = colors.get(self.settings.get("bg_color", "Black"), (0,0,0))
        luminance = 0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]
        fg = (0, 0, 0) if luminance > 128 else (200, 200, 200)
        fs = self.settings.get("font_size", "Medium")
        self.window.set_display_settings(bg_color=bg, font_size=fs, fg_color=fg)

    def _apply_keyboard_layout(self):
        self.speak("Restart to apply keyboard layout.")

    def _start_account_text_input(self, field, prompt):
        self.adjust_mode = "text_input"
        self.text_input_field = field
        self.text_input = ""
        self._text_input_buf = ""
        self.speak(prompt)
        self.window.update_text(f"{field.capitalize()}: ")

    def _handle_account_text_input(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.text_input = None
            self.adjust_mode = None
            self._enter_account_menu()
            return
        if vk == win32con.VK_RETURN:
            val = self._text_input_buf.strip()
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
            elif self.text_input_field == "custom_goodbye":
                self.settings["custom_goodbye"] = val
                self.save_settings()
                self.speak(f"Goodbye message set to {val}.")
            self.text_input = None
            self.adjust_mode = None
            self._enter_account_menu()
            return
        if vk == win32con.VK_BACK:
            if self._text_input_buf:
                self._text_input_buf = self._text_input_buf[:-1]
                self.window.update_text(self._text_input_buf if self._text_input_buf else " ")
            return
        ch = self._vk_to_char(vk)
        if ch is not None:
            self._text_input_buf += ch
            self.window.update_text(self._text_input_buf)

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
        elif self.pin_mode == "confirm_reset_pin":
            self._handle_confirm_reset_pin(vk)
        elif self.pin_mode == "confirm_reset_password":
            self._handle_confirm_reset_password(vk)

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

    def _handle_confirm_reset_pin(self, vk):
        if 0x30 <= vk <= 0x39:
            self.new_pin += chr(vk)
            self.window.update_text("*" * len(self.new_pin))
            if len(self.new_pin) == 4:
                try:
                    with open(ACCOUNT_PATH, 'r') as f:
                        account = json.load(f)
                    if self.new_pin == account.get("pin", ""):
                        self.pin_mode = None
                        self.confirm_mode = "confirm_reset"
                        self.speak("Are you sure you want to reset TechNote? Press Enter to confirm or Escape to cancel.")
                        self.window.update_text("Confirm Reset TechNote?")
                    else:
                        self.speak("Wrong PIN. Reset cancelled.")
                        self.pin_mode = None
                        self._announce_main()
                except Exception:
                    self.speak("Failed to verify PIN.")
                    self.pin_mode = None
                    self._announce_main()
        elif vk == win32con.VK_BACK:
            if self.new_pin:
                self.new_pin = self.new_pin[:-1]
                self.window.update_text("*" * len(self.new_pin) if self.new_pin else "Confirm PIN:")
            else:
                self.pin_mode = None
                self.speak("Cancelled.")
                self._announce_main()
        elif vk == win32con.VK_ESCAPE:
            self.pin_mode = None
            self.speak("Cancelled.")
            self._announce_main()

    def _handle_confirm_reset_password(self, vk):
        if vk == win32con.VK_RETURN:
            try:
                with open(ACCOUNT_PATH, 'r') as f:
                    account = json.load(f)
                if self._text_input_buf == account.get("password", ""):
                    self.pin_mode = None
                    self.confirm_mode = "confirm_reset"
                    self.speak("Are you sure you want to reset TechNote? Press Enter to confirm or Escape to cancel.")
                    self.window.update_text("Confirm Reset TechNote?")
                else:
                    self.speak("Wrong password. Reset cancelled.")
                    self.pin_mode = None
                    self._announce_main()
            except Exception:
                self.speak("Failed to verify password.")
                self.pin_mode = None
                self._announce_main()
            return
        if vk == win32con.VK_BACK:
            if self._text_input_buf:
                self._text_input_buf = self._text_input_buf[:-1]
                self.window.update_text("*" * len(self._text_input_buf) if self._text_input_buf else "Confirm Password:")
            else:
                self.pin_mode = None
                self.speak("Cancelled.")
                self._announce_main()
            return
        if vk == win32con.VK_ESCAPE:
            self.pin_mode = None
            self.speak("Cancelled.")
            self._announce_main()
            return
        if vk == win32con.VK_SPACE:
            self._text_input_buf += " "
            self.window.update_text("*" * len(self._text_input_buf))
            return
        ch = self._vk_to_char(vk)
        if ch is not None:
            self._text_input_buf += ch
            self.window.update_text("*" * len(self._text_input_buf))

    def _restart_app(self):
        subprocess.Popen([sys.executable] + sys.argv, creationflags=subprocess.CREATE_NO_WINDOW)
        self.manager._exit_app()

    def _reset_technote(self):
        account = self._load_account()
        lock_type = account.get("lock_type", "pin")
        if lock_type == "pin" and account.get("pin"):
            self.pin_mode = "confirm_reset_pin"
            self.new_pin = ""
            self.speak("Enter current PIN to confirm reset.")
            self.window.update_text("Confirm PIN:")
        elif lock_type == "password" and account.get("password"):
            self.pin_mode = "confirm_reset_password"
            self._text_input_buf = ""
            self.speak("Enter current password to confirm reset.")
            self.window.update_text("Confirm Password:")
        else:
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

    # --- Find Setting ---
    def _build_flat_settings_map(self):
        return {
            "Theme": ("Display Settings", "theme"),
            "Background Color": ("Display Settings", "bg_color"),
            "Font Size": ("Display Settings", "font_size"),
            "Night Mode Filter": ("Display Settings", "night_mode_filter"),
            "Time Format": ("System Settings", "time_format"),
            "Startup Sound": ("System Settings", "startup_sound"),
            "Keyboard Layout": ("System Settings", "keyboard_layout"),
            "Update Channel": ("System Settings", "update_channel"),
            "Auto-Update on Startup": ("System Settings", "auto_update_on_startup"),
            "Remember Last App": ("System Settings", "auto_resume_apps"),
            "Fade Audio on Shutdown": ("System Settings", "smooth_shutdown_audio"),
            "Sleep/Hibernate Options": ("System Settings", "app_sleep_hibernate"),
            "Block Keys During Shutdown": ("System Settings", "shutdown_key_protection"),
            "Log Level": ("System Settings", "log_level"),
            "Username": ("Account", "username"),
            "Custom Goodbye": ("Account", "custom_goodbye"),
            "Lock Type": ("Account", "lock_type"),
            "Shutdown PIN": ("Account", "shutdown_pin"),
        }

    def _enter_find_setting(self):
        self._find_setting_mode = True
        self._find_setting_buf = ""
        self.speak("Type setting name to find.")
        self.window.update_text("Find Setting: ")

    def _handle_find_setting(self, vk):
        if vk == win32con.VK_ESCAPE:
            self._find_setting_mode = False
            self._find_setting_buf = ""
            self.speak("Cancelled.")
            self._announce_main()
            return
        if vk == win32con.VK_BACK:
            if self._find_setting_buf:
                self._find_setting_buf = self._find_setting_buf[:-1]
                self.window.update_text(f"Find Setting: {self._find_setting_buf}")
            return
        if vk == win32con.VK_RETURN:
            self._find_setting_mode = False
            self._find_setting_buf = ""
            self._announce_main()
            return
        ch = self._vk_to_char(vk)
        if ch:
            self._find_setting_buf += ch
            self.window.update_text(f"Find Setting: {self._find_setting_buf}")
            q = self._find_setting_buf.lower()
            flat = self._build_flat_settings_map()
            matches = [(name, sub, key) for name, (sub, key) in flat.items() if q in name.lower()]
            if len(matches) == 1:
                name, sub, key = matches[0]
                if key in self.settings:
                    val = self.settings[key]
                    display = {False: "Off", True: "On"}.get(val, str(val))
                    self.speak(f"Found {name} in {sub}: {display}.")
                else:
                    self.speak(f"Found {name} in {sub}.")
            elif len(matches) > 1:
                names = [m[0] for m in matches]
                self.speak(f"{len(matches)} matches: {', '.join(names)}.")
            else:
                self.speak(f"No matches for {q}.")

    # --- Backup / Restore ---
    BACKUP_FILES = ["settings.json", "account.json", "notes.json", "installed_apps.json",
                     "favorite_apps.json", "bookmarks.json", "history.json", "email_config.json",
                     "chat_profiles.json", "habits.json", "tasks.json", "contacts.json",
                     "opencode_settings.json", "opencode_sessions.json", "chatgpt_settings.json",
                     "chatgpt_sessions.json", "scores.json", "pronunciation_dict.json"]

    def _do_backup(self):
        docs = os.path.join(TECH_SOFT, 'documents')
        os.makedirs(docs, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"full_backup_{ts}"
        backup_dir = os.path.join(docs, backup_name)
        try:
            os.makedirs(backup_dir, exist_ok=True)
            count = 0
            for fname in self.BACKUP_FILES:
                src = os.path.join(TECH_SOFT, fname)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(backup_dir, fname))
                    count += 1
            self.speak(f"Backup saved: {count} files in {backup_name}.")
            self.window.update_text(f"Backup: {backup_name} ({count} files)")
        except Exception:
            self.speak("Backup failed.")

    def _enter_restore(self):
        docs = os.path.join(TECH_SOFT, 'documents')
        if not os.path.exists(docs):
            self.speak("No backups found.")
            return
        old_backups = sorted([f for f in os.listdir(docs) if f.startswith("settings_backup_") and f.endswith(".json")])
        backups = sorted([d for d in os.listdir(docs) if d.startswith("full_backup_") and os.path.isdir(os.path.join(docs, d))]) + old_backups
        if not backups:
            self.speak("No backups found.")
            return
        root = MenuNode("Restore Settings")
        for b in backups:
            root.add_child(MenuNode(b, lambda name=b: self._do_restore(name)))
        root.add_child(MenuNode("Back", self._back_to_main_menu))
        self._switch_to_submenu(root, "Restore Settings")

    def _do_restore(self, name):
        backup_path = os.path.join(TECH_SOFT, 'documents', name)
        try:
            if os.path.isdir(backup_path):
                count = 0
                for fname in self.BACKUP_FILES:
                    src = os.path.join(backup_path, fname)
                    if os.path.exists(src):
                        shutil.copy2(src, os.path.join(TECH_SOFT, fname))
                        count += 1
                if os.path.exists(SETTINGS_PATH):
                    with open(SETTINGS_PATH, 'r') as f:
                        self.settings.update(json.load(f))
                self.speak(f"Restored {count} files.")
            else:
                with open(backup_path, 'r') as f:
                    loaded = json.load(f)
                with open(SETTINGS_PATH, 'w') as f:
                    json.dump(loaded, f)
                self.settings.update(loaded)
                self.speak(f"Restored from {name}.")
            self._back_to_main_menu()
        except Exception:
            self.speak("Restore failed.")

    def _switch_branch(self):
        branch = "main" if self.settings.get("update_channel") == "stable" else "testing"
        try:
            subprocess.run(
                ["git", "checkout", branch], cwd=BASE_DIR,
                capture_output=True, text=True, timeout=30
            )
            result = subprocess.run(
                ["git", "pull"], cwd=BASE_DIR,
                capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0:
                subprocess.run(
                    ["git", "branch", "--set-upstream-to", f"origin/{branch}", branch],
                    cwd=BASE_DIR, capture_output=True, text=True, timeout=30
                )
                result = subprocess.run(
                    ["git", "pull"], cwd=BASE_DIR,
                    capture_output=True, text=True, timeout=60
                )
            if result.returncode == 0 and "Already up to date" not in result.stdout.strip():
                self._install_requirements()
            self.speak(f"Switched to {branch}. Restarting.")
            self._restart_app()
        except Exception:
            self.speak("Could not switch branch.")

    def _check_for_updates(self):
        try:
            from core.updater import check_now
            check_now(synth=self.synth, window=self.window)
        except Exception:
            self.speak("Update check failed.")

    def get_help_text(self):
        if self.account_menu:
            return "Account Management. Use Space and Backspace to navigate. Enter to select. Escape to go back."
        return "Settings App. Use Space and Backspace to navigate. Enter to select. Escape to exit."
