import os
import importlib
import win32con
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem


def _get_app_list():
    apps_dir = os.path.join(os.path.dirname(__file__), '..', 'apps')
    apps_dir = os.path.abspath(apps_dir)
    results = []
    if os.path.exists(apps_dir):
        for f in sorted(os.listdir(apps_dir)):
            if f.endswith('.py') and not f.startswith('_'):
                name = f[:-3].replace('_', ' ').title()
                results.append((name, f[:-3]))
    menus_dir = os.path.join(os.path.dirname(__file__))
    if os.path.exists(menus_dir):
        for f in sorted(os.listdir(menus_dir)):
            if f.endswith('.py') and f not in ('__init__.py', 'run_dialog.py'):
                name = f[:-3].replace('_', ' ').title()
                results.append((name, 'menus.' + f[:-3]))
    return results


class RunDialog(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.all_apps = _get_app_list()
        self._build_menu("")

    def _build_menu(self, query):
        root = MenuNode("Run")
        q = query.lower()
        matches = [(n, m) for n, m in self.all_apps if q in n.lower()]
        if not matches:
            root.add_child(MenuNode("No matching apps"))
        else:
            for name, module in matches:
                root.add_child(MenuNode(name, lambda m=module: self._launch(m)))
        self.menu = MenuSystem(root, self.speak)
        if query:
            self.menu.search(query)

    def _launch(self, module_name):
        try:
            if module_name.startswith('menus.'):
                mod = importlib.import_module(module_name)
            else:
                mod = importlib.import_module('apps.' + module_name)
            app_class = getattr(mod, 'get_app_class', None)
            if app_class is None:
                for attr in dir(mod):
                    obj = getattr(mod, attr)
                    if isinstance(obj, type) and issubclass(obj, SoftApp) and obj is not SoftApp:
                        app_class = obj
                        break
            if app_class:
                self.manager.launch_app(app_class)
        except Exception as e:
            self.speak(f"Failed to launch: {e}")

    def on_focus(self):
        self._start_text_input("App name: ", self._on_input)

    def _on_input(self, text):
        if text:
            self._build_menu(text)
            self.menu.announce_current()

    def on_key(self, vk):
        if self._handle_text_input(vk):
            return
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
