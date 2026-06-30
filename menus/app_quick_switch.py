import os
import json
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode
from core.config import TECH_SOFT

RECENT_FILE = os.path.join(TECH_SOFT, "recent_apps.json")


class AppQuickSwitch(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._recent = self._load_recent()
        self._build_menu()

    def _load_recent(self):
        try:
            if os.path.exists(RECENT_FILE):
                with open(RECENT_FILE, 'r') as f:
                    return json.load(f)
        except:
            pass
        return []

    def _save_recent(self):
        try:
            with open(RECENT_FILE, 'w') as f:
                json.dump(self._recent[-20:], f)
        except:
            pass

    def add_app(self, app_name, module_path, class_name):
        entry = {"name": app_name, "module": module_path, "class": class_name}
        self._recent = [e for e in self._recent if e.get("name") != app_name]
        self._recent.append(entry)
        self._save_recent()

    def _build_menu(self):
        root = MenuNode("Quick Switch")
        for entry in reversed(self._recent[-10:]):
            name = entry.get("name", "Unknown")
            root.add_child(MenuNode(name, lambda e=entry: self._launch_recent(e)))
        if not self._recent:
            root.add_child(MenuNode("No recent apps"))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _launch_recent(self, entry):
        module_path = entry.get("module", "")
        class_name = entry.get("class", "")
        try:
            import importlib
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            self.manager.launch_app(cls)
        except:
            self.speak("App not found. It may have been removed.")
            self._recent = [e for e in self._recent if e.get("name") != entry.get("name")]
            self._save_recent()
            self._build_menu()
            self.menu.announce_current()

    def on_focus(self):
        self._build_menu()
        item = self.menu.get_current_item()
        self.speak("Quick Switch. " + (item.title if item else ""))

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))
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
        return "Quick Switch. Press Space+Q to open. Navigate with Space and Backspace. Enter to launch. Escape to exit."
