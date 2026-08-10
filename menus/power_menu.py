import os
import win32con
import json
import time
import threading
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.config import TECH_SOFT, SETTINGS_PATH, ACCOUNT_PATH
import core.error_handler

SCHEDULE_FILE = os.path.join(TECH_SOFT, "power_schedule.json")


class PowerApp(SoftApp):
    def __init__(self, manager, window, on_restart=None, on_exit=None):
        super().__init__(manager, window)
        self.on_restart = on_restart
        self.on_exit = on_exit
        self.settings = self._load_settings()
        self.pin_mode = None
        self.pin_input = ""
        self.pending_action = None
        self._schedule = self._load_schedule()
        self._schedule_timer = None
        self._text_input_field = None
        self._input_prompt = ""
        self._input_buf = ""
        self._start_schedule_watcher()
        self._build_menu()

    def _load_schedule(self):
        if os.path.exists(SCHEDULE_FILE):
            try:
                with open(SCHEDULE_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_schedule(self):
        try:
            with open(SCHEDULE_FILE, 'w') as f:
                json.dump(self._schedule, f)
        except Exception:
            pass

    def _start_schedule_watcher(self):
        if self._schedule.get("enabled") and self._schedule.get("time"):
            def _watch():
                while True:
                    now = time.localtime()
                    current = f"{now.tm_hour:02d}:{now.tm_min:02d}"
                    if current == self._schedule.get("time"):
                        if self._schedule.get("action") == "shutdown":
                            self.speak("Scheduled shutdown. Saving work.")
                            if self._check_unsaved():
                                self.speak("Unsaved work detected. Schedule cancelled.")
                                return
                            self._shutdown_impl()
                        elif self._schedule.get("action") == "sleep":
                            self._do_sleep()
                        break
                    time.sleep(30)
            t = threading.Thread(target=_watch, daemon=True)
            t.start()

    def _check_unsaved(self):
        if hasattr(self.manager, "app_manager") and hasattr(self.manager.app_manager, "_running_apps"):
            for app in self.manager.app_manager._running_apps.values():
                if hasattr(app, "is_dirty") and app.is_dirty():
                    return True
        return False

    def _enter_schedule_shutdown(self):
        self._text_input_field = "schedule_time"
        self._input_prompt = "Enter time in 24h format (HH:MM):"
        self.speak(self._input_prompt)
        self.window.update_text(self._input_prompt)

    def _enter_schedule_sleep(self):
        self._text_input_field = "schedule_time_sleep"
        self._input_prompt = "Enter time in 24h format (HH:MM):"
        self.speak(self._input_prompt)
        self.window.update_text(self._input_prompt)

    def _cancel_schedule(self):
        self._schedule = {}
        self._save_schedule()
        self.speak("Scheduled action cancelled.")
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
        
        schedule = root.add_child(MenuNode("Schedule"))
        if self._schedule.get("enabled"):
            schedule.add_child(MenuNode(f"Cancel Scheduled {self._schedule.get('action','').title()}", self._cancel_schedule))
        else:
            schedule.add_child(MenuNode("Schedule Shutdown", self._enter_schedule_shutdown))
            schedule.add_child(MenuNode("Schedule Sleep", self._enter_schedule_sleep))
            
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
        if self._text_input_field:
            self._handle_text_input(vk)
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

    def _handle_text_input(self, vk):
        if vk == win32con.VK_ESCAPE:
            self._text_input_field = None
            self._input_buf = ""
            self._build_menu()
            self.speak("Cancelled.")
            return
        if vk == win32con.VK_RETURN:
            if len(self._input_buf) == 5 and self._input_buf[2] == ":":
                self._schedule["time"] = self._input_buf
                self._schedule["enabled"] = True
                if self._text_input_field == "schedule_time_sleep":
                    self._schedule["action"] = "sleep"
                else:
                    self._schedule["action"] = "shutdown"
                self._save_schedule()
                self.speak(f"Scheduled {self._schedule['action']} at {self._input_buf}.")
                self._text_input_field = None
                self._input_buf = ""
                self._build_menu()
            else:
                self.speak("Invalid format. Use HH:MM.")
            return
        if vk == win32con.VK_BACK:
            if self._input_buf:
                self._input_buf = self._input_buf[:-1]
                self.window.update_text(self._input_prompt + " " + self._input_buf)
            return
        if 0x30 <= vk <= 0x39:
            self._input_buf += chr(vk)
            self.window.update_text(self._input_prompt + " " + self._input_buf)
        elif vk == 0xBA:
            self._input_buf += ":"
            self.window.update_text(self._input_prompt + " " + self._input_buf)

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
        if self._check_unsaved():
            self.speak("Warning: Unsaved work in open apps. Proceeding anyway.")
        self._restart_impl()

    def _restart_impl(self):
        self.speak("Restarting Tech-Note.")
        self.window.update_text("Restarting Tech-Note...")
        self.exit_app()
        if self.on_restart:
            self.on_restart()

    def _do_shutdown(self):
        if not self._check_security(self._shutdown_impl): return
        if self._check_unsaved():
            self.speak("Warning: Unsaved work in open apps. Proceeding anyway.")
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
