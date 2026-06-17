import os
import json
import win32con
from core.app_base import SoftApp
from core.config import TECH_SOFT
from core.menu import MenuNode, MenuSystem

class BookReaderApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.books_dir = os.path.join(TECH_SOFT, 'books')
        os.makedirs(self.books_dir, exist_ok=True)
        self.bookmarks_file = os.path.join(TECH_SOFT, 'bookmarks.json')
        self.bookmarks = self._load_bookmarks()
        self.menu = None
        self.state = "menu"
        self.lines = []
        self.line_index = 0
        self.page_size = 20
        self.page = 0
        self.filename = None
        self.auto_read = False
        self.read_speed = 200
        self._auto_timer = None

    def _load_bookmarks(self):
        if os.path.exists(self.bookmarks_file):
            try:
                with open(self.bookmarks_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_bookmarks(self):
        with open(self.bookmarks_file, 'w') as f:
            json.dump(self.bookmarks, f)

    def _build_menu(self):
        root = MenuNode("Book Reader")
        books = sorted([f for f in os.listdir(self.books_dir) if f.endswith('.txt')])
        if books:
            for b in books:
                tag = " [Bookmarked]" if b in self.bookmarks else ""
                root.add_child(MenuNode(f"{b}{tag}", lambda name=b: self._open_book(name)))
        else:
            root.add_child(MenuNode("No books found"))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _open_book(self, filename):
        path = os.path.join(self.books_dir, filename)
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                self.lines = f.read().splitlines()
        except Exception:
            self.speak("Failed to open book.")
            return

        self.filename = filename
        self.line_index = self.bookmarks.get(filename, 0)
        self.page = self.line_index // self.page_size
        self.state = "reading"
        self.speak(f"Opened {filename}. {len(self.lines)} lines.")
        self._announce_position()

    def on_focus(self):
        if self.state == "reading" and self.lines:
            self._announce_position()
        else:
            self._build_menu()
            self.state = "menu"
            item = self.menu.get_current_item()
            self.speak("Book Reader. " + item.title)
            self.window.update_text("Books: " + item.title)

    def _announce_position(self):
        if not self.lines:
            return
        total = len(self.lines)
        pos = self.line_index + 1
        page = self.page + 1
        total_pages = (total + self.page_size - 1) // self.page_size
        line = self.lines[self.line_index] if self.line_index < total else ""
        preview = line[:100] if line else "(empty line)"
        self.speak(f"Line {pos} of {total}. Page {page} of {total_pages}. {preview}")
        self.window.update_text(f"Page {page}/{total_pages} - {preview}")

    def on_key(self, vk):
        if self.state == "menu":
            self._handle_menu(vk)
        elif self.state == "reading":
            self._handle_reading(vk)

    def _handle_menu(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))
        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Books: " + item.title)

    def _handle_reading(self, vk):
        if vk == win32con.VK_ESCAPE:
            if self.filename:
                self.bookmarks[self.filename] = self.line_index
                self._save_bookmarks()
            self.auto_read = False
            self.state = "menu"
            self.on_focus()
            return

        if vk == win32con.VK_SPACE:
            if self.auto_read:
                self.auto_read = False
                self.speak("Stopped auto read.")
            else:
                self.line_index += 1
                if self.line_index >= len(self.lines):
                    self.speak("End of book.")
                    self.line_index = len(self.lines) - 1
                else:
                    self._announce_position()
            return

        if vk == win32con.VK_BACK:
            if self.auto_read:
                self.auto_read = False
            self.line_index = max(0, self.line_index - 1)
            self._announce_position()
            return

        if vk == win32con.VK_PRIOR:
            self.page = max(0, self.page - 1)
            self.line_index = self.page * self.page_size
            self._announce_position()
            return

        if vk == win32con.VK_NEXT:
            self.page += 1
            self.line_index = self.page * self.page_size
            if self.line_index >= len(self.lines):
                self.line_index = max(0, len(self.lines) - 1)
            self._announce_position()
            return

        if vk == win32con.VK_HOME:
            self.line_index = 0
            self.page = 0
            self._announce_position()
            return

        if vk == win32con.VK_END:
            self.line_index = max(0, len(self.lines) - 1)
            self.page = self.line_index // self.page_size
            self._announce_position()
            return

        if vk == 0x42:
            if self.filename:
                self.bookmarks[self.filename] = self.line_index
                self._save_bookmarks()
                self.speak(f"Bookmark saved at line {self.line_index + 1}.")
            return

        if vk == 0x4A:
            if self.filename and self.filename in self.bookmarks:
                self.line_index = self.bookmarks[self.filename]
                self.page = self.line_index // self.page_size
                self.speak(f"Jumped to bookmark at line {self.line_index + 1}.")
                self._announce_position()
            else:
                self.speak("No bookmark for this book.")
            return

        if vk in (0xBB, 0x6B):
            self.read_speed = min(500, self.read_speed + 50)
            self.speak(f"Speed {self.read_speed} words per minute.")
            return

        if vk in (0xBD, 0x6D):
            self.read_speed = max(100, self.read_speed - 50)
            self.speak(f"Speed {self.read_speed} words per minute.")
            return

        if vk == win32con.VK_RETURN:
            self.auto_read = not self.auto_read
            if self.auto_read:
                self.speak("Auto read on.")
                self._auto_read_next()
            else:
                self.speak("Auto read off.")
            return

    def _auto_read_next(self):
        if not self.auto_read or not self.lines:
            return
        if self.line_index < len(self.lines):
            line = self.lines[self.line_index]
            if line.strip():
                self.speak(line)
            self.line_index += 1
            delay = 60.0 / self.read_speed
            self.window.after(int(delay * 1000), self._auto_read_next)
        else:
            self.auto_read = False
            self.speak("End of book.")

    def get_help_text(self):
        if self.state == "reading":
            return "Reading. Space: next line. Backspace: previous. PageUp/PageDown: page. Home/End: start/end. Enter: auto read. B: bookmark. J: jump to bookmark. +/-: speed. Escape: exit."
        return "Book Reader. Browse .txt books. Space for next, Backspace for previous. Enter to open. Escape to exit."
