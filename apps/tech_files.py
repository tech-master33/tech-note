import os
import win32con
from core.app_base import SoftApp
from core.config import TECH_SOFT
from core.menu import MenuNode, MenuSystem

class TechFiles(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.path = os.path.join(TECH_SOFT, 'documents')
        os.makedirs(self.path, exist_ok=True)
        self.menu = None
        self.refresh()

    def refresh(self):
        try:
            self.items = sorted(os.listdir(self.path))
        except (FileNotFoundError, PermissionError):
            self.items = []
        self._build_menu()

    def _build_menu(self):
        root = MenuNode(os.path.basename(self.path))
        root.add_child(MenuNode("Parent Folder", self._go_up, "u"))
        
        for item in self.items:
            path = os.path.join(self.path, item)
            if os.path.isdir(path):
                root.add_child(MenuNode("Folder: " + item, lambda p=path: self._open_dir(p)))
            else:
                root.add_child(MenuNode(item, lambda p=path: self._open_file(p)))
        
        if not self.items:
            root.add_child(MenuNode("Empty Folder"))
            
        self.menu = MenuSystem(root, self.speak)

    def _go_up(self):
        parent = os.path.dirname(self.path)
        if parent != self.path:
            self.path = parent
            self.refresh()
            self.on_focus()
        else:
            self.speak("Root folder.")

    def _open_dir(self, path):
        self.path = path
        self.refresh()
        self.on_focus()

    def _open_file(self, path):
        filename = os.path.basename(path)
        if filename.lower().endswith('.json'):
            self.speak(f"Opening {filename} in Word Processor.")
            # We need a way to launch an app with parameters
            # For now, we'll use a hack or just speak
            from apps.tech_edit import TechEdit
            app = self.manager.launch_app(TechEdit)
            if app:
                app._load_file(filename)
        else:
            self.speak(f"File: {filename}")

    def on_focus(self):
        self._build_menu()
        item = self.menu.get_current_item()
        self.speak("File Manager. " + item.title)
        self.window.update_text("Files: " + item.title)

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        if vk == win32con.VK_F1:
            self._delete_current()
            return

        if vk in (win32con.VK_SPACE, win32con.VK_DOWN):
            self.menu.next()
        elif vk in (win32con.VK_BACK, win32con.VK_UP):
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))

        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Files: " + item.title)

    def _delete_current(self):
        item = self.menu.get_current_item()
        if item and item.title not in ("Parent Folder", "Empty Folder"):
            filename = item.title.replace("Folder: ", "")
            path = os.path.join(self.path, filename)
            try:
                if os.path.isfile(path):
                    os.remove(path)
                    self.speak("File deleted.")
                elif os.path.isdir(path):
                    import shutil
                    shutil.rmtree(path)
                    self.speak("Folder deleted.")
                self.refresh()
                self.on_focus()
            except Exception:
                self.speak("Delete failed.")

    def get_help_text(self):
        return "File Manager. Space for next, Backspace for previous. Enter to open. F1 to delete. Press Escape to exit."
