import os
import json
import win32con
import urllib.request
import urllib.error
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.config import TECH_SOFT

CATALOG_URL = "https://steady-licorice-d12c5f.netlify.app/catalog.json"
APPS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "apps")
INSTALLED_FILE = os.path.join(TECH_SOFT, "installed_apps.json")


class AppStore(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.catalog = []
        self.installed = self._load_installed()
        self._build_menu()

    def _load_installed(self):
        if os.path.exists(INSTALLED_FILE):
            try:
                with open(INSTALLED_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_installed(self):
        try:
            os.makedirs(os.path.dirname(INSTALLED_FILE), exist_ok=True)
            with open(INSTALLED_FILE, 'w') as f:
                json.dump(self.installed, f)
        except:
            pass

    def _build_menu(self):
        root = MenuNode("App Store")
        root.add_child(MenuNode("Games", self._show_category))
        root.add_child(MenuNode("Apps", self._show_category))
        root.add_child(MenuNode("My Installed Apps", self._show_installed))
        root.add_child(MenuNode("Refresh Catalog", self._fetch_catalog))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _fetch_catalog(self):
        self.speak("Fetching catalog. Please wait.")
        self.window.update_text("Loading catalog...")
        try:
            req = urllib.request.Request(CATALOG_URL, headers={"User-Agent": "TechNote/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            self.catalog = data.get("apps", [])
            count = len(self.catalog)
            self.speak(f"Found {count} items in catalog.")
            self.window.update_text(f"{count} items found.")
        except urllib.error.URLError:
            self.speak("No internet connection.")
            self.window.update_text("No internet.")
        except Exception:
            self.speak("Failed to load catalog.")
            self.window.update_text("Catalog error.")

    def _show_category(self):
        item = self.menu.get_current_item()
        if not item:
            return
        cat_name = item.title

        if not self.catalog:
            self._fetch_catalog()
        if not self.catalog:
            self.speak("No apps available. Check internet.")
            return

        apps = [a for a in self.catalog if a.get("category", "").lower() == cat_name.lower()]
        if not apps:
            self.speak(f"No {cat_name} available.")
            return

        root = MenuNode(cat_name)
        for app_info in apps:
            name = app_info.get("name", "Unknown")
            app_id = app_info.get("id", name)
            is_installed = app_id in self.installed
            tag = " [Installed]" if is_installed else ""
            root.add_child(MenuNode(f"{name}{tag}", lambda a=app_info: self._show_app(a)))
        root.add_child(MenuNode("Back", self._build_menu_back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _build_menu_back(self):
        self._build_menu()
        self.menu.announce_current()

    def _show_app(self, app_info):
        name = app_info.get("name", "Unknown")
        desc = app_info.get("description", "No description.")
        ver = app_info.get("version", "1.0")
        app_id = app_info.get("id", name)
        is_installed = app_id in self.installed

        root = MenuNode(name)
        root.add_child(MenuNode(f"Version {ver}. {desc}"))
        if is_installed:
            root.add_child(MenuNode("Uninstall", lambda: self._uninstall(app_info)))
        else:
            root.add_child(MenuNode("Install", lambda: self._install(app_info)))
        root.add_child(MenuNode("Back", self._browse_back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _browse_back(self):
        self._build_menu()
        self.menu.announce_current()

    def _install(self, app_info):
        name = app_info.get("name", "Unknown")
        app_id = app_info.get("id", name)
        download_url = app_info.get("download_url", "")
        filename = app_info.get("filename", "")

        if not download_url:
            self.speak("Cannot install. No download URL.")
            return

        self.speak(f"Installing {name}. Please wait.")
        self.window.update_text(f"Installing {name}...")

        try:
            req = urllib.request.Request(download_url, headers={"User-Agent": "TechNote/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                code = resp.read().decode('utf-8')

            if not filename:
                filename = app_id + ".py"

            filepath = os.path.join(APPS_DIR, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)

            self.installed[app_id] = {
                "name": name,
                "filename": filename,
                "version": app_info.get("version", "1.0"),
                "category": app_info.get("category", "Apps"),
                "entry_point": app_info.get("entry_point", ""),
            }
            self._save_installed()

            self.speak(f"{name} installed.")
            self.window.update_text(f"{name} installed.")
            if hasattr(self.manager, 'refresh_main_menu'):
                self.manager.refresh_main_menu()
        except urllib.error.URLError:
            self.speak("Download failed. No internet.")
            self.window.update_text("Download failed.")
        except Exception as e:
            self.speak(f"Install failed.")
            self.window.update_text("Install error.")

    def _uninstall(self, app_info):
        name = app_info.get("name", "Unknown")
        app_id = app_info.get("id", name)

        if app_id not in self.installed:
            self.speak("App not installed.")
            return

        info = self.installed[app_id]
        filename = info.get("filename", "")
        filepath = os.path.join(APPS_DIR, filename)

        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except:
            pass

        del self.installed[app_id]
        self._save_installed()

        self.speak(f"{name} uninstalled.")
        self.window.update_text(f"{name} removed.")
        if hasattr(self.manager, 'refresh_main_menu'):
            self.manager.refresh_main_menu()

    def _show_installed(self):
        if not self.installed:
            self.speak("No apps installed.")
            return

        root = MenuNode("Installed Apps")
        for app_id, info in self.installed.items():
            name = info.get("name", app_id)
            cat = info.get("category", "App")
            root.add_child(MenuNode(f"{name} ({cat})"))
        root.add_child(MenuNode("Back", self._build_menu_back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def on_focus(self):
        item = self.menu.get_current_item()
        title = item.title if item else "App Store"
        self.speak("App Store. " + title)
        self.window.update_text("App Store: " + title)

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
            self.window.update_text("App Store: " + item.title)

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text("App Store: " + item.title)

    def get_help_text(self):
        return "App Store. Browse Games and Apps. Space for next, Backspace for previous. Enter to select."
