import os
import json
from core.config import TECH_SOFT, SETTINGS_PATH

DORA_KEYS = [
    'username', 'ai_enabled', 'ai_provider', 'ai_endpoint',
    'ai_model', 'ai_api_key', 'wake_word', 'language', 'tts_rate'
]

DORA_DEFAULTS = {
    'username': 'User',
    'ai_enabled': False,
    'ai_provider': 'ollama',
    'ai_endpoint': 'http://localhost:11434/v1',
    'ai_model': 'llama3',
    'ai_api_key': '',
    'wake_word': 'computer',
    'language': 'en',
    'tts_rate': 0,
}

def _load_all_settings():
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_all_settings(data):
    os.makedirs(TECH_SOFT, exist_ok=True)
    try:
        with open(SETTINGS_PATH, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving settings: {e}")

def load_settings():
    all_settings = _load_all_settings()
    result = DORA_DEFAULTS.copy()
    result.update({k: all_settings[k] for k in DORA_KEYS if k in all_settings})
    return result

def save_settings(dora_settings):
    all_settings = _load_all_settings()
    for k in DORA_KEYS:
        if k in dora_settings:
            all_settings[k] = dora_settings[k]
    _save_all_settings(all_settings)

def is_first_run():
    all_settings = _load_all_settings()
    return not any(k in all_settings for k in DORA_KEYS)
