import os
import shutil
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode
from core.config import TECH_SOFT


def _format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


class DiskCleanup(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._result = ""
        self._recoverable = 0
        self._confirm_clean = False
        self._build_menu()

    def _build_menu(self):
        root = MenuNode("Disk Cleanup")
        root.add_child(MenuNode("Analyze Space", self._analyze))
        root.add_child(MenuNode("Temp Files", self._find_temp))
        root.add_child(MenuNode("Large Files (>10MB)", self._find_large))
        root.add_child(MenuNode("Empty Folders", self._find_empty))
        if self._result:
            root.add_child(MenuNode(f"Result: {self._result[:50]}..."))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _analyze(self):
        try:
            total = 0
            count = 0
            for root_dir, dirs, files in os.walk(TECH_SOFT):
                for fname in files:
                    try:
                        fpath = os.path.join(root_dir, fname)
                        total += os.path.getsize(fpath)
                        count += 1
                    except:
                        pass
            self._result = f"{count} files, {_format_size(total)} total."
        except:
            self._result = "Analysis failed."
        self.speak(self._result)

    def _find_temp(self):
        try:
            temp_paths = [
                os.environ.get("TEMP", ""),
                os.environ.get("TMP", ""),
                os.path.join(TECH_SOFT, "downloads"),
            ]
            total = 0
            count = 0
            for tp in temp_paths:
                if tp and os.path.exists(tp):
                    for fname in os.listdir(tp):
                        try:
                            fpath = os.path.join(tp, fname)
                            if os.path.isfile(fpath):
                                total += os.path.getsize(fpath)
                                count += 1
                        except:
                            pass
            self._recoverable = total
            self._result = f"{count} temp files, {_format_size(total)}. Clean?"
            self.speak(self._result)
            self._confirm_clean = True
            self.window.update_text("Press Enter to clean temp files, Escape to cancel.")
        except:
            self._result = "Temp scan failed."
            self.speak(self._result)

    def _find_large(self):
        try:
            large = []
            for root_dir, dirs, files in os.walk(TECH_SOFT):
                for fname in files:
                    try:
                        fpath = os.path.join(root_dir, fname)
                        size = os.path.getsize(fpath)
                        if size > 10 * 1024 * 1024:
                            large.append((fname, size, fpath))
                    except:
                        pass
            large.sort(key=lambda x: x[1], reverse=True)
            if large:
                lines = [f"{f}: {_format_size(s)}" for f, s, p in large[:10]]
                self._result = "; ".join(lines)
            else:
                self._result = "No large files found."
        except:
            self._result = "Scan failed."
        self.speak(self._result[:100])

    def _find_empty(self):
        try:
            empty = []
            for root_dir, dirs, files in os.walk(TECH_SOFT):
                if not dirs and not files:
                    empty.append(root_dir)
            if empty:
                self._result = f"Found {len(empty)} empty folders."
            else:
                self._result = "No empty folders."
        except:
            self._result = "Scan failed."
        self.speak(self._result)

    def _do_clean_temp(self):
        temp_paths = [
            os.environ.get("TEMP", ""),
            os.environ.get("TMP", ""),
            os.path.join(TECH_SOFT, "downloads"),
        ]
        count = 0
        for tp in temp_paths:
            if tp and os.path.exists(tp):
                for fname in os.listdir(tp):
                    try:
                        fpath = os.path.join(tp, fname)
                        if os.path.isfile(fpath):
                            os.remove(fpath)
                            count += 1
                    except:
                        pass
        self.speak(f"Cleaned {count} temp files.")
        self._confirm_clean = False
        self._build_menu()
        self.menu.announce_current()

    def on_focus(self):
        self._build_menu()
        item = self.menu.get_current_item()
        self.speak("Disk Cleanup. " + (item.title if item else ""))

    def on_key(self, vk):
        if self._confirm_clean:
            if vk == win32con.VK_RETURN:
                self._do_clean_temp()
                return
            if vk == win32con.VK_ESCAPE:
                self._confirm_clean = False
                self.speak("Cancelled.")
                self._build_menu()
                self.menu.announce_current()
                return
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
        return "Disk Cleanup. Find temp files, large files, empty folders. Space next, Backspace previous. Escape exit."
