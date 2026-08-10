import json
import os
import time
from core.config import TECH_SOFT

CACHE_DIR = os.path.join(TECH_SOFT, 'cache')
MAX_CACHE_AGE = 3600


def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(key):
    return os.path.join(CACHE_DIR, f"{key}.json")


def get(key):
    path = _cache_path(key)
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
            if time.time() - data.get("_time", 0) < MAX_CACHE_AGE:
                return data.get("value")
    except Exception:
        pass
    return None


def set(key, value):
    _ensure_cache_dir()
    path = _cache_path(key)
    try:
        with open(path, 'w') as f:
            json.dump({"_time": time.time(), "value": value}, f)
    except Exception:
        pass


def invalidate(key):
    path = _cache_path(key)
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def clear():
    try:
        if os.path.exists(CACHE_DIR):
            import shutil
            shutil.rmtree(CACHE_DIR)
    except Exception:
        pass


def get_stats():
    try:
        if not os.path.exists(CACHE_DIR):
            return {"files": 0, "size": 0}
        total_size = 0
        count = 0
        for f in os.listdir(CACHE_DIR):
            fpath = os.path.join(CACHE_DIR, f)
            if os.path.isfile(fpath):
                total_size += os.path.getsize(fpath)
                count += 1
        return {"files": count, "size": total_size}
    except Exception:
        return {"files": 0, "size": 0}
