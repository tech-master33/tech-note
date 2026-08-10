import json
import os
import re
from core.config import TECH_SOFT

DICT_FILE = os.path.join(TECH_SOFT, 'pronunciation_dict.json')
APP_OVERRIDE_FILE = os.path.join(TECH_SOFT, 'pronunciation_overrides.json')

_entries = {}
_app_overrides = {}

def load():
    global _entries, _app_overrides
    try:
        if os.path.exists(DICT_FILE):
            with open(DICT_FILE, 'r') as f:
                _entries = json.load(f)
    except Exception:
        _entries = {}
    try:
        if os.path.exists(APP_OVERRIDE_FILE):
            with open(APP_OVERRIDE_FILE, 'r') as f:
                _app_overrides = json.load(f)
    except Exception:
        _app_overrides = {}

def save():
    try:
        with open(DICT_FILE, 'w') as f:
            json.dump(_entries, f, indent=2)
    except Exception:
        pass

def save_overrides():
    try:
        with open(APP_OVERRIDE_FILE, 'w') as f:
            json.dump(_app_overrides, f, indent=2)
    except Exception:
        pass

def add(word, spoken):
    _entries[word.lower()] = spoken
    save()

def remove(word):
    _entries.pop(word.lower(), None)
    save()

def get_all():
    return dict(_entries)

def clear_all():
    _entries.clear()
    save()

def export_to_file(path):
    try:
        data = {"entries": dict(_entries), "app_overrides": dict(_app_overrides)}
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False

def import_from_file(path):
    global _entries, _app_overrides
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        if "entries" in data:
            _entries.update(data["entries"])
        if "app_overrides" in data:
            _app_overrides.update(data["app_overrides"])
        save()
        save_overrides()
        return True
    except Exception:
        return False

def set_app_override(app_name, word, spoken):
    if app_name not in _app_overrides:
        _app_overrides[app_name] = {}
    _app_overrides[app_name][word.lower()] = spoken
    save_overrides()

def remove_app_override(app_name, word):
    if app_name in _app_overrides:
        _app_overrides[app_name].pop(word.lower(), None)
        if not _app_overrides[app_name]:
            del _app_overrides[app_name]
        save_overrides()

def get_app_overrides(app_name=None):
    if app_name:
        return dict(_app_overrides.get(app_name, {}))
    return dict(_app_overrides)

def apply(text, app_name=None):
    if not _entries and not app_name:
        return text
    result = text
    for word, spoken in _entries.items():
        result = re.sub(r'\b' + re.escape(word) + r'\b', lambda m: spoken, result, flags=re.IGNORECASE)
    if app_name and app_name in _app_overrides:
        for word, spoken in _app_overrides[app_name].items():
            result = re.sub(r'\b' + re.escape(word) + r'\b', lambda m: spoken, result, flags=re.IGNORECASE)
    return result
