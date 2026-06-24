import os
import win32file
import win32api
import win32con
from core.menu import MenuNode, MenuSystem
from core.config import TECH_SOFT


class FileDialog:
    def __init__(self, manager, window, callback, start_path=None):
        self.manager = manager
        self.window = window
        self.speak = manager.speak
        self.callback = callback
        self.active = False
        self.current_dir = start_path or ''
        self.menu = None

    def start(self):
        self.active = True
        self._show_drives()

    def cancel(self):
        self.active = False
        self.callback(None)

    def _show_drives(self):
        self.current_dir = ''
        drives = self._get_drives()
        root = MenuNode("Select Drive")
        for d in drives:
            root.add_child(MenuNode(d['label'], lambda d=d: self._open_drive(d)))
        self.menu = MenuSystem(root, self.speak)
        self.speak("Select a drive")
        self.window.update_text("Drives")

    def _get_drives(self):
        drives = []
        drives.append({'path': TECH_SOFT, 'label': "Tech-Note"})

        # Add real drives, rename C: to Windows
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            path = letter + ':\\'
            if os.path.exists(path):
                try:
                    type_code = win32file.GetDriveTypeW(path)
                    type_map = {
                        win32file.DRIVE_FIXED: "Local",
                        win32file.DRIVE_REMOVABLE: "Removable",
                        win32file.DRIVE_CDROM: "CD-ROM",
                        win32file.DRIVE_REMOTE: "Network",
                    }
                    label = type_map.get(type_code, "")
                    try:
                        vol = win32api.GetVolumeInformation(path)
                        if path.upper() == 'C:\\':
                            label = "Windows (C:)"
                        elif vol[0]:
                            label = f"{vol[0]} ({letter}:)"
                        else:
                            label = f"Drive {letter} ({label})" if label else f"Drive {letter}"
                    except Exception:
                        label = f"Drive {letter} ({label})" if label else f"Drive {letter}"
                    drives.append({'path': path, 'label': label})
                except Exception:
                    drives.append({'path': path, 'label': f"Drive {letter}"})
        return drives

    def _open_drive(self, drive):
        self.current_dir = drive['path']
        self._show_dir()

    def _show_dir(self):
        try:
            items = self._list_dir(self.current_dir)
        except Exception:
            self.speak("Cannot access folder.")
            self._go_up()
            return
        title = os.path.basename(self.current_dir.rstrip('\\')) or self.current_dir
        # If current dir is TECH_SOFT, show "Tech-Note" as header
        if os.path.abspath(self.current_dir) == os.path.abspath(TECH_SOFT):
            title = "Tech-Note"
        root = MenuNode(title)
        root.add_child(MenuNode("..", lambda: self._go_up()))
        for item in items:
            if item['is_dir']:
                root.add_child(MenuNode(item['name'], lambda i=item: self._enter_dir(i)))
            else:
                root.add_child(MenuNode(item['name'], lambda i=item: self._select_file(i)))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _list_dir(self, path):
        items = []
        try:
            for name in os.listdir(path):
                if name == '.tech-soft':
                    continue
                full = os.path.join(path, name)
                try:
                    is_dir = os.path.isdir(full)
                    items.append({'name': name, 'path': full, 'is_dir': is_dir})
                except Exception:
                    pass
        except Exception:
            pass
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        return items

    def _go_up(self):
        if not self.current_dir:
            self.cancel()
            return
        # At Tech-Note root, go to drives
        if os.path.abspath(self.current_dir) == os.path.abspath(TECH_SOFT):
            self._show_drives()
            return
        parent = os.path.dirname(self.current_dir.rstrip('\\'))
        if parent == self.current_dir.rstrip('\\'):
            self._show_drives()
        else:
            self.current_dir = parent
            self._show_dir()

    def _enter_dir(self, item):
        self.current_dir = item['path']
        self._show_dir()

    def _select_file(self, item):
        self.active = False
        self.callback(item['path'])

    def _update_window(self):
        if self.menu:
            item = self.menu.get_current_item()
            if item:
                self.window.update_text(item.title)

    def on_key(self, vk):
        if not self.active:
            return False
        if vk == win32con.VK_ESCAPE:
            self.cancel()
            return True
        if vk == win32con.VK_BACK:
            if self.menu:
                self.menu.previous()
            self._update_window()
            return True
        if vk == win32con.VK_RETURN:
            if self.menu:
                self.menu.select()
            return True
        if 0x41 <= vk <= 0x5A:
            if self.menu:
                self.menu.first_letter_nav(chr(vk))
            self._update_window()
            return True
        return False

    def on_key_up(self, vk):
        if not self.active:
            return False
        if vk == win32con.VK_SPACE and not getattr(self.manager, 'space_used_in_chord', False):
            if self.menu:
                self.menu.next()
            self._update_window()
            return True
        return False
