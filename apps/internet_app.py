import win32con
import threading
import time
import os
import json
import mimetypes
from urllib.parse import urljoin, urlparse
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.config import TECH_SOFT

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_WEB_DEPS = True
except ImportError:
    HAS_WEB_DEPS = False

try:
    from readability import Document
    HAS_READABILITY = True
except ImportError:
    HAS_READABILITY = False


BOOKMARKS_PATH = os.path.join(TECH_SOFT, 'bookmarks.json')
HISTORY_PATH = os.path.join(TECH_SOFT, 'browser_history.json')
DOWNLOADS_DIR = os.path.join(TECH_SOFT, 'downloads')


class ContentItem:
    def __init__(self, text, url=None, tag_name=None):
        self.text = text
        self.url = url
        self.tag_name = tag_name

    @property
    def is_heading(self):
        return self.tag_name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')

    @property
    def is_link(self):
        return self.url is not None


def _default_bookmarks():
    return {
        "Google": "https://www.google.com",
        "Wikipedia": "https://www.wikipedia.org",
        "TechCrunch": "https://www.techcrunch.com"
    }


def _load_bookmarks():
    if os.path.exists(BOOKMARKS_PATH):
        try:
            with open(BOOKMARKS_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return _default_bookmarks()


def _save_bookmarks(bm):
    try:
        with open(BOOKMARKS_PATH, 'w') as f:
            json.dump(bm, f)
    except Exception:
        pass


def _load_history():
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_history(entries):
    try:
        with open(HISTORY_PATH, 'w') as f:
            json.dump(entries[-50:], f)
    except Exception:
        pass


def _sanitize_filename(url):
    parsed = urlparse(url)
    name = os.path.basename(parsed.path)
    if not name:
        name = parsed.netloc.replace('.', '_') + '.html'
    safe = "".join(c for c in name if c.isalnum() or c in '._- ')
    return safe or 'download'


class InternetApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.bookmarks = _load_bookmarks()
        self.menu = None
        self.content = []
        self.content_index = 0
        self.reading_mode = False
        self.fetching = False
        self.url_input_mode = False
        self.input_buf = ""
        self._speech_queue = []
        self._queue_lock = threading.Lock()
        self._content_lock = threading.Lock()
        self._search_mode = False
        self._search_query = ""
        self._search_results = []
        self._search_index = 0
        self._add_bookmark_stage = None
        self._page_title = ""
        self._page_url = ""
        self._back_stack = []
        self._download_progress = None
        self._history = _load_history()

    def _queue_speech(self, text):
        with self._queue_lock:
            self._speech_queue.append(text)

    def _process_speech_queue(self):
        with self._queue_lock:
            while self._speech_queue:
                text = self._speech_queue.pop(0)
                self.speak(text)

    def _build_menu(self):
        root = MenuNode("Internet")
        root.add_child(MenuNode("Open URL", self._start_url_input, "o"))
        root.add_child(MenuNode("Add Bookmark", self._start_add_bookmark, "a"))
        root.add_child(MenuNode("Remove Bookmark", self._enter_remove_bookmark, "r"))
        root.add_child(MenuNode("History", self._show_history, "h"))
        items = self.bookmarks.get("__items__", [])
        if items:
            root.add_child(MenuNode("--- Quick Links ---", None))
            for name in items:
                url = self.bookmarks.get(name)
                if url:
                    root.add_child(MenuNode(name, lambda u=url: self.fetch_page(u)))
        keys = [k for k in sorted(self.bookmarks.keys()) if k != "__items__"]
        for name in keys:
            url = self.bookmarks[name]
            root.add_child(MenuNode(name, lambda u=url: self.fetch_page(u)))
        self.menu = MenuSystem(root, self.speak)

    def _start_url_input(self):
        self.url_input_mode = True
        self.input_buf = ""
        self.speak("Enter URL.")
        self.window.update_text("URL: ")

    def _start_add_bookmark(self):
        self._add_bookmark_stage = "url"
        self.input_buf = ""
        self.speak("Enter URL for bookmark.")
        self.window.update_text("Bookmark URL: ")

    def _enter_remove_bookmark(self):
        root = MenuNode("Remove Bookmark")
        for name in sorted(self.bookmarks.keys()):
            root.add_child(MenuNode(name, lambda n=name: self._do_remove_bookmark(n)))
        root.add_child(MenuNode("Back", self._build_menu))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _do_remove_bookmark(self, name):
        if name in self.bookmarks:
            del self.bookmarks[name]
            _save_bookmarks(self.bookmarks)
            self.speak(f"{name} removed.")
        self._build_menu()
        self.menu.announce_current()

    def _show_history(self):
        if not self._history:
            self.speak("No history.")
            return
        root = MenuNode("History")
        for entry in reversed(self._history[-20:]):
            title = entry.get("title", entry.get("url", "Unknown"))
            url = entry.get("url", "")
            root.add_child(MenuNode(title, lambda u=url: self.fetch_page(u)))
        root.add_child(MenuNode("Clear History", self._clear_history))
        root.add_child(MenuNode("Back", self._build_menu))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _clear_history(self):
        self._history = []
        _save_history(self._history)
        self.speak("History cleared.")
        self._build_menu()

    def on_focus(self):
        self._build_menu()
        name = self.menu.get_current_item().title if self.menu.get_current_item() else "Internet"
        self.speak("Internet. " + name)
        self.window.update_text("Internet: " + name)

    def on_key(self, vk):
        self._process_speech_queue()

        if self._download_progress:
            self.speak(f"Downloading {self._download_progress}")
            self._download_progress = None
            return True

        if self._add_bookmark_stage:
            self._handle_add_bookmark(vk)
            return True

        if self.url_input_mode:
            self._handle_url_input(vk)
            return True

        if vk == win32con.VK_ESCAPE:
            if self._search_mode:
                self._search_mode = False
                self.speak("Search cancelled.")
                return True
            if self.reading_mode and self._back_stack:
                url = self._back_stack.pop()
                self.speak("Going back.")
                self.fetch_page(url)
                return True
            if self.reading_mode:
                self.reading_mode = False
                self.content = []
                self.speak("Returning to menu.")
                return True
            self.exit_app()
            return True

        if self.reading_mode:
            self._handle_reading_key(vk)
            return True

        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))

        if not self.reading_mode:
            item = self.menu.get_current_item()
            if item:
                self.window.update_text("Internet: " + item.title)

    def _handle_reading_key(self, vk):
        if self._search_mode:
            if vk == win32con.VK_ESCAPE:
                self._search_mode = False
                self.speak("Search cancelled.")
            elif vk == win32con.VK_BACK:
                self._search_mode = False
                self.speak("Search cancelled.")
            elif vk == win32con.VK_SPACE:
                self._search_query += " "
                self._do_search()
            elif vk == win32con.VK_RETURN:
                self._search_mode = False
                if self._search_results:
                    self.content_index = self._search_results[0]
                    self._announce_content()
            elif 0x20 <= vk <= 0x5A:
                ch = chr(vk).lower() if 0x41 <= vk <= 0x5A else chr(vk)
                self._search_query += ch
                self._do_search()
            elif 0x30 <= vk <= 0x39:
                self._search_query += chr(vk)
                self._do_search()
            return

        if vk == win32con.VK_BACK:
            self._previous_content()
        elif vk == win32con.VK_RETURN:
            self._follow_link()
        elif vk == 0x44:
            self._download_current()
        elif vk == 0x48:
            self._next_heading()
        elif vk == 0x49:
            self._page_info()
        elif vk == 0x4C:
            self._next_link()
        elif vk == 0xBF:
            self._enter_search_mode()

    def on_key_up(self, vk):
        self._process_speech_queue()

        if self._search_mode and vk == win32con.VK_SPACE:
            self._search_query += " "
            self._do_search()
            return

        if vk == win32con.VK_SPACE:
            if self.url_input_mode or self._add_bookmark_stage:
                return
            if self._search_mode:
                self._next_search_result()
                return
            if self.reading_mode:
                self._next_content()
            else:
                self.menu.next()
                item = self.menu.get_current_item()
                if item:
                    self.window.update_text("Internet: " + item.title)

    def _handle_add_bookmark(self, vk):
        if vk == win32con.VK_ESCAPE:
            self._add_bookmark_stage = None
            self.on_focus()
            return
        if vk == win32con.VK_RETURN:
            val = self.input_buf.strip()
            if not val:
                self.speak("Cannot be empty.")
                return
            if self._add_bookmark_stage == "url":
                if not val.startswith('http'):
                    val = "https://" + val
                self._pending_bookmark_url = val
                self._add_bookmark_stage = "name"
                self.input_buf = ""
                self.speak("Enter name for bookmark.")
                self.window.update_text("Bookmark name: ")
            elif self._add_bookmark_stage == "name":
                name = val
                self.bookmarks[name] = self._pending_bookmark_url
                if "__items__" not in self.bookmarks:
                    self.bookmarks["__items__"] = []
                self.bookmarks["__items__"].append(name)
                _save_bookmarks(self.bookmarks)
                self._add_bookmark_stage = None
                self.speak(f"Bookmark {name} added.")
                self._build_menu()
                self.menu.announce_current()
            return
        if vk == win32con.VK_BACK:
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                self.window.update_text(f"{'URL' if self._add_bookmark_stage == 'url' else 'Name'}: {self.input_buf}")
            return
        ch = self._vk_to_char(vk)
        if ch:
            self.input_buf += ch
            self.window.update_text(f"{'URL' if self._add_bookmark_stage == 'url' else 'Name'}: {self.input_buf}")
            self.speak(ch)

    def _handle_url_input(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.url_input_mode = False
            self.on_focus()
            return
        if vk == win32con.VK_RETURN:
            url = self.input_buf.strip()
            if url:
                if not url.startswith('http'):
                    url = "https://" + url
                self.url_input_mode = False
                self.fetch_page(url)
            return
        if vk == win32con.VK_BACK:
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                self.window.update_text(f"URL: {self.input_buf}")
            return
        ch = self._vk_to_char(vk)
        if ch:
            self.input_buf += ch
            self.window.update_text(f"URL: {self.input_buf}")
            self.speak(ch)

    def _next_content(self):
        if not self.content:
            return
        self.content_index = (self.content_index + 1) % len(self.content)
        self._announce_content()

    def _previous_content(self):
        if not self.content:
            return
        self.content_index = (self.content_index - 1) % len(self.content)
        self._announce_content()

    def _next_heading(self):
        if not self.content:
            return
        start = self.content_index
        for i in range(1, len(self.content)):
            idx = (start + i) % len(self.content)
            if self.content[idx].is_heading:
                self.content_index = idx
                self._announce_content()
                return
        self.speak("No more headings.")

    def _next_link(self):
        if not self.content:
            return
        start = self.content_index
        for i in range(1, len(self.content)):
            idx = (start + i) % len(self.content)
            if self.content[idx].is_link:
                self.content_index = idx
                self._announce_content()
                return
        self.speak("No more links.")

    def _follow_link(self):
        if not self.content:
            return
        item = self.content[self.content_index]
        if item.url:
            if self._page_url:
                self._back_stack.append(self._page_url)
            self.speak("Opening link.")
            self.fetch_page(item.url)
        else:
            self.speak("Not a link.")

    def _download_current(self):
        if not self.content:
            return
        item = self.content[self.content_index]
        if not item.url:
            self.speak("No link to download.")
            return
        self.speak(f"Downloading {item.text[:50]}.")
        threading.Thread(target=self._do_download, args=(item.url,), daemon=True).start()

    def _do_download(self, url):
        try:
            os.makedirs(DOWNLOADS_DIR, exist_ok=True)
            resp = requests.get(url, stream=True, timeout=15)
            fname = _sanitize_filename(url)
            path = os.path.join(DOWNLOADS_DIR, fname)
            with open(path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            self._queue_speech(f"Downloaded to {fname}.")
        except Exception:
            self._queue_speech("Download failed.")

    def _page_info(self):
        if self._page_title:
            self.speak(f"Title: {self._page_title}. URL: {self._page_url}. Items: {len(self.content)}.")
        else:
            self.speak(f"Page has {len(self.content)} items.")

    def _enter_search_mode(self):
        self._search_mode = True
        self._search_query = ""
        self._search_results = []
        self._search_index = 0
        self.speak("Search page.")

    def _do_search(self):
        q = self._search_query.lower().strip()
        if not q:
            self._search_results = []
            return
        self._search_results = [i for i, item in enumerate(self.content) if q in item.text.lower()]
        self._search_index = 0
        if self._search_results:
            self.content_index = self._search_results[0]
            c = len(self._search_results)
            self.speak(f"{c} match{'es' if c != 1 else ''}.")
            self._announce_content()
        else:
            self.speak(f"No matches for {q}.")

    def _next_search_result(self):
        if not self._search_results:
            return
        self._search_index = (self._search_index + 1) % len(self._search_results)
        self.content_index = self._search_results[self._search_index]
        pos = self._search_index + 1
        total = len(self._search_results)
        item = self.content[self.content_index]
        self.speak(f"Match {pos} of {total}.")

    def _announce_content(self):
        item = self.content[self.content_index]
        self.speak(item.text)
        self.window.update_text(item.text)

    def get_help_text(self):
        if self.reading_mode:
            return "Reading Mode. Space next, Backspace previous. H heading, L link, Enter follow, D download, I info, / search. Escape back."
        return "Internet. Space next, Backspace previous, Enter open. O URL, A add bookmark, R remove, H history. Escape exit."

    def fetch_page(self, url):
        if not HAS_WEB_DEPS:
            self.speak("Internet features require requests and beautifulsoup4.")
            return
        self.fetching = True
        self.speak("Fetching.")
        threading.Thread(target=self._do_fetch, args=(url,), daemon=True).start()

    def _do_fetch(self, url):
        try:
            response = requests.get(url, timeout=10)
            html = response.text
            title = ""
            if HAS_READABILITY:
                try:
                    doc = Document(html)
                    title = doc.title()
                    html = doc.summary()
                except Exception:
                    pass
            soup = BeautifulSoup(html, 'html.parser')
            if not title:
                t = soup.find('title')
                if t:
                    title = t.get_text()
            new_content = []
            for element in soup.find_all(['h1', 'h2', 'h3', 'p', 'a']):
                if element.name in ['h1', 'h2', 'h3']:
                    new_content.append(ContentItem(f"Heading: {element.get_text().strip()}", tag_name=element.name))
                elif element.name == 'a':
                    href = element.get('href')
                    if href:
                        href = urljoin(url, href)
                    new_content.append(ContentItem(f"Link: {element.get_text().strip()}", url=href, tag_name='a'))
                else:
                    txt = element.get_text().strip()
                    if txt:
                        new_content.append(ContentItem(txt, tag_name='p'))
            with self._content_lock:
                self.content = new_content
            self.fetching = False
            self._page_title = title
            self._page_url = url
            self._history.append({"title": title or url, "url": url, "time": time.time()})
            _save_history(self._history)
            if self.content:
                self.reading_mode = True
                self.content_index = 0
                item = self.content[0]
                msg = "Page loaded. "
                if title:
                    msg += f"{title}. "
                self._queue_speech(msg + item.text)
                self.window.update_text(item.text)
            else:
                self._queue_speech("No content found on page.")
            self._process_speech_queue()
        except Exception:
            self.fetching = False
            self._queue_speech("Error fetching page.")
