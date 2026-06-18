import os
import json
import datetime
import win32con
import urllib.request
import urllib.error
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.config import TECH_SOFT

CATALOG_URL = "https://tech-note.surge.sh/catalog.json"
APPS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "apps")
INSTALLED_FILE = os.path.join(TECH_SOFT, "installed_apps.json")
FAVORITES_FILE = os.path.join(TECH_SOFT, "favorites.json")
DOWNLOADS_FILE = os.path.join(TECH_SOFT, "download_counts.json")
CATALOG_CACHE = os.path.join(TECH_SOFT, "catalog_cache.json")

CATEGORIES = ["Games", "Productivity", "Utilities", "Media"]


def _version_newer(v1, v2):
    try:
        parts1 = [int(x) for x in v1.split(".")]
        parts2 = [int(x) for x in v2.split(".")]
        return parts1 > parts2
    except:
        return False


def _is_new(app_info):
    added = app_info.get("added_date", "")
    if not added:
        return False
    try:
        added_date = datetime.date.fromisoformat(added)
        return (datetime.date.today() - added_date).days <= 7
    except:
        return False


class AppStore(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.catalog = []
        self.installed = self._load_json(INSTALLED_FILE, {})
        self.favorites = self._load_json(FAVORITES_FILE, [])
        self.downloads = self._load_json(DOWNLOADS_FILE, {})
        self._history = []
        self._search_mode = False
        self._search_text = ""
        self._confirm_delete = None
        self._build_menu()

    def _load_json(self, path, default):
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return default

    def _save_json(self, path, data):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        except:
            pass

    def _save_installed(self):
        self._save_json(INSTALLED_FILE, self.installed)

    def _save_favorites(self):
        self._save_json(FAVORITES_FILE, self.favorites)

    def _save_downloads(self):
        self._save_json(DOWNLOADS_FILE, self.downloads)

    def _push_history(self):
        self._history.append(self.menu)

    def _pop_history(self):
        if self._history:
            self.menu = self._history.pop()
            self.menu.announce_current()
            return True
        return False

    def _build_menu(self):
        root = MenuNode("App Store")
        root.add_child(MenuNode("Search", self._start_search))
        root.add_child(MenuNode("Favorites", self._show_favorites))
        for cat in CATEGORIES:
            root.add_child(MenuNode(cat, self._show_category))
        root.add_child(MenuNode("My Installed Apps", self._show_installed))
        root.add_child(MenuNode("Refresh Catalog", self._fetch_catalog))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _start_search(self):
        self._search_mode = True
        self._search_text = ""
        self.speak("Type to search apps. Enter to search. Escape to cancel.")
        self.window.update_text("Search: ")

    def _do_search(self):
        self._search_mode = False
        query = self._search_text.strip().lower()
        if not query:
            self.speak("No search text.")
            return
        if not self.catalog:
            self._fetch_catalog()
        if not self.catalog:
            self.speak("No catalog available.")
            return
        results = [a for a in self.catalog if query in a.get("name", "").lower() or query in a.get("description", "").lower()]
        if not results:
            self.speak("No results found.")
            return
        self._push_history()
        root = MenuNode(f"Search: {self._search_text}")
        for app_info in results:
            root.add_child(MenuNode(self._app_label(app_info), lambda a=app_info: self._show_app(a)))
        root.add_child(MenuNode("Back", self._back_from_search))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _back_from_search(self):
        if self._pop_history():
            return
        self._build_menu()
        self.menu.announce_current()

    def _show_favorites(self):
        if not self.favorites:
            self.speak("No favorites yet.")
            return
        if not self.catalog:
            self._fetch_catalog()
        fav_apps = [a for a in self.catalog if a.get("id", a.get("name", "")) in self.favorites]
        if not fav_apps:
            self.speak("No favorites found in catalog.")
            return
        self._push_history()
        root = MenuNode("Favorites")
        for app_info in fav_apps:
            root.add_child(MenuNode(self._app_label(app_info), lambda a=app_info: self._show_app(a)))
        root.add_child(MenuNode("Back", self._back_from_favorites))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _back_from_favorites(self):
        if self._pop_history():
            return
        self._build_menu()
        self.menu.announce_current()

    def _app_label(self, app_info):
        name = app_info.get("name", "Unknown")
        app_id = app_info.get("id", name)
        tags = []
        if app_id in self.favorites:
            tags.append("*")
        if _is_new(app_info):
            tags.append("New")
        if app_id in self.installed:
            installed_ver = self.installed[app_id].get("version", "0")
            catalog_ver = app_info.get("version", "0")
            if _version_newer(catalog_ver, installed_ver):
                tags.append("Update")
            else:
                tags.append("Installed")
        dl = self.downloads.get(app_id, 0)
        if dl > 0:
            tags.append(f"{dl} dl")
        tag_str = f" [{', '.join(tags)}]" if tags else ""
        return f"{name}{tag_str}"

    def _fetch_catalog(self):
        self.speak("Fetching catalog. Please wait.")
        self.window.update_text("Loading catalog...")
        try:
            req = urllib.request.Request(CATALOG_URL, headers={"User-Agent": "TechNote/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            self.catalog = data.get("apps", [])
            self._save_json(CATALOG_CACHE, self.catalog)
            count = len(self.catalog)
            self.speak(f"Found {count} items in catalog.")
            self.window.update_text(f"{count} items found.")
        except urllib.error.URLError:
            cached = self._load_json(CATALOG_CACHE, [])
            if cached:
                self.catalog = cached
                self.speak(f"Offline. Using cached catalog. {len(self.catalog)} items.")
            else:
                self.speak("No internet connection and no cached catalog.")
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

        self._push_history()
        root = MenuNode(cat_name)
        for app_info in apps:
            root.add_child(MenuNode(self._app_label(app_info), lambda a=app_info: self._show_app(a)))
        root.add_child(MenuNode("Back", self._back_from_category))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _back_from_category(self):
        if self._pop_history():
            return
        self._build_menu()
        self.menu.announce_current()

    def _show_app(self, app_info):
        name = app_info.get("name", "Unknown")
        desc = app_info.get("description", "No description.")
        ver = app_info.get("version", "1.0")
        app_id = app_info.get("id", name)
        is_installed = app_id in self.installed
        is_fav = app_id in self.favorites
        dl = self.downloads.get(app_id, 0)

        self._push_history()
        root = MenuNode(name)
        root.add_child(MenuNode(f"Version {ver}. {desc}"))

        features = app_info.get("features", [])
        if features:
            root.add_child(MenuNode(f"Features: {', '.join(features)}"))

        controls = app_info.get("controls", [])
        if controls:
            root.add_child(MenuNode(f"Controls: {', '.join(controls)}"))

        if dl > 0:
            root.add_child(MenuNode(f"Downloaded {dl} times"))

        if _is_new(app_info):
            root.add_child(MenuNode("Newly added!"))

        if is_installed:
            installed_ver = self.installed[app_id].get("version", "0")
            has_update = _version_newer(ver, installed_ver)
            if has_update:
                root.add_child(MenuNode(f"Update (v{installed_ver} -> v{ver})", lambda: self._update_app(app_info)))
            root.add_child(MenuNode("Uninstall", lambda: self._start_uninstall(app_info)))
        else:
            root.add_child(MenuNode("Install", lambda: self._install(app_info)))

        if is_fav:
            root.add_child(MenuNode("Remove from Favorites", lambda: self._toggle_favorite(app_id)))
        else:
            root.add_child(MenuNode("Add to Favorites", lambda: self._toggle_favorite(app_id)))

        root.add_child(MenuNode("Back", self._back_from_app))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _back_from_app(self):
        if self._pop_history():
            return
        self._build_menu()
        self.menu.announce_current()

    def _toggle_favorite(self, app_id):
        if app_id in self.favorites:
            self.favorites.remove(app_id)
            self.speak("Removed from favorites.")
        else:
            self.favorites.append(app_id)
            self.speak("Added to favorites.")
        self._save_favorites()

    def _start_uninstall(self, app_info):
        name = app_info.get("name", "Unknown")
        self._confirm_delete = app_info
        self.speak(f"Are you sure you want to uninstall {name}? Enter to confirm, Escape to cancel.")
        self.window.update_text(f"Uninstall {name}? Enter=Yes, Esc=No")

    def _confirm_uninstall(self):
        app_info = self._confirm_delete
        self._confirm_delete = None
        if app_info:
            self._uninstall(app_info)

    def _cancel_uninstall(self):
        self._confirm_delete = None
        self.speak("Uninstall cancelled.")

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
            os.makedirs(APPS_DIR, exist_ok=True)
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

            self.downloads[app_id] = self.downloads.get(app_id, 0) + 1
            self._save_downloads()

            self.speak(f"{name} installed.")
            self.window.update_text(f"{name} installed.")
            if hasattr(self.manager, 'refresh_main_menu'):
                self.manager.refresh_main_menu()
        except urllib.error.URLError:
            self.speak("Download failed. No internet.")
            self.window.update_text("Download failed.")
        except Exception:
            self.speak("Install failed.")
            self.window.update_text("Install error.")

    def _update_app(self, app_info):
        name = app_info.get("name", "Unknown")
        app_id = app_info.get("id", name)
        download_url = app_info.get("download_url", "")
        filename = app_info.get("filename", "")

        if not download_url:
            self.speak("Cannot update. No download URL.")
            return

        self.speak(f"Updating {name}. Please wait.")
        self.window.update_text(f"Updating {name}...")

        try:
            os.makedirs(APPS_DIR, exist_ok=True)
            req = urllib.request.Request(download_url, headers={"User-Agent": "TechNote/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                code = resp.read().decode('utf-8')

            if app_id in self.installed:
                filename = self.installed[app_id].get("filename", filename)

            if not filename:
                filename = app_id + ".py"

            filepath = os.path.join(APPS_DIR, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)

            self.installed[app_id]["version"] = app_info.get("version", "1.0")
            self._save_installed()

            self.speak(f"{name} updated to version {app_info.get('version', '1.0')}.")
            self.window.update_text(f"{name} updated.")
        except urllib.error.URLError:
            self.speak("Download failed. No internet.")
            self.window.update_text("Download failed.")
        except Exception:
            self.speak("Update failed.")
            self.window.update_text("Update error.")

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

        self._push_history()
        root = MenuNode("Installed Apps")
        for app_id, info in self.installed.items():
            name = info.get("name", app_id)
            cat = info.get("category", "App")
            ver = info.get("version", "?")

            catalog_ver = None
            for a in self.catalog:
                if a.get("id", a.get("name", "")) == app_id:
                    catalog_ver = a.get("version")
                    break

            tag = ""
            if catalog_ver and _version_newer(catalog_ver, ver):
                tag = f" [Update: v{catalog_ver}]"

            root.add_child(MenuNode(f"{name} v{ver} ({cat}){tag}"))
        root.add_child(MenuNode("Back", self._back_from_installed))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _back_from_installed(self):
        if self._pop_history():
            return
        self._build_menu()
        self.menu.announce_current()

    def on_focus(self):
        if self._search_mode:
            self.window.update_text(f"Search: {self._search_text}")
            return
        item = self.menu.get_current_item()
        title = item.title if item else "App Store"
        installed_count = len(self.installed)
        self.speak(f"App Store. {installed_count} apps installed. {title}")
        self.window.update_text(f"App Store: {title}")

    def on_key(self, vk):
        if self._confirm_delete:
            if vk == win32con.VK_RETURN:
                self._confirm_uninstall()
                return
            if vk == win32con.VK_ESCAPE:
                self._cancel_uninstall()
                return
            return

        if self._search_mode:
            if vk == win32con.VK_ESCAPE:
                self._search_mode = False
                self.speak("Search cancelled.")
                return
            if vk == win32con.VK_RETURN:
                self._do_search()
                return
            if vk == win32con.VK_BACK:
                self._search_text = self._search_text[:-1]
                self.window.update_text(f"Search: {self._search_text}")
                return
            ch = self._vk_to_char(vk)
            if ch:
                self._search_text += ch
                self.window.update_text(f"Search: {self._search_text}")
            return

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
        if self._confirm_delete or self._search_mode:
            return
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text("App Store: " + item.title)

    def get_help_text(self):
        if self._confirm_delete:
            return "Confirm uninstall? Enter to confirm, Escape to cancel."
        if self._search_mode:
            return "Type to search. Enter to search. Escape to cancel."
        return "App Store. Space next, Backspace previous, Enter select, S search."
