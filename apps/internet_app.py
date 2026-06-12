import win32con
from core.app_base import SoftApp

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
        self.keys = list(self.bookmarks.keys())
        self.index = 0
        self.content = []
        self.content_index = 0
        self.reading_mode = False

    def on_focus(self):
        self.speak("Internet. " + self.keys[self.index])
        self.window.update_text("Internet: " + self.keys[self.index])

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            if self.reading_mode:
                self.reading_mode = False
                self.content = []
                self.speak(self.keys[self.index])
                self.window.update_text("Internet: " + self.keys[self.index])
                return
            self.exit_app()
            return

        if vk == win32con.VK_BACK:
            if self.reading_mode:
                self._previous_content()
            else:
                self.index = (self.index - 1) % len(self.keys)
                self.announce()
            return

        if self.reading_mode:
            if vk == win32con.VK_SPACE or vk == win32con.VK_DOWN:
                self._next_content()
            return

        if vk == win32con.VK_SPACE or vk == win32con.VK_DOWN:
            self.index = (self.index + 1) % len(self.keys)
            self.announce()
        elif vk == win32con.VK_UP:
            self.index = (self.index - 1) % len(self.keys)
            self.announce()
        elif vk == win32con.VK_RETURN:
            self.fetch_page(self.bookmarks[self.keys[self.index]])

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

    def fetch_page(self, url):
        if not HAS_WEB_DEPS:
            self.speak("Internet features require requests and beautifulsoup4.")
            return
        self.speak("Fetching.")
        try:
            response = requests.get(url, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            self.content = []
            for element in soup.find_all(['h1', 'h2', 'h3', 'p', 'a']):
                if element.name in ['h1', 'h2', 'h3']:
                    self.content.append(f"Heading: {element.get_text()}")
                elif element.name == 'a':
                    self.content.append(f"Link: {element.get_text()}")
                else:
                    self.content.append(element.get_text())
            if self.content:
                self.reading_mode = True
                self.content_index = 0
                text = self.content[0]
                self.speak("Page loaded. " + text)
                self.window.update_text(text)
            else:
                self.speak("No content found on page.")
        except Exception as e:
            self.speak("Error fetching page.")

    def announce(self):
        item = self.keys[self.index]
        self.speak(item)
        self.window.update_text("Internet: " + item)
