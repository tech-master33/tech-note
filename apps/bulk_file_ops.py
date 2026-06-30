import os
import shutil
import re
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode
from core.config import TECH_SOFT
from core.file_dialog import FileDialog


class BulkFileOps(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._target_dir = TECH_SOFT
        self._result = ""
        self._input_mode = None
        self._input_text = ""
        self._build_menu()

    def _set_dir(self, path):
        self._target_dir = path

    def _build_menu(self):
        root = MenuNode("Bulk File Operations")
        root.add_child(MenuNode(f"Target: {os.path.basename(self._target_dir)}", self._pick_dir))
        root.add_child(MenuNode("Batch Rename", self._start_batch_rename))
        root.add_child(MenuNode("Delete by Pattern", self._start_delete_pattern))
        root.add_child(MenuNode("Move by Extension", self._move_by_extension))
        root.add_child(MenuNode("Find Duplicates", self._find_duplicates))
        if self._result:
            root.add_child(MenuNode(f"Result: {self._result[:50]}..."))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _pick_dir(self):
        self._fd = FileDialog(self.manager, self.window, self._on_pick_dir)
        self._fd.start()

    def _on_pick_dir(self, path):
        if path and os.path.isdir(path):
            self._target_dir = path
            self.speak(f"Target set to {os.path.basename(path)}.")
        self._build_menu()
        self.menu.announce_current()

    def _start_batch_rename(self):
        self._input_mode = "rename"
        self._input_text = ""
        self.speak("Enter rename pattern. Use {n} for number, {name} for original name.")
        self.window.update_text("Pattern: ")

    def _do_batch_rename(self):
        pattern = self._input_text.strip()
        if not pattern:
            return
        try:
            files = sorted([f for f in os.listdir(self._target_dir) if os.path.isfile(os.path.join(self._target_dir, f))])
            count = 0
            for i, fname in enumerate(files):
                name, ext = os.path.splitext(fname)
                new_name = pattern.replace("{n}", str(i + 1)).replace("{name}", name) + ext
                os.rename(os.path.join(self._target_dir, fname), os.path.join(self._target_dir, new_name))
                count += 1
            self._result = f"Renamed {count} files."
        except:
            self._result = "Rename failed."
        self.speak(self._result)

    def _start_delete_pattern(self):
        self._input_mode = "delete"
        self._input_text = ""
        self.speak("Enter pattern to match files for deletion (e.g., .tmp, backup_). Will ask to confirm.")
        self.window.update_text("Pattern: ")

    def _do_delete_pattern(self):
        pattern = self._input_text.strip().lower()
        if not pattern:
            return
        matches = [f for f in os.listdir(self._target_dir) if pattern in f.lower()]
        if not matches:
            self._result = "No matches."
            self.speak(self._result)
            return
        self._confirm_delete_matches = matches
        self.speak(f"{len(matches)} files match. Press Enter to delete, Escape to cancel.")
        self.window.update_text(f"Delete {len(matches)} files?")
        self._confirm_mode = "delete_matches"

    def _do_confirm_delete(self):
        count = 0
        for fname in self._confirm_delete_matches:
            try:
                os.remove(os.path.join(self._target_dir, fname))
                count += 1
            except:
                pass
        self._result = f"Deleted {count} files."
        self.speak(self._result)
        self._confirm_delete_matches = []
        self._confirm_mode = None
        self._build_menu()
        self.menu.announce_current()

    def _move_by_extension(self):
        try:
            files = [f for f in os.listdir(self._target_dir) if os.path.isfile(os.path.join(self._target_dir, f))]
            dirs = set()
            for fname in files:
                ext = os.path.splitext(fname)[1].lower().lstrip(".") or "no_ext"
                if not ext:
                    ext = "no_ext"
                ext_dir = os.path.join(self._target_dir, ext.upper())
                dirs.add(ext)
                os.makedirs(ext_dir, exist_ok=True)
                shutil.move(os.path.join(self._target_dir, fname), os.path.join(ext_dir, fname))
            self._result = f"Moved {len(files)} files into {len(dirs)} folders."
        except:
            self._result = "Move failed."
        self.speak(self._result)

    def _find_duplicates(self):
        try:
            by_size = {}
            for fname in os.listdir(self._target_dir):
                full = os.path.join(self._target_dir, fname)
                if os.path.isfile(full):
                    size = os.path.getsize(full)
                    by_size.setdefault(size, []).append(fname)
            dups = {s: names for s, names in by_size.items() if len(names) > 1}
            if dups:
                lines = []
                for size, names in dups.items():
                    lines.append(f"{len(names)} files of size {size}")
                self._result = f"Found {sum(len(v) for v in dups.values())} potential duplicates: {'; '.join(lines[:5])}"
            else:
                self._result = "No duplicates found."
        except:
            self._result = "Duplicate check failed."
        self.speak(self._result[:100])

    def on_focus(self):
        if getattr(self, '_fd', None) and self._fd.active:
            return
        self._build_menu()
        item = self.menu.get_current_item()
        self.speak("Bulk File Operations. " + (item.title if item else ""))

    def on_key(self, vk):
        if getattr(self, '_fd', None) and self._fd.active:
            self._fd.on_key(vk)
            return
        if getattr(self, '_confirm_mode', None):
            if vk == win32con.VK_RETURN:
                self._do_confirm_delete()
                return
            if vk == win32con.VK_ESCAPE:
                self._confirm_mode = None
                self._confirm_delete_matches = []
                self.speak("Cancelled.")
                self._build_menu()
                self.menu.announce_current()
                return
            return
        if self._input_mode:
            if vk == win32con.VK_ESCAPE:
                self._input_mode = None
                self._build_menu()
                self.menu.announce_current()
                return
            if vk == win32con.VK_RETURN:
                mode = self._input_mode
                self._input_mode = None
                if mode == "rename":
                    self._do_batch_rename()
                elif mode == "delete":
                    self._do_delete_pattern()
                self._build_menu()
                self.menu.announce_current()
                return
            if vk == win32con.VK_BACK:
                self._input_text = self._input_text[:-1]
                self.window.update_text(f"{self._input_mode}: {self._input_text}")
                return
            ch = self._vk_to_char(vk)
            if ch:
                self._input_text += ch
                self.window.update_text(f"{self._input_mode}: {self._input_text}")
            return
        if vk == win32con.VK_ESCAPE:
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

    def get_help_text(self):
        return "Bulk File Operations. Batch rename, delete by pattern, organize by extension. Space next, Backspace previous. Escape exit."
