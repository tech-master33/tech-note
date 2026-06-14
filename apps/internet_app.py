import win32con
import threading
import time
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_WEB_DEPS = True
except ImportError:
    HAS_WEB_DEPS = False

class InternetApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.bookmarks = {
            "Google": "https://www.google.com",
            "Wikipedia": "https://www.wikipedia.org",
            "TechNews": "https://www.techcrunch.com"
        }
        self.menu = None
        self.content = []
        self.content_index = 0
        self.reading_mode = False
        self.fetching = False
        self.url_input_mode = False
        self.input_buf = ""

    def _build_menu(self):
        root = MenuNode("Internet")
        root.add_child(MenuNode("Open URL", self._start_url_input, "o"))
        keys = sorted(self.bookmarks.keys())
        for name in keys:
            url = self.bookmarks[name]
            root.add_child(MenuNode(name, lambda u=url: self.fetch_page(u)))
        self.menu = MenuSystem(root, self.speak)

    def _start_url_input(self):
        self.url_input_mode = True
        self.input_buf = ""
        self.speak("Enter URL.")
        self.window.update_text("URL: ")

    def on_focus(self):
        self._build_menu()
        name = self.menu.get_current_item().title
        self.speak("Internet. " + name)
        self.window.update_text("Internet: " + name)

    def on_key(self, vk):
        if self.url_input_mode:
            self._handle_url_input(vk)
            return

        if vk == win32con.VK_ESCAPE:
            if self.reading_mode:
                self.reading_mode = False
                self.content = []
                name = self.menu.get_current_item().title
                self.speak(name)
                self.window.update_text("Internet: " + name)
                return
            self.exit_app()
            return

        if self.reading_mode:
            if vk in (win32con.VK_SPACE):
                self._next_content()
            elif vk in (win32con.VK_BACK):
                self._previous_content()
            elif vk == 0x48: # 'H' for headings
                self._next_heading()
            return

        if vk in (win32con.VK_SPACE):
            self.menu.next()
        elif vk in (win32con.VK_BACK):
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))

        if not self.reading_mode:
            item = self.menu.get_current_item()
            if item:
                self.window.update_text("Internet: " + item.title)

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

    def _vk_to_char(self, vk):
        import win32api
        shift = win32api.GetAsyncKeyState(win32con.VK_SHIFT) & 0x8000
        if 0x41 <= vk <= 0x5A:
            return chr(vk).lower()
        if 0x30 <= vk <= 0x39:
            return chr(vk)
        syms = {0xBE: '.', 0xBF: '/', 0xBD: '-', 0xBA: ':', 0xC0: '~'}
        if vk in syms: return syms[vk]
        return None

    def _next_content(self):
        if not self.content: return
        self.content_index = (self.content_index + 1) % len(self.content)
        self._announce_content()

    def _previous_content(self):
        if not self.content: return
        self.content_index = (self.content_index - 1) % len(self.content)
        self._announce_content()

    def _next_heading(self):
        if not self.content: return
        start = self.content_index
        for i in range(1, len(self.content)):
            idx = (start + i) % len(self.content)
            if self.content[idx].startswith("Heading:"):
                self.content_index = idx
                self._announce_content()
                return
        self.speak("No more headings.")

    def _announce_content(self):
        text = self.content[self.content_index]
        self.speak(text)
        self.window.update_text(text)

    def _progress_ticker(self):
        while self.fetching:
            # Subtle auditory feedback
            self.speak("Working")
            time.sleep(3.0)

    def get_help_text(self):
        if self.reading_mode:
            return "Reading Mode. Space for next line, Backspace for previous. H for next heading. Escape to return to bookmarks."
        return "Internet Browser. Space for next bookmark, Backspace for previous. Enter to open. O for Open URL. Press Escape to exit."

    def fetch_page(self, url):
        if not HAS_WEB_DEPS:
            self.speak("Internet features require requests and beautifulsoup4.")
            return
        
        self.fetching = True
        threading.Thread(target=self._progress_ticker, daemon=True).start()
        self.speak("Fetching.")

        def _do_fetch():
            try:
                response = requests.get(url, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                self.content = []
                for element in soup.find_all(['h1', 'h2', 'h3', 'p', 'a']):
                    if element.name in ['h1', 'h2', 'h3']:
                        self.content.append(f"Heading: {element.get_text()}")
                    elif element.name == 'a':
                        self.content.append(f"Link: {element.get_text()}")
                    else:
                        txt = element.get_text().strip()
                        if txt: self.content.append(txt)
                
                self.fetching = False
                if self.content:
                    self.reading_mode = True
                    self.content_index = 0
                    text = self.content[0]
                    self.speak("Page loaded. " + text)
                    self.window.update_text(text)
                else:
                    self.speak("No content found on page.")
            except Exception:
                self.fetching = False
                self.speak("Error fetching page.")

        threading.Thread(target=_do_fetch, daemon=True).start()
