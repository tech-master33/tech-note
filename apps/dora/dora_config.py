import os
import json
from core.config import TECH_SOFT

DORA_DIR = os.path.join(TECH_SOFT, 'dora')
SETTINGS_FILE = os.path.join(DORA_DIR, 'settings.json')

def ensure_dirs():
    os.makedirs(DORA_DIR, exist_ok=True)

def load_settings():
    ensure_dirs()
    defaults = {
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
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                defaults.update(settings)
        except Exception:
            pass
    return defaults

def save_settings(settings):
    ensure_dirs()
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"Error saving Dora settings: {e}")

def is_first_run():
    return not os.path.exists(SETTINGS_FILE)
