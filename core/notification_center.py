import json
import os
import time
import threading
from collections import deque
from core.config import TECH_SOFT

NOTIFY_FILE = os.path.join(TECH_SOFT, 'notifications.json')
MAX_NOTIFICATIONS = 100

PRIORITY_LOW = "low"
PRIORITY_NORMAL = "normal"
PRIORITY_HIGH = "high"
PRIORITY_CRITICAL = "critical"


class NotificationCenter:
    def __init__(self):
        self._notifications = deque(maxlen=MAX_NOTIFICATIONS)
        self._unread_count = 0
        self._dnd = False
        self._load()
        try:
            from core.settings_manager import settings_manager
            self._dnd = settings_manager.get("notifications", "dnd_enabled", False)
        except Exception:
            pass

    def post(self, source, text, priority=PRIORITY_NORMAL):
        if self._dnd and priority in (PRIORITY_LOW, PRIORITY_NORMAL):
            return
        notif = {
            "source": source,
            "text": text,
            "priority": priority,
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

    def get_by_priority(self, min_priority):
        levels = {"low": 0, "normal": 1, "high": 2, "critical": 3}
        min_level = levels.get(min_priority, 0)
        return [n for n in self._notifications if levels.get(n.get("priority", "normal"), 1) >= min_level]

    def mark_read(self):
        self._unread_count = 0

    def set_dnd(self, enabled):
        self._dnd = enabled

    def get_dnd(self):
        return self._dnd

    def clear(self):
        self._notifications.clear()
        self._unread_count = 0
        self._save()

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
                    if "priority" not in item:
                        item["priority"] = PRIORITY_NORMAL
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
