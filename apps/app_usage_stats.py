import os
import json
import datetime
import threading
import time
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode
from core.config import TECH_SOFT

DATA_FILE = os.path.join(TECH_SOFT, "app_usage.json")


class AppUsageStats(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.stats = self._load_data()
        self._tracking = False
        self._current_app = None
        self._session_start = None
        self._build_menu()

    def _load_data(self):
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}

    def _save_data(self):
        try:
            os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
            with open(DATA_FILE, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except:
            pass

    def _build_menu(self):
        root = MenuNode("App Usage Stats")
        root.add_child(MenuNode("Refresh", self._build_menu_refresh))
        if self.stats:
            sorted_apps = sorted(self.stats.items(), key=lambda x: x[1].get("total_seconds", 0), reverse=True)
            for name, data in sorted_apps[:20]:
                total = data.get("total_seconds", 0)
                h, m = divmod(int(total), 3600)
                mi, s = divmod(m, 60)
                time_str = f"{h}h {mi}m" if h else f"{mi}m {s}s"
                today = data.get("dates", {}).get(datetime.date.today().isoformat(), 0)
                t_min, t_sec = divmod(int(today), 60)
                today_str = f"{t_min}m today" if t_min else f"{t_sec}s today"
                root.add_child(MenuNode(f"{name}: {time_str} ({today_str})"))
        else:
            root.add_child(MenuNode("No data yet"))
        root.add_child(MenuNode("Reset Stats", self._reset))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _build_menu_refresh(self):
        self._build_menu()
        self.menu.announce_current()

    def _reset(self):
        self.stats = {}
        self._save_data()
        self.speak("Stats reset.")
        self._build_menu()
        self.menu.announce_current()

    def log_app_use(self, app_name, seconds):
        if app_name not in self.stats:
            self.stats[app_name] = {"total_seconds": 0, "dates": {}}
        self.stats[app_name]["total_seconds"] = self.stats[app_name].get("total_seconds", 0) + seconds
        today = datetime.date.today().isoformat()
        self.stats[app_name].setdefault("dates", {})
        self.stats[app_name]["dates"][today] = self.stats[app_name]["dates"].get(today, 0) + seconds
        self._save_data()

    def on_focus(self):
        self._build_menu()
        item = self.menu.get_current_item()
        self.speak("App Usage Stats. " + (item.title if item else ""))

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
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
        return "App Usage Stats. View time spent in each app. Space next, Backspace previous. Escape exit."
