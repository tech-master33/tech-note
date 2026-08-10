import json
import os
import time
from collections import deque
from core.config import TECH_SOFT

HISTORY_FILE = os.path.join(TECH_SOFT, 'clipboard_history.json')
MAX_HISTORY = 50

_history = deque(maxlen=MAX_HISTORY)


def _load():
    global _history
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                data = json.load(f)
            _history = deque(data[-MAX_HISTORY:], maxlen=MAX_HISTORY)
    except Exception:
        _history = deque(maxlen=MAX_HISTORY)


def _save():
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(list(_history), f)
    except Exception:
        pass


def push(text):
    if not text or text.strip() == "":
        return
    _load()
    if _history and _history[-1] == text:
        return
    _history.append(text)
    _save()


def get_all():
    _load()
    return list(reversed(_history))


def clear():
    _history.clear()
    _save()


def remove(index):
    _load()
    if 0 <= index < len(_history):
        items = list(_history)
        items.pop(index)
        _history = deque(items, maxlen=MAX_HISTORY)
        _save()


def count():
    _load()
    return len(_history)
