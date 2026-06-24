import os
from core.config import TECH_SOFT

CRASH_COUNT_FILE = os.path.join(TECH_SOFT, '.crash_count')
MAX_CRASHES = 3

def _get_crash_count():
    try:
        if os.path.exists(CRASH_COUNT_FILE):
            with open(CRASH_COUNT_FILE, 'r') as f:
                return int(f.read().strip())
    except Exception:
        pass
    return 0

def _set_crash_count(count):
    try:
        with open(CRASH_COUNT_FILE, 'w') as f:
            f.write(str(count))
    except Exception:
        pass

def record_crash():
    count = _get_crash_count() + 1
    _set_crash_count(count)
    return count

def record_clean_exit():
    _set_crash_count(0)

def should_enter_safe_mode():
    return _get_crash_count() >= MAX_CRASHES

def clear_safe_mode():
    _set_crash_count(0)

SAFE_MODE_FILE = os.path.join(TECH_SOFT, '.safe_mode')

def is_safe_mode():
    return os.path.exists(SAFE_MODE_FILE)

def set_safe_mode(enabled):
    if enabled:
        try:
            with open(SAFE_MODE_FILE, 'w'):
                pass
        except Exception:
            pass
    else:
        try:
            if os.path.exists(SAFE_MODE_FILE):
                os.remove(SAFE_MODE_FILE)
        except Exception:
            pass
