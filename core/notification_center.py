import json
import os
import time
import threading
from collections import deque
from core.config import TECH_SOFT

NOTIFY_FILE = os.path.join(TECH_SOFT, 'notifications.json')
MAX_NOTIFICATIONS = 100

class NotificationCenter:
    def __init__(self):
        self._notifications = deque(maxlen=MAX_NOTIFICATIONS)
        self._unread_count = 0
        self._load()

    def post(self, source, text):
        notif = {
            "source": source,
            "text": text,
            "timestamp": time.time(),
        }
        self._notifications.append(notif)
        self._unread_count += 1
        self._save()

    def get_unread_count(self):
        return self._unread_count

    def get_latest(self):
        if not self._notifications:
            return None
        return self._notifications[-1]

    def get_all(self):
        return list(self._notifications)

    def mark_read(self):
        self._unread_count = 0

    def _save(self):
        try:
            with open(NOTIFY_FILE, 'w') as f:
                json.dump(list(self._notifications), f)
        except Exception:
            pass

    def _load(self):
        try:
            if os.path.exists(NOTIFY_FILE):
                with open(NOTIFY_FILE, 'r') as f:
                    data = json.load(f)
                for item in data[-MAX_NOTIFICATIONS:]:
                    self._notifications.append(item)
        except Exception:
            pass

_notification_center = None
_center_lock = threading.Lock()

def get_center():
    global _notification_center
    if _notification_center is None:
        with _center_lock:
            if _notification_center is None:
                _notification_center = NotificationCenter()
    return _notification_center
