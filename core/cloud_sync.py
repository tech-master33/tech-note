import json
import os
import threading
import time
from core.config import TECH_SOFT
from core.chat_client import ChatClient

SYNC_URL = 'https://tech-chat.tech-chat.workers.dev'
SYNC_FILE = os.path.join(TECH_SOFT, 'cloud_sync.json')
SYNC_INTERVAL = 300

SYNCABLES = {
    "settings": "settings.json",
    "notes": "notes.json",
    "contacts": "address_book.json",
    "favorites": "favorites.json",
    "download_counts": "download_counts.json",
}

_sync_instance = None


def get_cloud_sync():
    global _sync_instance
    if _sync_instance is None:
        _sync_instance = CloudSync()
    return _sync_instance


def _load_json(path, default=None):
    if default is None:
        default = {}
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
    except:
        pass
    return default


def _save_json(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f)
    except:
        pass


class CloudSync:
    def __init__(self):
        self._client = None
        self._username = None
        self._password = None
        self._config = _load_json(SYNC_FILE, {"enabled": False, "auto_sync": True})
        self._synced_versions = self._config.get("versions", {})
        self._running = False
        self._thread = None

    def configure(self, username, password):
        self._username = username
        self._password = password

    def set_enabled(self, enabled):
        self._config["enabled"] = enabled
        _save_json(SYNC_FILE, self._config)

    def is_enabled(self):
        return self._config.get("enabled", False)

    def set_auto_sync(self, enabled):
        self._config["auto_sync"] = enabled
        _save_json(SYNC_FILE, self._config)

    def _ensure_client(self):
        if not self._client or not self._client.is_connected:
            if self._username and self._password:
                self._client = ChatClient(SYNC_URL)
                try:
                    self._client.login(self._username, self._password)
                    return True
                except:
                    self._client = None
                    return False
        return bool(self._client and self._client.is_connected)

    def _get_sync_key(self, data_type):
        return f"sync_{data_type}_{self._username}"

    def push(self, data_type):
        if not self.is_enabled():
            return False
        if not self._ensure_client():
            return False
        filepath = os.path.join(TECH_SOFT, SYNCABLES.get(data_type, f"{data_type}.json"))
        if not os.path.exists(filepath):
            return False
        try:
            with open(filepath, 'rb') as f:
                data = f.read()
            import base64
            b64 = base64.b64encode(data).decode('ascii')
            result = self._client.upload_file(filepath)
            if result and result.get('id'):
                version = str(int(time.time()))
                self._synced_versions[data_type] = version
                self._config["versions"] = self._synced_versions
                _save_json(SYNC_FILE, self._config)
                return True
        except:
            pass
        return False

    def pull(self, data_type):
        if not self.is_enabled():
            return False
        if not self._ensure_client():
            return False
        try:
            result = self._client._get(f"sync/{data_type}")
            if result and result.get('data'):
                import base64
                data = base64.b64decode(result['data'])
                filepath = os.path.join(TECH_SOFT, SYNCABLES.get(data_type, f"{data_type}.json"))
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'wb') as f:
                    f.write(data)
                version = result.get('version', str(int(time.time())))
                self._synced_versions[data_type] = version
                self._config["versions"] = self._synced_versions
                _save_json(SYNC_FILE, self._config)
                return True
        except:
            pass
        return False

    def sync_all(self):
        if not self.is_enabled():
            return
        if not self._ensure_client():
            return
        for data_type in SYNCABLES:
            try:
                self.push(data_type)
            except:
                pass

    def start_auto_sync(self):
        if self._running:
            return
        self._running = True

        def _loop():
            while self._running:
                if self.is_enabled() and self._config.get("auto_sync", True):
                    try:
                        self.sync_all()
                    except:
                        pass
                self._running = False
                if self._stop_event:
                    break
                for _ in range(SYNC_INTERVAL):
                    if self._stop_event and self._stop_event.is_set():
                        self._running = False
                        return
                    time.sleep(1)

        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop_auto_sync(self):
        self._running = False
        if self._stop_event:
            self._stop_event.set()
        self._thread = None

    def get_config(self):
        return dict(self._config)
