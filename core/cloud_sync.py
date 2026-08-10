import json
import os
import time
from core.config import TECH_SOFT

SYNC_FILE = os.path.join(TECH_SOFT, 'cloud_sync.json')
CLOUD_DIR = os.path.join(TECH_SOFT, 'cloud_backups')


def _ensure_cloud_dir():
    os.makedirs(CLOUD_DIR, exist_ok=True)


def export_to_cloud(label=""):
    _ensure_cloud_dir()
    timestamp = int(time.time())
    safe_label = "".join(c for c in label if c.isalnum() or c in " _-") if label else f"backup_{timestamp}"
    dest = os.path.join(CLOUD_DIR, f"{safe_label}.json")
    data = {
        "timestamp": timestamp,
        "label": label,
        "version": 1,
        "settings": {},
    }
    settings_path = os.path.join(TECH_SOFT, 'settings.json')
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as f:
                data["settings"] = json.load(f)
        except Exception:
            pass
    try:
        with open(dest, 'w') as f:
            json.dump(data, f, indent=2)
        with open(SYNC_FILE, 'w') as f:
            json.dump({"last_sync": timestamp, "last_file": dest}, f)
        return True
    except Exception:
        return False


def import_from_cloud(path=None):
    if not path:
        backups = list_cloud_backups()
        if not backups:
            return False
        path = backups[-1]["path"]
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        settings = data.get("settings", {})
        if settings:
            settings_path = os.path.join(TECH_SOFT, 'settings.json')
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=2)
        with open(SYNC_FILE, 'w') as f:
            json.dump({"last_sync": int(time.time()), "last_file": path}, f)
        return True
    except Exception:
        return False


def list_cloud_backups():
    _ensure_cloud_dir()
    backups = []
    try:
        for fname in sorted(os.listdir(CLOUD_DIR), reverse=True):
            fpath = os.path.join(CLOUD_DIR, fname)
            if fname.endswith('.json'):
                try:
                    with open(fpath, 'r') as f:
                        data = json.load(f)
                    backups.append({
                        "path": fpath,
                        "filename": fname,
                        "label": data.get("label", fname),
                        "timestamp": data.get("timestamp", 0),
                    })
                except Exception:
                    backups.append({
                        "path": fpath,
                        "filename": fname,
                        "label": fname,
                        "timestamp": 0,
                    })
    except Exception:
        pass
    return backups


def get_last_sync():
    try:
        if os.path.exists(SYNC_FILE):
            with open(SYNC_FILE, 'r') as f:
                data = json.load(f)
            return data.get("last_sync", 0)
    except Exception:
        pass
    return 0
