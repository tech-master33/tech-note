import os
import string
import win32con
import win32file
import win32api
from core.app_base import SoftApp
from core.config import TECH_SOFT
from core.menu import MenuNode, MenuSystem


def _get_techsoft_drive():
    return os.path.splitdrive(TECH_SOFT)[0].upper()


def _get_volume_label(root):
    try:
        info = win32api.GetVolumeInformation(root)
        return info[0]
    except Exception:
        return ""


def _get_drive_type(root):
    return win32file.GetDriveTypeW(root)


def _get_drive_list():
    tech_drive = _get_techsoft_drive()
    drives = []
    drive_num = 1
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if not os.path.exists(root):
            continue
        drv_type = _get_drive_type(root)
        if root.upper().startswith(tech_drive):
            drives.append(("Tech-Note", root))
        elif drv_type == win32file.DRIVE_REMOVABLE:
            drives.append(("External", root))
        elif drv_type == win32file.DRIVE_CDROM:
            drives.append(("CD-ROM", root))
        elif drv_type == win32file.DRIVE_REMOTE:
            drives.append(("Network", root))
        else:
            label = _get_volume_label(root)
            if label:
                drives.append((label, root))
            else:
                name = "Drive" if drive_num == 1 else f"Drive {drive_num}"
                drives.append((name, root))
                drive_num += 1
    return drives


class TechFiles(SoftApp):
    DRIVE_MENU = 0
    FILE_MENU = 1

    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.drives = _get_drive_list()
        self.drive_index = 0
        self.path = None
        self.state = self.FILE_MENU
        self._saved_menu = None
        self._open_drive(0)

    def _open_drive(self, index):
        if 0 <= index < len(self.drives):
            self.drive_index = index
            name, root_path = self.drives[index]
            self.path = root_path
            self.speak(f"File Manager. {name}")
            self.state = self.FILE_MENU
            self.refresh()

    def _show_drive_menu(self):
        self._saved_menu = self.menu
        root = MenuNode("Switch Drive")
        for i, (name, root_path) in enumerate(self.drives):
            root.add_child(MenuNode(name, lambda idx=i: self._open_drive(idx)))
        self.menu = MenuSystem(root, self.speak)
        self.state = self.DRIVE_MENU
        self.speak("Switch Drive. " + self.menu.get_current_item().title)

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
            return
        parent = os.path.dirname(self.path)
        if parent != self.path:
            self.path = parent
            self.refresh()
        else:
            self.speak("Root of drive.")

    def _open_file(self, path):
        filename = os.path.basename(path)
        self.speak(f"File: {filename}")

    def on_focus(self):
        if self.state == self.DRIVE_MENU:
            return
        self._build_menu()
        item = self.menu.get_current_item()
        title = item.title if item else "File Manager"
        self.window.update_text("Files: " + title)
        self.speak("File Manager. " + title)

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            if self.state == self.DRIVE_MENU:
                self.menu = self._saved_menu
                self.state = self.FILE_MENU
                item = self.menu.get_current_item()
                if item:
                    self.window.update_text("Files: " + item.title)
                return
            self.exit_app()
            return

        if vk == win32con.VK_F1 and self.state == self.FILE_MENU:
            self._delete_current()
            return

        if self.window.space_down and vk == 0x44:
            self._show_drive_menu()
            return

        if vk == win32con.VK_DOWN:
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
        return "File Manager. Down for next, Backspace for previous. Enter to open. Space+D for drive menu. F1 to delete. Escape to exit."
