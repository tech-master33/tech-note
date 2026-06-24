import os
import json
import threading
import time
from core.config import TECH_SOFT

AUTOSAVE_DIR = os.path.join(TECH_SOFT, 'autosave')

_callbacks = {}
_thread_started = False
_thread_lock = threading.Lock()

def register(name, is_dirty_fn, save_fn, interval=30):
    _callbacks[name] = {
        'is_dirty': is_dirty_fn,
        'save': save_fn,
        'interval': interval,
        'last_save': 0
    }
    _ensure_thread()

def _ensure_thread():
    global _thread_started
    with _thread_lock:
        if _thread_started:
            return
        _thread_started = True
    t = threading.Thread(target=_loop, daemon=True)
    t.start()

def _loop():
    while True:
        time.sleep(10)
        now = time.time()
        for name, cb in list(_callbacks.items()):
            if now - cb['last_save'] >= cb['interval']:
                try:
                    if cb['is_dirty']():
                        cb['save']()
                        cb['last_save'] = now
                except Exception:
                    pass

def get_recovery_files():
    if not os.path.exists(AUTOSAVE_DIR):
        return []
    try:
        return [f for f in os.listdir(AUTOSAVE_DIR) if f.endswith('.json')]
    except Exception:
        return []

def clear_recovery(filename):
    try:
        path = os.path.join(AUTOSAVE_DIR, filename)
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

def get_recovery_path(filename):
    os.makedirs(AUTOSAVE_DIR, exist_ok=True)
    return os.path.join(AUTOSAVE_DIR, filename)
