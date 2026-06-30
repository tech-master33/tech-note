import os
import json
import shutil
import datetime
import threading
import time
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode
from core.config import TECH_SOFT

BACKUP_FILES = ["settings.json", "account.json", "notes.json", "habits.json",
                "planner.json", "bookmarks.json", "browser_history.json", "contacts.json",
                "expenses.json", "passwords.json", "app_usage.json"]


class AutoBackup(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._backup_dir = os.path.join(TECH_SOFT, "backups")
        os.makedirs(self._backup_dir, exist_ok=True)
        self._interval_hours = 24
        self._auto_mode = False
        self._thread = None
        self._build_menu()

    def _build_menu(self):
        root = MenuNode("Auto Backup")
        count = len([f for f in os.listdir(self._backup_dir) if f.startswith("backup_")]) if os.path.exists(self._backup_dir) else 0
        root.add_child(MenuNode(f"Backups: {count}"))
        root.add_child(MenuNode("Backup Now", self._backup_now))
        root.add_child(MenuNode("Restore", self._enter_restore))
        root.add_child(MenuNode(f"Auto: {'On' if self._auto_mode else 'Off'}", self._toggle_auto))
        root.add_child(MenuNode(f"Interval: {self._interval_hours}h", self._set_interval))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _backup_now(self):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{ts}"
        backup_path = os.path.join(self._backup_dir, backup_name)
        try:
            os.makedirs(backup_path, exist_ok=True)
            count = 0
            for fname in BACKUP_FILES:
                src = os.path.join(TECH_SOFT, fname)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(backup_path, fname))
                    count += 1
            self.speak(f"Backup saved: {count} files.")
        except:
            self.speak("Backup failed.")

    def _enter_restore(self):
        if not os.path.exists(self._backup_dir):
            self.speak("No backups.")
            return
        backups = sorted([d for d in os.listdir(self._backup_dir) if d.startswith("backup_") and os.path.isdir(os.path.join(self._backup_dir, d))])
        if not backups:
            self.speak("No backups.")
            return
        root = MenuNode("Restore")
        for b in backups:
            root.add_child(MenuNode(b, lambda name=b: self._do_restore(name)))
        root.add_child(MenuNode("Back", self._build_menu_back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _do_restore(self, name):
        backup_path = os.path.join(self._backup_dir, name)
        try:
            count = 0
            for fname in BACKUP_FILES:
                src = os.path.join(backup_path, fname)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(TECH_SOFT, fname))
                    count += 1
            self.speak(f"Restored {count} files from {name}.")
        except:
            self.speak("Restore failed.")
        self._build_menu()
        self.menu.announce_current()

    def _toggle_auto(self):
        self._auto_mode = not self._auto_mode
        if self._auto_mode:
            self._thread = threading.Thread(target=self._auto_loop, daemon=True)
            self._thread.start()
            self.speak(f"Auto backup every {self._interval_hours} hours.")
        else:
            self.speak("Auto backup off.")
        self._build_menu()
        self.menu.announce_current()

    def _auto_loop(self):
        while self._auto_mode:
            time.sleep(self._interval_hours * 3600)
            if self._auto_mode:
                self._backup_now()

    def _set_interval(self):
        self._input_mode = "interval"
        self._input_text = str(self._interval_hours)
        self.speak(f"Interval in hours ({self._interval_hours}). Enter new value.")
        self.window.update_text(f"Interval hours: ")

    def _build_menu_back(self):
        self._build_menu()
        self.menu.announce_current()

    def on_focus(self):
        self._build_menu()
        item = self.menu.get_current_item()
        self.speak("Auto Backup. " + (item.title if item else ""))

    def on_key(self, vk):
        if getattr(self, '_input_mode', None):
            if vk == win32con.VK_ESCAPE:
                self._input_mode = None
                self._build_menu()
                self.menu.announce_current()
                return
            if vk == win32con.VK_RETURN:
                try:
                    v = int(self._input_text.strip())
                    if v > 0:
                        self._interval_hours = v
                        self.speak(f"Interval set to {v} hours.")
                except:
                    self.speak("Invalid.")
                self._input_mode = None
                self._build_menu()
                self.menu.announce_current()
                return
            if vk == win32con.VK_BACK:
                self._input_text = self._input_text[:-1]
                self.window.update_text(self._input_text)
                return
            if 0x30 <= vk <= 0x39:
                self._input_text += chr(vk)
                self.window.update_text(self._input_text)
            return
        if vk == win32con.VK_ESCAPE:
            self._auto_mode = False
            self.exit_app()
            return
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        else:
            self._handle_first_letter_nav(vk, self.menu)
        item = self.menu.get_current_item()
        if item:
            self.window.update_text(item.title)

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text(item.title)

    def get_help_text(self):
        return "Auto Backup. Backup and restore your data. Set automatic interval. Space next, Backspace previous. Escape exit."
