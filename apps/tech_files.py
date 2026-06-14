import os
import string
import win32con
from core.app_base import SoftApp
from core.config import TECH_SOFT
from core.menu import MenuNode, MenuSystem


def _get_techsoft_drive():
    return os.path.splitdrive(TECH_SOFT)[0].upper()


def _get_drive_list():
    tech_drive = _get_techsoft_drive()
    drives = []
    hd_num = 1
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if os.path.exists(root):
            if root.upper().startswith(tech_drive):
                drives.append(("TechNote 0", root))
            else:
                drives.append((f"HardDisk {hd_num}", root))
                hd_num += 1
    return drives


class TechFiles(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.path = None
        self._show_drives()

    def _show_drives(self):
        self.path = None
        root = MenuNode("Drives")
        for name, root_path in _get_drive_list():
            root.add_child(MenuNode(name, lambda p=root_path: self._open_dir(p)))
        self.menu = MenuSystem(root, self.speak)
        self.speak("File Manager. Drives.")

    def _open_dir(self, path):
        self.path = path
        self.refresh()

    def refresh(self):
        try:
            self.items = sorted(os.listdir(self.path))
        except (FileNotFoundError, PermissionError):
            self.items = []
        self._build_menu()

    def _build_menu(self):
        label = os.path.basename(self.path) or self.path
        root = MenuNode(label)
        root.add_child(MenuNode("Parent Folder", self._go_up, "u"))

        for item in self.items:
            full = os.path.join(self.path, item)
            if os.path.isdir(full):
                root.add_child(MenuNode("Folder: " + item, lambda p=full: self._open_dir(p)))
            else:
                root.add_child(MenuNode(item, lambda p=full: self._open_file(p)))

        if not self.items:
            root.add_child(MenuNode("Empty Folder"))

        self.menu = MenuSystem(root, self.speak)

    def _go_up(self):
        if self.path is None:
            self.speak("Already at drives.")
            return
        parent = os.path.dirname(self.path)
        if parent != self.path:
            self.path = parent
            self.refresh()
        else:
            self._show_drives()

    def _open_file(self, path):
        filename = os.path.basename(path)
        self.speak(f"File: {filename}")

    def _go_techsoft(self):
        self._open_dir(TECH_SOFT)
        self.speak("TechNote 0.")

    def on_focus(self):
        if self.path is None:
            self._show_drives()
        else:
            self._build_menu()
        item = self.menu.get_current_item()
        title = item.title if item else "File Manager"
        self.speak("File Manager. " + title)
        self.window.update_text("Files: " + title)

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        if vk == win32con.VK_F1:
            self._delete_current()
            return

        if self.window.space_down and vk == 0x44:
            self._go_techsoft()
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
        if item and item.title not in ("Parent Folder", "Empty Folder", "Drives"):
            clean = item.title.replace("Folder: ", "")
            full = os.path.join(self.path, clean)
            try:
                if os.path.isfile(full):
                    os.remove(full)
                    self.speak("File deleted.")
                elif os.path.isdir(full):
                    import shutil
                    shutil.rmtree(full)
                    self.speak("Folder deleted.")
                self.refresh()
            except Exception:
                self.speak("Delete failed.")

    def get_help_text(self):
        return "File Manager. Space for next, Backspace for previous. Enter to open. Space+D for TechNote. F1 to delete. Escape to exit."
