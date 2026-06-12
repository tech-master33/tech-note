import os
import win32con
from core.app_base import SoftApp

class TechFiles(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.path = os.path.join(os.environ['USERPROFILE'], '.tech-soft', 'documents')
        os.makedirs(self.path, exist_ok=True)
        self.items = []
        self.index = 0
        self.refresh()

    def refresh(self):
        try:
            self.items = sorted(os.listdir(self.path))
            self.index = 0
        except FileNotFoundError:
            self.speak("folder not found")
            self.items = []
        except PermissionError:
            self.speak("access denied")
            self.items = []

    def on_focus(self):
        self.speak("File Manager. " + os.path.basename(self.path) + ". F1 delete, F2 parent folder.")
        self.window.update_text("Files: " + os.path.basename(self.path))

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        # Delete file
        if vk == win32con.VK_F1:
            if self.items:
                item_path = os.path.join(self.path, self.items[self.index])
                if os.path.isfile(item_path):
                    os.remove(item_path)
                    self.speak("Deleted")
                    self.refresh()
            return

        # Go up to parent directory
        if vk == win32con.VK_F2:
            parent = os.path.dirname(self.path)
            if parent != self.path:
                self.path = parent
                self.refresh()
                self.speak(os.path.basename(self.path))
            return

        if not self.items:
            self.speak("folder empty")
            return

        if vk == win32con.VK_SPACE or vk == win32con.VK_DOWN:
            self.index = (self.index + 1) % len(self.items)
            self.announce()
        elif vk == win32con.VK_BACK or vk == win32con.VK_UP:
            self.index = (self.index - 1) % len(self.items)
            self.announce()
        elif vk == win32con.VK_RETURN:
            new_path = os.path.join(self.path, self.items[self.index])
            if os.path.isdir(new_path):
                self.path = new_path
                self.refresh()
                self.speak("opening " + os.path.basename(self.path))
            else:
                self.speak("file " + self.items[self.index])

    def announce(self):
        item = self.items[self.index]
        self.speak(item)
        self.window.update_text(item)
