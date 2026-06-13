# Tests that key modules import and instantiate without crashing.
# Run: python project\temp\smoke_test.py

import os
import sys
import tempfile
import importlib

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE)

errors = []

def check(label, fn):
    try:
        fn()
        print(f"  PASS: {label}")
    except Exception as e:
        print(f"  FAIL: {label} \u2014 {e}")
        errors.append(label)

print("Smoke tests for Tech-Note features")
print("=" * 40)

check("audio_player import", lambda: __import__("core.audio_player"))
check("audio_ducking import", lambda: __import__("core.audio_ducking"))
check("menu import", lambda: __import__("core.menu"))
check("config import", lambda: __import__("core.config"))
check("app_base import", lambda: __import__("core.app_base"))

check("AudioPlayer instantiation", lambda: __import__("core.audio_player", fromlist=["AudioPlayer"]))
check("AudioDucker instantiation", lambda: __import__("core.audio_ducking", fromlist=["AudioDucker"]))

check("menu has SOUND_SCHEME", lambda: importlib.import_module("core.menu").SOUND_SCHEME)
check("menu has ANNOUNCE_POSITION", lambda: importlib.import_module("core.menu").ANNOUNCE_POSITION)
check("menu has _get_sound_path", lambda: importlib.import_module("core.menu")._get_sound_path)

check("synths registry import", lambda: __import__("synths.registry"))
check("synths sapi_synth import", lambda: __import__("synths.sapi_synth"))

def _check_synth_methods():
    from synths.sapi_synth import SapiSynthBase
    for m in ["get_pitch", "set_pitch", "get_capital_pitch_change",
              "set_capital_pitch_change",
              "set_volume_ducking", "set_punctuation_level"]:
        if not hasattr(SapiSynthBase, m):
            raise AttributeError(f"SapiSynthBase missing {m}")

check("synth has required methods", _check_synth_methods)

check("options_menu import", lambda: __import__("apps.options_menu"))
check("settings_app import", lambda: __import__("apps.settings_app"))
check("recovery import", lambda: __import__("core.recovery"))

def _check_options_keys():
    fake = {"pitch": 50, "capital_pitch_change": "Off", "state_keys": "Off",
            "volume_ducking": "Off", "sound_scheme": "Default"}
    for k in ["pitch", "capital_pitch_change", "state_keys",
              "volume_ducking", "sound_scheme"]:
        if k not in fake:
            raise KeyError(f"Missing setting: {k}")

check("options_menu settings keys", _check_options_keys)

print("=" * 40)
if errors:
    print(f"FAILED: {len(errors)} test(s)")
    sys.exit(1)
else:
    print("ALL PASSED")
