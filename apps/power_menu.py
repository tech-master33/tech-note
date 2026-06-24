import os
import win32con
import json
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.config import TECH_SOFT, SETTINGS_PATH, ACCOUNT_PATH
import core.error_handler

class PowerApp(SoftApp):
    def __init__(self, manager, window, on_restart=None, on_exit=None):
        super().__init__(manager, window)
        self.on_restart = on_restart
        self.on_exit = on_exit
        self.settings = self._load_settings()
        self.pin_mode = None
        self.pin_input = ""
        self.pending_action = None
        self._build_menu()

    def _load_settings(self):
        if os.path.exists(SETTINGS_PATH):
            try:
                with open(SETTINGS_PATH, 'r') as f:
                    return json.load(f)
            except Exception as e: core.error_handler.log(e, "Loading settings")
        return {}

    def _build_menu(self):
        root = MenuNode("Power Options")
        root.add_child(MenuNode("Restart Tech-Note", self._do_restart))
        root.add_child(MenuNode("Shutdown Tech-Note", self._do_shutdown))
        
        if self.settings.get("app_sleep_hibernate", True):
            root.add_child(MenuNode("Sleep Tech-Note", self._do_sleep))
            root.add_child(MenuNode("Hibernate Tech-Note", self._do_hibernate))
            
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def on_focus(self):
        item = self.menu.get_current_item()
        title = item.title if item else "Power Options"
        self.speak("Power Options. " + title)
        self.window.update_text("Power: " + title)

    def on_key(self, vk):
        if self.pin_mode:
            self._handle_pin(vk)
            return

        if vk == win32con.VK_ESCAPE:
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
            self.window.update_text("Power: " + item.title)

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if self.manager.space_used_in_chord:
                return
            if self.pin_mode:
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text("Power: " + item.title)

    def _handle_pin(self, vk):
        if 0x30 <= vk <= 0x39:
            self.pin_input += chr(vk)
            self.window.update_text("*" * len(self.pin_input))
            if len(self.pin_input) == 4:
                self._verify_pin()
        elif vk == win32con.VK_BACK:
            if self.pin_input:
                self.pin_input = self.pin_input[:-1]
                self.window.update_text("*" * len(self.pin_input) if self.pin_input else "Enter PIN: ")
            else:
                self.pin_mode = None
                self.speak("Cancelled.")
        elif vk == win32con.VK_ESCAPE:
            self.pin_mode = None
            self.speak("Cancelled.")

    def _verify_pin(self):
        try:
            with open(ACCOUNT_PATH, 'r') as f:
                account = json.load(f)
            if self.pin_input == account.get("pin", ""):
                self.pin_mode = None
                if self.pending_action:
                    self.pending_action()
            else:
                self.speak("Wrong PIN.")
                self.pin_mode = None
                self.pin_input = ""
        except:
            self.speak("Error verifying PIN.")
            self.pin_mode = None

    def _check_security(self, action):
        if self.settings.get("shutdown_pin", False):
            self.pin_mode = True
            self.pin_input = ""
            self.pending_action = action
            self.speak("Enter PIN to proceed.")
            self.window.update_text("Enter PIN: ")
            return False
        return True

    def _do_restart(self):
        if not self._check_security(self._restart_impl): return
        self._restart_impl()

    def _restart_impl(self):
        self.speak("Restarting Tech-Note.")
        self.window.update_text("Restarting Tech-Note...")
        self.exit_app()
        if self.on_restart:
            self.on_restart()

    def _do_shutdown(self):
        if not self._check_security(self._shutdown_impl): return
        self._shutdown_impl()

    def _shutdown_impl(self):
        if self.on_exit:
            self.on_exit()

    def _do_sleep(self):
        self.exit_app()
        if hasattr(self.manager, "_exit_app"):
            self.manager._exit_app(mode="sleep")

    def _do_hibernate(self):
        if not self._check_security(self._do_hibernate): return
        self.exit_app()
        if hasattr(self.manager, "_exit_app"):
            self.manager._exit_app(mode="hibernate")
