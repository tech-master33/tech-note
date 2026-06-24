import os
import json
import threading
import traceback
from core.config import TECH_SOFT

LOG_FILE = os.path.join(TECH_SOFT, 'tech-note.log')
MAX_LOG_SIZE = 5 * 1024 * 1024

LEVEL_SILENT = 0
LEVEL_ERROR = 1
LEVEL_WARN = 2
LEVEL_INFO = 3
LEVEL_DEBUG = 4
LEVEL_ALL = 5

LEVEL_NAMES = {
    LEVEL_SILENT: "SILENT",
    LEVEL_ERROR: "ERROR",
    LEVEL_WARN: "WARN",
    LEVEL_INFO: "INFO",
    LEVEL_DEBUG: "DEBUG",
    LEVEL_ALL: "ALL",
}

_current_level = LEVEL_WARN
_log_lock = threading.Lock()

def set_level(level):
    global _current_level
    _current_level = max(LEVEL_SILENT, min(LEVEL_ALL, level))

def get_level():
    return _current_level

def get_level_name():
    return LEVEL_NAMES.get(_current_level, "WARN")

def log(exception, context="", level=LEVEL_WARN):
    if level > _current_level:
        return
    try:
        msg = f"[{LEVEL_NAMES.get(level, '?')}] {context}"
        if exception:
            msg += f": {exception}"
            tb = traceback.format_exc()
            if tb and tb != "NoneType: None\n":
                msg += f"\n{tb}"
        with _log_lock:
            with open(LOG_FILE, 'a') as f:
                f.write(msg + "\n")
            _rotate_if_needed()
    except Exception:
        pass

def _rotate_if_needed():
    try:
        if os.path.getsize(LOG_FILE) > MAX_LOG_SIZE:
            base = LOG_FILE
            for i in range(9, 0, -1):
                old = f"{base}.{i}"
                new = f"{base}.{i + 1}"
                if os.path.exists(old):
                    os.rename(old, new)
            if os.path.exists(base):
                os.rename(base, f"{base}.1")
    except Exception:
        pass

def load_level_from_settings():
    try:
        settings_path = os.path.join(TECH_SOFT, 'settings.json')
        if os.path.exists(settings_path):
            with open(settings_path, 'r') as f:
                s = json.load(f)
            level_name = s.get("log_level", "WARN")
            name_map = {
                "SILENT": LEVEL_SILENT, "ERROR": LEVEL_ERROR,
                "WARN": LEVEL_WARN, "INFO": LEVEL_INFO,
                "DEBUG": LEVEL_DEBUG, "ALL": LEVEL_ALL,
            }
            set_level(name_map.get(level_name, LEVEL_WARN))
    except Exception:
        pass
