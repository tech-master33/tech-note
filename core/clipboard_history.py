import json
import os
import threading
import time
import win32clipboard
from core.config import TECH_SOFT

HISTORY_PATH = os.path.join(TECH_SOFT, 'clipboard_history.json')
MAX_ITEMS = 50


class ClipboardHistory:
    def __init__(self):
        self._items = []
        self._last_text = ""
        self._lock = threading.Lock()
        self._load()

    @property
    def items(self):
        with self._lock:
            return list(self._items)

    def add(self, text):
        if not text or not text.strip():
            return
        with self._lock:
            if self._items and self._items[0] == text:
                return
            if text in self._items:
                self._items.remove(text)
            self._items.insert(0, text)
            if len(self._items) > MAX_ITEMS:
                self._items = self._items[:MAX_ITEMS]
            self._save()

    def remove(self, text):
        with self._lock:
            if text in self._items:
                self._items.remove(text)
                self._save()

    def clear(self):
        with self._lock:
            self._items = []
            self._save()

    def copy_to_clipboard(self, text):
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text)
            win32clipboard.CloseClipboard()
            return True
        except Exception:
            return False

    def poll(self):
        try:
            win32clipboard.OpenClipboard()
            try:
                text = win32clipboard.GetClipboardData(win32clipboard.CF_TEXT)
                if isinstance(text, bytes):
                    text = text.decode('utf-8', errors='replace')
            except:
                try:
                    text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                except:
                    text = None
            win32clipboard.CloseClipboard()
            if text and text != self._last_text:
                self._last_text = text
                self.add(text)
        except Exception:
            pass

    def _load(self):
        if os.path.exists(HISTORY_PATH):
            try:
                with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
                    self._items = json.load(f)
            except Exception:
                self._items = []

    def _save(self):
        try:
            os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
            with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
                json.dump(self._items, f, indent=2)
        except Exception:
            pass


clipboard_history = ClipboardHistory()
