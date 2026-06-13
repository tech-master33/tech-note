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

    def _build_menu(self):
        root = MenuNode("Internet")
        keys = sorted(self.bookmarks.keys())
        for name in keys:
            url = self.bookmarks[name]
            root.add_child(MenuNode(name, lambda u=url: self.fetch_page(u)))
        self.menu = MenuSystem(root, self.speak)

    def on_focus(self):
        self._build_menu()
        name = self.menu.get_current_item().title
        self.speak("Internet. " + name)
        self.window.update_text("Internet: " + name)

    def on_key(self, vk):
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
            if vk in (win32con.VK_SPACE, win32con.VK_DOWN):
                self._next_content()
            elif vk in (win32con.VK_BACK, win32con.VK_UP):
                self._previous_content()
            return

        if vk in (win32con.VK_SPACE, win32con.VK_DOWN):
            self.menu.next()
        elif vk in (win32con.VK_BACK, win32con.VK_UP):
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))

        if not self.reading_mode:
            item = self.menu.get_current_item()
            if item:
                self.window.update_text("Internet: " + item.title)

    def _next_content(self):
        if not self.content:
            return
        self.content_index = (self.content_index + 1) % len(self.content)
        text = self.content[self.content_index]
        self.speak(text)
        self.window.update_text(text)

    def _previous_content(self):
        if not self.content:
            return
        self.content_index = (self.content_index - 1) % len(self.content)
        text = self.content[self.content_index]
        self.speak(text)
        self.window.update_text(text)

    def _progress_ticker(self):
        while self.fetching:
            # Subtle tick sound or message
            # Since we don't have a small tick.wav yet, we can use a very short speak or print
            # Or just wait for implementation of more sounds
            time.sleep(1.5)
            if self.fetching:
                # We could play a sound here if we had a tick.wav
                pass

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
