import datetime
import os
import json
import threading
import traceback
from core.config import TECH_SOFT

LOG_FILE = os.path.join(TECH_SOFT, 'tech-note.log')
CRASH_REPORT_FILE = os.path.join(TECH_SOFT, 'crash_reports.json')
MAX_LOG_SIZE = 5 * 1024 * 1024
MAX_CRASH_REPORTS = 20

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
_crash_reports = []
_crash_lock = threading.Lock()


def _load_crash_reports():
    global _crash_reports
    try:
        if os.path.exists(CRASH_REPORT_FILE):
            with open(CRASH_REPORT_FILE, 'r') as f:
                _crash_reports = json.load(f)[-MAX_CRASH_REPORTS:]
    except Exception:
        _crash_reports = []


def _save_crash_reports():
    try:
        with open(CRASH_REPORT_FILE, 'w') as f:
            json.dump(_crash_reports[-MAX_CRASH_REPORTS:], f, indent=2)
    except Exception:
        pass


def report_crash(exception, context=""):
    _load_crash_reports()
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "context": context,
        "exception": str(exception),
        "traceback": traceback.format_exc(),
    }
    with _crash_lock:
        _crash_reports.append(report)
        _save_crash_reports()
    log(exception, f"CRASH: {context}", level=LEVEL_ERROR)


def get_crash_reports():
    _load_crash_reports()
    return list(reversed(_crash_reports))


def clear_crash_reports():
    with _crash_lock:
        _crash_reports.clear()
        _save_crash_reports()


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
