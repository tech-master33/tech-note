import json
import os
import threading
import tempfile
from core.config import TECH_SOFT

SETTINGS_PATH = os.path.join(TECH_SOFT, 'settings.json')
SCHEMA_VERSION = 1

DEFAULT_SCHEMA = {
    "display": {
        "theme": "Dark",
        "bg_color": "Black",
        "font_size": "Medium",
        "night_mode_filter": False,
    },
    "system": {
        "time_format": "12h",
        "startup_sound": "On",
        "keyboard_layout": "US",
        "update_channel": "stable",
        "auto_update_on_startup": False,
        "auto_resume_apps": True,
        "smooth_shutdown_audio": True,
        "app_sleep_hibernate": True,
        "shutdown_key_protection": True,
        "log_level": "WARN",
        "custom_goodbye": "Goodbye.",
        "shutdown_pin": False,
    },
    "tts": {
        "rate": 0,
        "volume": 100,
        "voice_index": 0,
        "pitch": 50,
        "punctuation_level": "Some",
        "capital_pitch_change": "Off",
        "speech_history_size": 50,
        "rate_range": 30,
    },
    "keyboard": {
        "char_echo": "Off",
        "word_echo": "Off",
        "typing_echo_mode": "",
        "announce_position": "On",
        "state_keys": "Off",
    },
    "audio": {
        "volume_ducking": "Off",
        "sound_scheme": "Default",
    },
    "braille": {
        "braille_display": "Off",
        "braille_grade": 2,
    },
    "notifications": {
        "dnd_enabled": False,
    },
    "custom": {
        "key_bindings": {},
        "voice_profiles": {},
        "per_app_voice": {},
    },
}


class SettingsManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._data = {}
        self._load()

    def get(self, category, key, default=None):
        with self._lock:
            return self._data.get(category, {}).get(key, default)

    def set(self, category, key, value):
        with self._lock:
            self._data.setdefault(category, {})[key] = value

    def set_multi(self, category, items):
        with self._lock:
            cat = self._data.setdefault(category, {})
            cat.update(items)

    def get_category(self, category):
        with self._lock:
            return dict(self._data.get(category, {}))

    def get_all(self):
        with self._lock:
            return dict(self._data)

    def save(self):
        with self._lock:
            self._data["_schema_version"] = SCHEMA_VERSION
            os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
            tmp = tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8',
                dir=os.path.dirname(SETTINGS_PATH),
                suffix='.tmp', delete=False
            )
            try:
                json.dump(self._data, tmp, indent=2)
                tmp.close()
                os.replace(tmp.name, SETTINGS_PATH)
            except Exception:
                os.unlink(tmp.name)
                raise

    def reset_to_defaults(self):
        with self._lock:
            self._data = {}
            for cat, keys in DEFAULT_SCHEMA.items():
                self._data[cat] = dict(keys)

    def _load(self):
        self.reset_to_defaults()
        if not os.path.exists(SETTINGS_PATH):
            self.save()
            return
        try:
            with open(SETTINGS_PATH, 'r') as f:
                loaded = json.load(f)
            self._migrate(loaded)
            for cat, keys in loaded.items():
                if isinstance(keys, dict):
                    defaults = DEFAULT_SCHEMA.get(cat, {})
                    merged = dict(defaults)
                    merged.update(keys)
                    self._data[cat] = merged
                elif cat == "_schema_version":
                    pass
                else:
                    self._data[cat] = keys
        except (json.JSONDecodeError, IOError):
            backup = SETTINGS_PATH + ".corrupted"
            try:
                os.rename(SETTINGS_PATH, backup)
            except Exception:
                pass
            self.save()

    def _migrate(self, data):
        version = data.get("_schema_version", 0)
        if version < 1:
            self._migrate_v0_to_v1(data)
        data["_schema_version"] = SCHEMA_VERSION

    def _migrate_v0_to_v1(self, data):
        flat_map = {
            "theme": ("display", "theme"),
            "bg_color": ("display", "bg_color"),
            "font_size": ("display", "font_size"),
            "night_mode_filter": ("display", "night_mode_filter"),
            "time_format": ("system", "time_format"),
            "startup_sound": ("system", "startup_sound"),
            "keyboard_layout": ("system", "keyboard_layout"),
            "update_channel": ("system", "update_channel"),
            "auto_update_on_startup": ("system", "auto_update_on_startup"),
            "auto_resume_apps": ("system", "auto_resume_apps"),
            "smooth_shutdown_audio": ("system", "smooth_shutdown_audio"),
            "app_sleep_hibernate": ("system", "app_sleep_hibernate"),
            "shutdown_key_protection": ("system", "shutdown_key_protection"),
            "log_level": ("system", "log_level"),
            "custom_goodbye": ("system", "custom_goodbye"),
            "shutdown_pin": ("system", "shutdown_pin"),
            "rate": ("tts", "rate"),
            "volume": ("tts", "volume"),
            "voice_index": ("tts", "voice_index"),
            "pitch": ("tts", "pitch"),
            "punctuation_level": ("tts", "punctuation_level"),
            "capital_pitch_change": ("tts", "capital_pitch_change"),
            "speech_history_size": ("tts", "speech_history_size"),
            "char_echo": ("keyboard", "char_echo"),
            "word_echo": ("keyboard", "word_echo"),
            "announce_position": ("keyboard", "announce_position"),
            "state_keys": ("keyboard", "state_keys"),
            "volume_ducking": ("audio", "volume_ducking"),
            "sound_scheme": ("audio", "sound_scheme"),
            "braille_display": ("braille", "braille_display"),
            "braille_grade": ("braille", "braille_grade"),
            "key_bindings": ("custom", "key_bindings"),
            "voice_profiles": ("custom", "voice_profiles"),
            "per_app_voice": ("custom", "per_app_voice"),
        }
        for old_key, (cat, new_key) in flat_map.items():
            if old_key in data:
                self._data.setdefault(cat, {})[new_key] = data.pop(old_key)


settings_manager = SettingsManager()
