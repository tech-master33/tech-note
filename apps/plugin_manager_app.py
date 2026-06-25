import os
import win32con
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.plugin_manager import get_plugin_manager


class PluginManagerApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._pm = get_plugin_manager()
        self._confirm_name = None
        self._build_menu()

    def _build_menu(self):
        root = MenuNode("Plugin Manager")
        if self._confirm_name:
            root.add_child(MenuNode(f"Uninstall {self._confirm_name}?", lambda: self._do_uninstall(self._confirm_name)))
            root.add_child(MenuNode("Cancel", self._cancel_uninstall))
        else:
            plugins = self._pm.get_all_plugin_info()
            if not plugins:
                plugins_node = MenuNode("No plugins installed")
                root.add_child(plugins_node)
            else:
                for p in sorted(plugins, key=lambda x: x['name'].lower()):
                    label = f"{p['name']} ({p['plugin_type']}) v{p['version']}"
                    root.add_child(MenuNode(label, lambda info=p: self._show_detail(info)))
        root.add_child(MenuNode("Install plugin", self._do_install))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _do_install(self):
        path = self._pick_scrugn()
        if path:
            try:
                self._pm.install_plugin(path)
                self.speak("Plugin installed.")
            except Exception as e:
                self.speak(f"Install failed: {e}")
            self._build_menu()
            self.menu.announce_current()

    def _pick_scrugn(self):
        import ctypes
        from ctypes import wintypes
        class OPENFILENAME(ctypes.Structure):
            _fields_ = [
                ("lStructSize", wintypes.DWORD),
                ("hwndOwner", wintypes.HWND),
                ("hInstance", wintypes.HINSTANCE),
                ("lpstrFilter", wintypes.LPCWSTR),
                ("lpstrCustomFilter", wintypes.LPWSTR),
                ("nMaxCustFilter", wintypes.DWORD),
                ("nFilterIndex", wintypes.DWORD),
                ("lpstrFile", wintypes.LPWSTR),
                ("nMaxFile", wintypes.DWORD),
                ("lpstrFileTitle", wintypes.LPWSTR),
                ("nMaxFileTitle", wintypes.DWORD),
                ("lpstrInitialDir", wintypes.LPCWSTR),
                ("lpstrTitle", wintypes.LPCWSTR),
                ("Flags", wintypes.DWORD),
                ("nFileOffset", wintypes.WORD),
                ("nFileExtension", wintypes.WORD),
                ("lpstrDefExt", wintypes.LPCWSTR),
                ("lCustData", wintypes.LPARAM),
                ("lpfnHook", wintypes.LPVOID),
                ("lpTemplateName", wintypes.LPCWSTR),
            ]
        buf = ctypes.create_unicode_buffer(512)
        ofn = OPENFILENAME()
        ofn.lStructSize = ctypes.sizeof(ofn)
        ofn.hwndOwner = None
        ofn.lpstrFilter = "Plugin files (*.scrugn)\0*.scrugn\0All files (*.*)\0*.*\0"
        ofn.lpstrFile = buf
        ofn.nMaxFile = 512
        ofn.Flags = 0x00000800 | 0x00000004
        ofn.lpstrDefExt = "scrugn"
        try:
            if ctypes.windll.comdlg32.GetOpenFileNameW(ctypes.byref(ofn)):
                return buf.value
        except Exception:
            pass
        return None

    def _show_detail(self, info):
        self._build_detail_menu(info)

    def _build_detail_menu(self, info):
        root = MenuNode(info['name'])
        root.add_child(MenuNode(f"Version: {info['version']}"))
        root.add_child(MenuNode(f"Type: {info['plugin_type']}"))
        root.add_child(MenuNode(f"Author: {info['author']}"))
        root.add_child(MenuNode(f"Description: {info['description']}"))
        root.add_child(MenuNode("Uninstall", lambda: self._confirm_uninstall(info['name'])))
        root.add_child(MenuNode("Back", self._build_menu_back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _confirm_uninstall(self, name):
        self._confirm_name = name
        self._build_menu()
        self.menu.announce_current()

    def _cancel_uninstall(self):
        self._confirm_name = None
        self._build_menu()
        self.menu.announce_current()

    def _do_uninstall(self, name):
        try:
            self._pm.uninstall_plugin(name)
            self.speak(f"{name} uninstalled.")
        except Exception as e:
            self.speak(f"Uninstall failed: {e}")
        self._confirm_name = None
        self._build_menu()
        self.menu.announce_current()

    def _build_menu_back(self):
        self._build_menu()
        self.menu.announce_current()

    def on_focus(self):
        self._pm.scan()
        self._build_menu()
        item = self.menu.get_current_item()
        self._announce("Plugin Manager. " + (item.title if item else ""))

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            if self._confirm_name:
                self._cancel_uninstall()
                return
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
