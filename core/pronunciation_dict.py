import json
import os
import re
from core.config import TECH_SOFT

DICT_FILE = os.path.join(TECH_SOFT, 'pronunciation_dict.json')

_entries = {}

def load():
    global _entries
    try:
        if os.path.exists(DICT_FILE):
            with open(DICT_FILE, 'r') as f:
                _entries = json.load(f)
    except Exception:
        _entries = {}

def save():
    try:
        with open(DICT_FILE, 'w') as f:
            json.dump(_entries, f, indent=2)
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

def apply(text):
    if not _entries:
        return text
    result = text
    for word, spoken in _entries.items():
        result = re.sub(r'\b' + re.escape(word) + r'\b', spoken, result, flags=re.IGNORECASE)
    return result
