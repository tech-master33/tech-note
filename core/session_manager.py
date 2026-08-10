import json
import os
import time
from core.config import TECH_SOFT

SESSION_FILE = os.path.join(TECH_SOFT, 'session_state.json')


def save_session(app_name, state):
    try:
        data = {}
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, 'r') as f:
                data = json.load(f)
        data[app_name] = {"state": state, "timestamp": time.time()}
        with open(SESSION_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def load_session(app_name):
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, 'r') as f:
                data = json.load(f)
            entry = data.get(app_name)
            if entry:
                return entry.get("state")
    except Exception:
        pass
    return None


def list_sessions():
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, 'r') as f:
                data = json.load(f)
            return list(data.keys())
    except Exception:
        pass
    return []


def clear_session(app_name):
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, 'r') as f:
                data = json.load(f)
            data.pop(app_name, None)
            with open(SESSION_FILE, 'w') as f:
                json.dump(data, f, indent=2)
    except Exception:
        pass


def clear_all():
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
    except Exception:
        pass
