import os
import win32con
import json
import time
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.config import TECH_SOFT, SETTINGS_PATH, ACCOUNT_PATH
import core.error_handler

SCHEDULE_FILE = os.path.join(TECH_SOFT, "power_schedule.json")


class PowerApp(SoftApp):
    def __init__(self, manager, window, on_restart=None, on_exit=None,
                 on_lock=None):
        super().__init__(manager, window)
        self.on_restart = on_restart
        self.on_exit = on_exit
        self.on_lock = on_lock
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
        """Register the 'power-schedule' systmanserv service (30-second
        tick) so a scheduled shutdown/sleep fires while enabled. Replaces
        the old hand-rolled watcher thread."""
        if not (self._schedule.get("enabled") and self._schedule.get("time")):
            return
        from core.systmanserv import get_manager
        m = get_manager()
        m.register(
            "power-schedule",
            description="Fire scheduled shutdown/sleep at the configured time",
            run=self._schedule_tick,
            interval=30,
        )
        m.start("power-schedule")

    def _schedule_tick(self):
        """One check of the power schedule (called by systmanserv). Fires
        once when the current time matches, then disables the schedule so
        later ticks don't re-fire it."""
        if not (self._schedule.get("enabled") and self._schedule.get("time")):
            return
        now = time.localtime()
        current = f"{now.tm_hour:02d}:{now.tm_min:02d}"
        if current != self._schedule.get("time"):
            return
        self._schedule["enabled"] = False
        self._save_schedule()
        if self._schedule.get("action") == "shutdown":
            self._handle_scheduled_shutdown()
        elif self._schedule.get("action") == "sleep":
            self._do_sleep()

    def _handle_scheduled_shutdown(self):
        """Fire a scheduled shutdown. Returns True if the schedule was cancelled
        because of unsaved work in blocking mode; False if shutdown proceeded."""
        self.speak("Scheduled shutdown. Saving work.")
        if self.manager._unsaved_warnings_enabled():
            names = self.manager._unsaved_app_names()
            if names and self.manager._unsaved_blocks_exit():
                self.speak(f"Unsaved work in {names}. Schedule cancelled.")
                return True
        self._shutdown_impl()
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

    def _account_has_credential(self):
        """True if a PIN or password is set, so locking actually protects
        the session. Without one, the lock screen could never be unlocked."""
        try:
            if os.path.exists(ACCOUNT_PATH):
                with open(ACCOUNT_PATH, 'r') as f:
                    acct = json.load(f)
                return bool(acct.get("pin") or acct.get("password"))
        except Exception:
            pass
        return False

    def _build_menu(self):
        root = MenuNode("Power Options")
        root.add_child(MenuNode("Restart Tech-Note", self._do_restart))
        root.add_child(MenuNode("Shutdown Tech-Note", self._do_shutdown))
        if self._account_has_credential():
            root.add_child(MenuNode("Lock Tech-Note", self._do_lock))

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

    def _do_lock(self):
        """Lock Tech-Note. The manager swaps the power menu for the lock
        screen, so a successful unlock resumes the app the power menu had
        interrupted."""
        if self.on_lock:
            self.on_lock()

    def _do_restart(self):
        if not self._check_security(self._restart_impl): return
        self._restart_impl()

    def _restart_impl(self):
        if self._unsaved_blocks_action("Restart"):
            return
        self.speak("Restarting Tech-Note.")
        self.window.update_text("Restarting Tech-Note...")
        self.exit_app()
        if self.on_restart:
            self.on_restart()

    def _do_shutdown(self):
        if not self._check_security(self._shutdown_impl): return
        self._shutdown_impl()

    def _shutdown_impl(self):
        if self._unsaved_blocks_action("Shutdown"):
            return
        if self.on_exit:
            self.on_exit()

    def _do_sleep(self):
        if self._unsaved_blocks_action("Sleep"):
            return
        self.exit_app()
        if hasattr(self.manager, "_exit_app"):
            self.manager._exit_app(mode="sleep")

    def _do_hibernate(self):
        if not self._check_security(self._hibernate_impl): return
        self._hibernate_impl()

    def _hibernate_impl(self):
        if self._unsaved_blocks_action("Hibernate"):
            return
        self.exit_app()
        if hasattr(self.manager, "_exit_app"):
            self.manager._exit_app(mode="hibernate")

    def _unsaved_blocks_action(self, action):
        """If unsaved-work warnings are enabled, unsaved work exists, and the
        block setting is on, abort the action and return the user to the app
        they interrupted. Returns True if aborted."""
        if not self.manager._unsaved_warnings_enabled():
            return False
        names = self.manager._unsaved_app_names()
        if names and self.manager._unsaved_blocks_exit():
            self.speak(f"Unsaved work in {names}. {action} cancelled.")
            self.exit_app()
            return True
        return False
