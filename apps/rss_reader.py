import os
import json
import threading
import time
import win32con
import urllib.request
import urllib.error
import xml.parsers.expat
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.config import TECH_SOFT

FEEDS_FILE = os.path.join(TECH_SOFT, "rss_feeds.json")
ARTICLES_CACHE = os.path.join(TECH_SOFT, "rss_cache.json")


class RSSReader(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.feeds = self._load_feeds()
        self.articles = self._load_cache()
        self._input_mode = None
        self._input_text = ""
        self._selected_feed = None
        self._build_menu()

    def _load_feeds(self):
        try:
            if os.path.exists(FEEDS_FILE):
                with open(FEEDS_FILE, 'r') as f:
                    return json.load(f)
        except:
            pass
        return [
            {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
            {"name": "Hacker News", "url": "https://hnrss.org/frontpage"},
            {"name": "BBC News", "url": "https://feeds.bbci.co.uk/news/rss.xml"},
        ]

    def _save_feeds(self):
        try:
            os.makedirs(os.path.dirname(FEEDS_FILE), exist_ok=True)
            with open(FEEDS_FILE, 'w') as f:
                json.dump(self.feeds, f, indent=2)
        except:
            pass

    def _load_cache(self):
        try:
            if os.path.exists(ARTICLES_CACHE):
                with open(ARTICLES_CACHE, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}

    def _save_cache(self):
        try:
            os.makedirs(os.path.dirname(ARTICLES_CACHE), exist_ok=True)
            with open(ARTICLES_CACHE, 'w') as f:
                json.dump(self.articles, f, indent=2)
        except:
            pass

    def _build_menu(self):
        root = MenuNode("RSS Reader")
        root.add_child(MenuNode("Refresh All", self._refresh_all))
        root.add_child(MenuNode("Add Feed", self._start_add_feed))
        for feed in self.feeds:
            name = feed.get("name", "Unknown")
            root.add_child(MenuNode(name, lambda f=feed: self._show_feed(f)))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _refresh_all(self):
        self.speak("Refreshing all feeds...")
        self.window.update_text("Refreshing...")
        for feed in self.feeds:
            self._fetch_feed(feed)
        self.speak("Refresh complete.")

    def _fetch_feed(self, feed):
        url = feed.get("url", "")
        name = feed.get("name", "Unknown")
        if not url:
            return
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TechNote-RSS/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read().decode('utf-8', errors='replace')
            articles = self._parse_rss(data)
            if articles:
                self.articles[name] = articles
                self._save_cache()
                self.speak(f"{name}: {len(articles)} articles.")
        except:
            cached = self.articles.get(name, [])
            if cached:
                self.speak(f"{name}: using cached ({len(cached)} articles).")

    def _parse_rss(self, data):
        articles = []
        in_item = False
        in_title = False
        in_link = False
        in_desc = False
        in_pub = False
        current = {}
        tag_stack = []

        def start(name, attrs):
            nonlocal in_item, in_title, in_link, in_desc, in_pub
            tag_stack.append(name)
            if name == 'item':
                in_item = True
                current.clear()
            if in_item:
                if name == 'title':
                    in_title = True
                elif name == 'link':
                    in_link = True
                elif name == 'description':
                    in_desc = True
                elif name in ('pubDate', 'published'):
                    in_pub = True

        def end(name):
            nonlocal in_item, in_title, in_link, in_desc, in_pub
            if name == 'item' and in_item:
                if current.get('title'):
                    articles.append(dict(current))
                current.clear()
                in_item = False
            if in_item:
                if name == 'title':
                    in_title = False
                elif name == 'link':
                    in_link = False
                elif name == 'description':
                    in_desc = False
                elif name in ('pubDate', 'published'):
                    in_pub = False
            if tag_stack:
                tag_stack.pop()

        def text(data):
            nonlocal in_title, in_link, in_desc, in_pub
            if in_item:
                if in_title:
                    current['title'] = current.get('title', '') + data
                elif in_link:
                    current['link'] = current.get('link', '') + data
                elif in_desc:
                    current['description'] = current.get('description', '') + data
                elif in_pub:
                    current['published'] = current.get('published', '') + data

        p = xml.parsers.expat.ParserCreate()
        p.StartElementHandler = start
        p.EndElementHandler = end
        p.CharacterDataHandler = text
        try:
            p.Parse(data, True)
        except:
            pass
        return articles

    def _start_add_feed(self):
        self._input_mode = "add_feed"
        self._input_text = ""
        self.speak("Enter feed URL.")
        self.window.update_text("Feed URL: ")

    def _do_add_feed(self):
        url = self._input_text.strip()
        if not url:
            return
        self._input_mode = "add_feed_name"
        self._pending_url = url
        self._input_text = ""
        self.speak("Enter feed name.")
        self.window.update_text("Feed name: ")

    def _finish_add_feed(self):
        name = self._input_text.strip() or "Feed"
        self.feeds.append({"name": name, "url": self._pending_url})
        self._save_feeds()
        self.speak(f"Added {name}.")
        self._input_mode = None
        self._build_menu()
        self.menu.announce_current()

    def _remove_feed(self, feed):
        name = feed.get("name", "")
        self.feeds = [f for f in self.feeds if f.get("name") != name]
        self._save_feeds()
        self.articles.pop(name, None)
        self._save_cache()
        self.speak(f"Removed {name}.")

    def _show_feed(self, feed):
        self._selected_feed = feed
        name = feed.get("name", "Unknown")
        if name not in self.articles:
            self._fetch_feed(feed)
        articles = self.articles.get(name, [])
        root = MenuNode(name)
        root.add_child(MenuNode("Refresh", lambda: self._refresh_one(feed)))
        for i, art in enumerate(articles):
            title = art.get("title", "Untitled")[:60]
            root.add_child(MenuNode(title, lambda a=art: self._show_article(a)))
        if articles:
            root.add_child(MenuNode("Remove Feed", lambda: self._remove_feed(feed)))
        root.add_child(MenuNode("Back", self._build_menu_back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _refresh_one(self, feed):
        self._fetch_feed(feed)
        self._show_feed(feed)

    def _show_article(self, article):
        title = article.get("title", "Untitled")
        desc = article.get("description", "No description.")
        link = article.get("link", "")
        import re
        clean_desc = re.sub(r'<[^>]+>', '', desc)[:200]
        root = MenuNode(title)
        root.add_child(MenuNode(clean_desc))
        if link:
            root.add_child(MenuNode("Open Link", lambda: self._open_link(link)))
        root.add_child(MenuNode("Back", lambda: self._show_feed(self._selected_feed)))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _open_link(self, url):
        try:
            import subprocess
            subprocess.Popen(["rundll32.exe", "url.dll,FileProtocolHandler", url])
            self.speak("Opening in browser.")
        except:
            self.speak("Failed to open link.")

    def _build_menu_back(self):
        self._build_menu()
        self.menu.announce_current()

    def on_focus(self):
        item = self.menu.get_current_item()
        self._announce("RSS Reader. " + (item.title if item else ""))

    def on_key(self, vk):
        if self._input_mode:
            if vk == win32con.VK_ESCAPE:
                self._input_mode = None
                self._build_menu()
                self.menu.announce_current()
                return
            if vk == win32con.VK_RETURN:
                if self._input_mode == "add_feed":
                    self._do_add_feed()
                elif self._input_mode == "add_feed_name":
                    self._finish_add_feed()
                return
            if vk == win32con.VK_BACK:
                self._input_text = self._input_text[:-1]
                self.window.update_text(self._input_text)
                return
            ch = self._vk_to_char(vk)
            if ch:
                self._input_text += ch
                self.window.update_text(self._input_text)
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
