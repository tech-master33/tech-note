import json
import os
import time
import threading
from collections import deque
from core.config import TECH_SOFT

NOTIFY_FILE = os.path.join(TECH_SOFT, 'notifications.json')
MAX_NOTIFICATIONS = 100
DEFAULT_SOUNDS = {
    "system": "notification.wav",
    "chat": "message.wav",
    "email": "email.wav",
    "alarm": "alarm.wav",
    "reminder": "reminder.wav",
    "update": "update.wav",
    "default": "notification.wav",
}


class NotificationCenter:
    def __init__(self):
        self._notifications = deque(maxlen=MAX_NOTIFICATIONS)
        self._unread_count = 0
        self._min_priority = 0
        self._sound_sources = dict(DEFAULT_SOUNDS)
        self._dnd = False
        self._load()

    def post(self, source, text, priority=0):
        if self._dnd:
            return
        if priority < self._min_priority:
            return
        notif = {
            "source": source,
            "text": text,
            "timestamp": time.time(),
            "priority": priority,
        }
        self._notifications.append(notif)
        self._unread_count += 1
        self._save()

    def set_min_priority(self, priority):
        self._min_priority = priority

    def get_min_priority(self):
        return self._min_priority

    def set_sound_for_source(self, source, sound_file):
        self._sound_sources[source] = sound_file

    def get_sound_for_source(self, source):
        return self._sound_sources.get(source) or self._sound_sources.get("default")

    def get_all_sound_sources(self):
        return dict(self._sound_sources)

    def get_by_priority(self, min_priority=0):
        return [n for n in self._notifications if n.get("priority", 0) >= min_priority]

    def get_unread_count(self):
        return self._unread_count

    def get_latest(self):
        if not self._notifications:
            return None
        return self._notifications[-1]

    def get_all(self):
        return list(self._notifications)

    def get_history(self, source=None, limit=50):
        items = list(self._notifications)
        if source:
            items = [n for n in items if n.get("source") == source]
        return items[-limit:]

    def get_unread(self):
        return list(self._notifications)[-self._unread_count:] if self._unread_count > 0 else []

    def mark_read(self):
        self._unread_count = 0

    def set_dnd(self, enabled):
        self._dnd = enabled

    def get_dnd(self):
        return self._dnd

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
