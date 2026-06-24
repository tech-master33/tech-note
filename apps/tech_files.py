import os
import time
import string
import shutil
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
                name = f"Drive {drive_num}"
                drives.append((name, root))
                drive_num += 1
    return drives


def _format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def _format_date(timestamp):
    try:
        t = time.localtime(timestamp)
        return time.strftime("%B %d, %Y", t)
    except:
        return "Unknown"


SORT_MODES = ["Name", "Date", "Size", "Type"]


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
        self.items = []
        self.sort_mode = 0
        self.clipboard = None
        self.input_mode = None
        self.input_buf = ""
        self.confirm_delete = False
        self._overwrite_confirm = False
        self._pending_paste = None
        self._selected = set()
        self._multi_select = False
        self._open_drive(0)

    def _open_drive(self, index):
        if 0 <= index < len(self.drives):
            self.drive_index = index
            name, root_path = self.drives[index]
            self.path = root_path
            self.state = self.FILE_MENU
            self.refresh()

    def _display_path(self):
        if not self.path:
            return "File Manager"
        label, root = self.drives[self.drive_index]
        relative = self.path[len(root):]
        if relative:
            return f"{label}:{os.sep}{relative}"
        return f"{label}:{os.sep}"

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
            self.items = os.listdir(self.path)
        except (FileNotFoundError, PermissionError):
            self.items = []
        self._sort_items()
        self._build_menu()

    def _sort_items(self):
        mode = SORT_MODES[self.sort_mode]
        items_with_info = []
        for item in self.items:
            full = os.path.join(self.path, item)
            try:
                is_dir = os.path.isdir(full)
                stat = os.stat(full)
                items_with_info.append((item, is_dir, stat.st_mtime, stat.st_size))
            except:
                items_with_info.append((item, False, 0, 0))

        if mode == "Name":
            items_with_info.sort(key=lambda x: x[0].lower())
        elif mode == "Date":
            items_with_info.sort(key=lambda x: x[2], reverse=True)
        elif mode == "Size":
            items_with_info.sort(key=lambda x: (x[1], -x[3]))
        elif mode == "Type":
            items_with_info.sort(key=lambda x: (not x[1], x[0].lower()))

        self.items = [x[0] for x in items_with_info]

    def _build_menu(self):
        label = os.path.basename(self.path) or self.path
        root = MenuNode(label)
        root.add_child(MenuNode("Parent Folder", self._go_up, "u"))

        for item in self.items:
            full = os.path.join(self.path, item)
            prefix = "+ " if item in self._selected else "  "
            if os.path.isdir(full):
                root.add_child(MenuNode(f"{prefix}Folder: {item}", lambda p=full: self._open_dir(p)))
            else:
                root.add_child(MenuNode(f"{prefix}{item}", lambda p=full: self._open_file(p)))

        if not self.items:
            root.add_child(MenuNode("Empty Folder"))

        self.menu = MenuSystem(root, self.speak)
        self._announce_folder()

    def _announce_folder(self):
        count = len(self.items)
        path = self._display_path()
        sort = SORT_MODES[self.sort_mode]
        self.speak(f"{path}. {count} item{'s' if count != 1 else ''}. Sorted by {sort}.")
        item = self.menu.get_current_item()
        if item:
            self.window.update_text(f"{path} - {item.title}")

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
        ext = os.path.splitext(filename)[1].lower()
        text_exts = {'.txt', '.py', '.md', '.json', '.xml', '.html', '.css', '.js', '.ini', '.cfg', '.log', '.csv'}
        audio_exts = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.wma'}
        if ext in audio_exts:
            from apps.media_player import MediaPlayerApp
            self.manager.current_app = MediaPlayerApp(self.manager, self.window)
            self.manager.current_app.on_focus()
            if hasattr(self.manager.current_app, 'load_file'):
                self.manager.current_app.load_file(path)
        elif ext in text_exts:
            from apps.tech_edit import TechEdit
            te = TechEdit(self.manager, self.window)
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    te.text = f.read()
                te.cursor = len(te.text)
                te.filename = filename
            except:
                pass
            self.manager.current_app = te
            te.on_focus()
            te.speak(f"Opened {filename}.")
        else:
            self.speak(f"File: {filename}. Cannot open this file type.")

    def _show_file_info(self):
        item = self.menu.get_current_item()
        if not item or item.title in ("Parent Folder", "Empty Folder"):
            return
        clean = item.title.replace("Folder: ", "")
        full = os.path.join(self.path, clean)
        try:
            stat = os.stat(full)
            is_dir = os.path.isdir(full)
            size = _format_size(stat.st_size) if not is_dir else f"{len(os.listdir(full))} items"
            modified = _format_date(stat.st_mtime)
            read_only = "Read-only" if os.access(full, os.W_OK) == False else "Read-write"
            if is_dir:
                self.speak(f"{clean}. Folder. {size}. Modified {modified}.")
            else:
                self.speak(f"{clean}. {size}. Modified {modified}. {read_only}.")
        except Exception:
            self.speak("Cannot read file info.")

    def on_focus(self):
        if self.state == self.DRIVE_MENU:
            return
        self.refresh()

    def on_key(self, vk):
        if self.input_mode:
            self._handle_input(vk)
            return

        if self.confirm_delete:
            self._handle_delete_confirm(vk)
            return

        if self._overwrite_confirm:
            self._overwrite_confirm = False
            if vk == win32con.VK_RETURN and self._pending_paste:
                src, dst = self._pending_paste
                self._pending_paste = None
                self._do_paste(src, dst)
            elif vk == win32con.VK_ESCAPE:
                self._pending_paste = None
                self.speak("Cancelled.")
            return

        if vk == win32con.VK_ESCAPE:
            if self.state == self.DRIVE_MENU:
                self.menu = self._saved_menu
                self.state = self.FILE_MENU
                item = self.menu.get_current_item()
                if item:
                    self.window.update_text(f"{self._display_path()} - {item.title}")
                return
            self.exit_app()
            return

        if vk == win32con.VK_SPACE and (win32api.GetAsyncKeyState(win32con.VK_CONTROL) & 0x8000):
            self._toggle_multi()
            return

        if vk == win32con.VK_F1 and self.state == self.FILE_MENU:
            self._delete_current()
            return

        if vk == win32con.VK_F2 and self.state == self.FILE_MENU:
            self._rename_current()
            return

        if vk == win32con.VK_F3 and self.state == self.FILE_MENU:
            self._new_folder()
            return

        if vk == win32con.VK_F4 and self.state == self.FILE_MENU:
            self._new_file()
            return

        if vk == win32con.VK_F6 and self.state == self.FILE_MENU:
            if win32api.GetAsyncKeyState(win32con.VK_SHIFT) & 0x8000:
                self._cut_current()
            else:
                self._copy_current()
            return

        if vk == 0x49 and self.state == self.FILE_MENU:
            self._show_file_info()
            return

        if self.window.space_down and vk == 0x44:
            self._show_drive_menu()
            return

        if vk == win32con.VK_F5:
            self.sort_mode = (self.sort_mode + 1) % len(SORT_MODES)
            self.speak(f"Sorted by {SORT_MODES[self.sort_mode]}.")
            self.refresh()
            return

        if vk == win32con.VK_F7:
            self._start_search()
            return

        if self.clipboard and vk == win32con.VK_F8:
            self._paste()
            return

        if vk == win32con.VK_F9 and self.clipboard:
            self.clipboard = None
            self.speak("Clipboard cleared.")
            return

        if vk == win32con.VK_F10:
            if win32api.GetAsyncKeyState(win32con.VK_SHIFT) & 0x8000:
                self._unzip_current()
            else:
                self._zip_selected()
            return

        if self._multi_select:
            if vk == win32con.VK_SPACE and self.window.space_down:
                pass
            elif vk == win32con.VK_SPACE or vk == win32con.VK_RETURN:
                self._select_current()
                return

        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))

        item = self.menu.get_current_item()
        if item:
            self.window.update_text(f"{self._display_path()} - {item.title}")

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text(f"{self._display_path()} - {item.title}")

    def _delete_current(self):
        item = self.menu.get_current_item()
        if not item or item.title in ("Parent Folder", "Empty Folder"):
            return
        clean = item.title.replace("Folder: ", "")
        self.confirm_delete = True
        self.speak(f"Delete {clean}? Press Enter to confirm, Escape to cancel.")
        self.window.update_text(f"Delete {clean}? Enter=Yes, Escape=No")

    def _handle_delete_confirm(self, vk):
        self.confirm_delete = False
        if vk == win32con.VK_RETURN:
            item = self.menu.get_current_item()
            if item and item.title not in ("Parent Folder", "Empty Folder"):
                clean = item.title.replace("Folder: ", "")
                full = os.path.join(self.path, clean)
                try:
                    if os.path.isfile(full):
                        os.remove(full)
                        self.speak("File deleted.")
                    elif os.path.isdir(full):
                        shutil.rmtree(full)
                        self.speak("Folder deleted.")
                    self.refresh()
                except Exception:
                    self.speak("Delete failed.")
        else:
            self.speak("Cancelled.")
            item = self.menu.get_current_item()
            if item:
                self.window.update_text(f"{self._display_path()} - {item.title}")

    def _rename_current(self):
        item = self.menu.get_current_item()
        if not item or item.title in ("Parent Folder", "Empty Folder"):
            return
        clean = item.title.replace("Folder: ", "")
        self.input_mode = "rename"
        self.input_buf = clean
        self.speak(f"Rename {clean}. Enter new name.")
        self.window.update_text(f"Rename: {clean}")

    def _new_folder(self):
        self.input_mode = "new_folder"
        self.input_buf = ""
        self.speak("Enter folder name.")
        self.window.update_text("New Folder: ")

    def _new_file(self):
        self.input_mode = "new_file"
        self.input_buf = ""
        self.speak("Enter filename.")
        self.window.update_text("New File: ")

    def _copy_current(self):
        item = self.menu.get_current_item()
        if not item or item.title in ("Parent Folder", "Empty Folder"):
            return
        clean = item.title.replace("Folder: ", "")
        full = os.path.join(self.path, clean)
        if os.path.exists(full):
            self.clipboard = {"path": full, "mode": "copy"}
            self.speak(f"Copied {clean}.")

    def _cut_current(self):
        item = self.menu.get_current_item()
        if not item or item.title in ("Parent Folder", "Empty Folder"):
            return
        clean = item.title.replace("Folder: ", "")
        full = os.path.join(self.path, clean)
        if os.path.exists(full):
            self.clipboard = {"path": full, "mode": "cut"}
            self.speak(f"Cut {clean}.")

    def _start_search(self):
        self.input_mode = "search"
        self.input_buf = ""
        self.speak("Search. Enter filename.")
        self.window.update_text("Search: ")

    def _handle_input(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.input_mode = None
            self.speak("Cancelled.")
            item = self.menu.get_current_item()
            if item:
                self.window.update_text(f"{self._display_path()} - {item.title}")
            return

        if vk == win32con.VK_RETURN:
            val = self.input_buf.strip()
            if not val:
                self.speak("Cannot be empty.")
                return

            if self.input_mode == "rename":
                self._do_rename(val)
            elif self.input_mode == "new_folder":
                self._do_new_folder(val)
            elif self.input_mode == "new_file":
                self._do_new_file(val)
            elif self.input_mode == "search":
                self._do_search(val)
            self.input_mode = None
            return

        if vk == win32con.VK_BACK:
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                self.window.update_text(f"{self.input_mode}: {self.input_buf}")
            return

        ch = self._vk_to_char(vk)
        if ch:
            self.input_buf += ch
            self.window.update_text(f"{self.input_mode}: {self.input_buf}")

    def _do_rename(self, new_name):
        item = self.menu.get_current_item()
        if not item or item.title in ("Parent Folder", "Empty Folder"):
            return
        old_name = item.title.replace("Folder: ", "")
        old_path = os.path.join(self.path, old_name)
        new_path = os.path.join(self.path, new_name)
        try:
            if os.path.exists(new_path):
                self.speak("Name already exists.")
                return
            os.rename(old_path, new_path)
            self.speak(f"Renamed to {new_name}.")
            self.refresh()
        except Exception:
            self.speak("Rename failed.")

    def _do_new_folder(self, name):
        path = os.path.join(self.path, name)
        try:
            if os.path.exists(path):
                self.speak("Name already exists.")
                return
            os.makedirs(path)
            self.speak(f"Created folder {name}.")
            self.refresh()
        except Exception:
            self.speak("Failed to create folder.")

    def _do_new_file(self, name):
        path = os.path.join(self.path, name)
        try:
            if os.path.exists(path):
                self.speak("Name already exists.")
                return
            with open(path, 'w') as f:
                f.write("")
            self.speak(f"Created file {name}.")
            self.refresh()
        except Exception:
            self.speak("Failed to create file.")

    def _do_search(self, query):
        matches = []
        query_lower = query.lower()
        for item in self.items:
            if query_lower in item.lower():
                matches.append(item)

        if not matches:
            self.speak(f"No matches for {query}.")
            return

        root = MenuNode(f"Search: {query}")
        for m in matches:
            full = os.path.join(self.path, m)
            if os.path.isdir(full):
                root.add_child(MenuNode(f"Folder: {m}", lambda p=full: self._open_dir(p)))
            else:
                root.add_child(MenuNode(m, lambda p=full: self._open_file(p)))
        root.add_child(MenuNode("Back", self._back_from_search))
        self._saved_menu = self.menu
        self.menu = MenuSystem(root, self.speak)
        self.speak(f"{len(matches)} match{'es' if len(matches) != 1 else ''}. " + self.menu.get_current_item().title)
        self.window.update_text(f"Search: {self.menu.get_current_item().title}")

    def _back_from_search(self):
        self.menu = self._saved_menu
        self._announce_folder()

    def _paste(self):
        if not self.clipboard:
            self.speak("Clipboard empty.")
            return
        src = self.clipboard["path"]
        name = os.path.basename(src)
        dst = os.path.join(self.path, name)
        try:
            if os.path.exists(dst):
                self._pending_paste = (src, dst)
                self._overwrite_confirm = True
                self.speak(f"{name} exists. Overwrite? Press Enter to confirm, Escape to cancel.")
                self.window.update_text(f"Overwrite {name}?")
                return
            self._do_paste(src, dst)
        except Exception:
            self.speak("Paste failed.")

    def _do_paste(self, src, dst):
        name = os.path.basename(src)
        try:
            if self.clipboard["mode"] == "cut":
                shutil.move(src, dst)
                self.speak(f"Moved {name}.")
            else:
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                self.speak(f"Copied {name}.")
            self.clipboard = None
            self.refresh()
        except Exception:
            self.speak("Paste failed.")

    def _toggle_multi(self):
        self._multi_select = not self._multi_select
        if not self._multi_select:
            self._selected.clear()
            self.refresh()
        self.speak("Multi-select on." if self._multi_select else "Multi-select off.")
        if self._multi_select:
            self._select_current()

    def _select_current(self):
        item = self.menu.get_current_item()
        if not item or item.title in ("Parent Folder", "Empty Folder"):
            return
        clean = item.title[2:] if item.title.startswith("+ ") or item.title.startswith("  ") else item.title
        clean = clean.replace("Folder: ", "")
        if clean in self._selected:
            self._selected.discard(clean)
            self.speak(f"Deselected {clean}. {len(self._selected)} selected.")
        else:
            self._selected.add(clean)
            self.speak(f"Selected {clean}. {len(self._selected)} selected.")
        self.refresh()

    def _zip_selected(self):
        target = self._selected if self._selected else None
        if not target:
            item = self.menu.get_current_item()
            if not item or item.title in ("Parent Folder", "Empty Folder"):
                self.speak("Nothing to zip.")
                return
            clean = item.title[2:] if item.title.startswith("+ ") or item.title.startswith("  ") else item.title
            clean = clean.replace("Folder: ", "")
            target = {clean}
        zip_name = os.path.basename(self.path) + ".zip"
        zip_path = os.path.join(self.path, zip_name)
        try:
            import zipfile
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for name in target:
                    full = os.path.join(self.path, name)
                    if os.path.isdir(full):
                        for root, dirs, files in os.walk(full):
                            for fname in files:
                                fpath = os.path.join(root, fname)
                                arcname = os.path.relpath(fpath, self.path)
                                zf.write(fpath, arcname)
                    else:
                        zf.write(full, name)
            self._selected.clear()
            self.refresh()
            self.speak(f"Zipped {len(target)} item{'s' if len(target) != 1 else ''} to {zip_name}.")
        except Exception:
            self.speak("Zip failed.")

    def _unzip_current(self):
        item = self.menu.get_current_item()
        if not item or item.title in ("Parent Folder", "Empty Folder"):
            self.speak("Nothing to unzip.")
            return
        clean = item.title[2:] if item.title.startswith("+ ") or item.title.startswith("  ") else item.title
        full = os.path.join(self.path, clean)
        if not full.lower().endswith('.zip'):
            self.speak("Not a zip file.")
            return
        out_dir = os.path.join(self.path, clean[:-4])
        try:
            import zipfile
            os.makedirs(out_dir, exist_ok=True)
            with zipfile.ZipFile(full, 'r') as zf:
                zf.extractall(out_dir)
            self.refresh()
            self.speak(f"Extracted to {clean[:-4]}.")
        except Exception:
            self.speak("Unzip failed.")

    def get_help_text(self):
        return "File Manager. Space next, Backspace previous. Enter open. F1 delete, F2 rename, F3 new folder, F4 new file. F5 sort, F6 copy, Shift+F6 cut, F7 search. F8 paste, F9 clear clipboard. F10 zip, Shift+F10 unzip. Ctrl+Space multi-select. I info. Space+D drives. Escape exit."
