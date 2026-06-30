import json
import os
import win32con
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.config import TECH_SOFT

RESUME_PATH = os.path.join(TECH_SOFT, 'resume.json')
SNAPSHOTS_DIR = os.path.join(TECH_SOFT, 'snapshots')


class SessionManagerApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
        self._build_menu()

    def _build_menu(self):
        root = MenuNode("Session Manager")
        root.add_child(MenuNode("Save Current Session", lambda: self._save_session()))
        root.add_child(MenuNode("Restore Last Session", lambda: self._restore_last()))
        snapshots = self._list_snapshots()
        if snapshots:
            for snap in snapshots:
                root.add_child(MenuNode(f"Restore: {snap}", lambda s=snap: self._restore_snapshot(s)))
        if os.path.exists(RESUME_PATH):
            root.add_child(MenuNode("Clear Resume Data", lambda: self._clear_resume()))
        self.menu = MenuSystem(root, self.speak)

    def _save_session(self):
        if not self.manager.current_app:
            self.speak("No active app to save")
            return
        app_module = self.manager.current_app.__class__.__module__
        app_class = self.manager.current_app.__class__.__name__
        data = {"app_module": app_module, "app_class": app_class}
        if hasattr(self.manager.current_app, "get_state"):
            state = self.manager.current_app.get_state()
            if state:
                data["state"] = state
        import time
        name = f"snapshot_{int(time.time())}.json"
        path = os.path.join(SNAPSHOTS_DIR, name)
        try:
            with open(path, 'w') as f:
                json.dump(data, f)
            self.speak("Session saved")
        except Exception as e:
            self.speak(f"Save failed: {e}")

    def _restore_last(self):
        if not os.path.exists(RESUME_PATH):
            self.speak("No saved session")
            return
        self._do_restore(RESUME_PATH)

    def _restore_snapshot(self, name):
        path = os.path.join(SNAPSHOTS_DIR, name)
        if os.path.exists(path):
            self._do_restore(path)

    def _do_restore(self, path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            import importlib
            module = importlib.import_module(data["app_module"])
            app_class = getattr(module, data["app_class"])
            self.manager.launch_app(app_class)
            if "state" in data and hasattr(self.manager.current_app, "set_state"):
                self.manager.current_app.set_state(data["state"])
            self.speak("Session restored")
            self.exit_app()
        except Exception as e:
            self.speak(f"Restore failed: {e}")

    def _clear_resume(self):
        try:
            os.remove(RESUME_PATH)
            self.speak("Resume data cleared")
        except Exception:
            self.speak("Nothing to clear")
        self.exit_app()

    def _list_snapshots(self):
        try:
            return sorted([f for f in os.listdir(SNAPSHOTS_DIR) if f.endswith('.json')], reverse=True)
        except OSError:
            return []

    def on_focus(self):
        self._build_menu()
        self.menu.announce_current()

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
        self._update_display()

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            self._update_display()

    def _update_display(self):
        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Sessions: " + item.title)
