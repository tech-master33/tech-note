import os
import json
import time
from core.config import TECH_SOFT

AUTOSAVE_DIR = os.path.join(TECH_SOFT, 'autosave')

_callbacks = {}


def register(name, is_dirty_fn, save_fn, interval=30):
    _callbacks[name] = {
        'is_dirty': is_dirty_fn,
        'save': save_fn,
        'interval': interval,
        'last_save': 0
    }
    _ensure_service()


def tick():
    """One autosave pass: run any due dirty callbacks. Driven by the
    systmanserv 'autosave' service (10-second tick)."""
    now = time.time()
    for name, cb in list(_callbacks.items()):
        if now - cb['last_save'] >= cb['interval']:
            try:
                if cb['is_dirty']():
                    cb['save']()
                    cb['last_save'] = now
            except Exception:
                pass


def _ensure_service():
    """Make sure the systmanserv autosave service exists and is running.
    boot_64 registers it at startup; this covers standalone use of the
    module (e.g. tests) where no boot sequence has run."""
    try:
        from core.systmanserv import get_manager
        m = get_manager()
        if m.get("autosave") is None:
            m.register(
                "autosave",
                description="Autosave dirty apps every 10 seconds",
                run=tick,
                interval=10,
            )
        m.start("autosave")
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
