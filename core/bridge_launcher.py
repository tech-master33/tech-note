"""
core/bridge_launcher — where the 32-bit Tech-Note bridge lives.

The bridge is one unified 32-bit executable (`bridge/TechNoteBridge32.exe`,
built from `bridge/bridge_main.py` with PyInstaller under a 32-bit Python)
that serves both the SAPI TTS backend and `bits: 32` synth plugins. This
module builds the argv to launch it in a given mode, preferring the
compiled exe and falling back to a 32-bit Python + the source script so
development works before the exe is built.
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIDGE_EXE = os.path.join(BASE_DIR, "bridge", "TechNoteBridge32.exe")
BRIDGE_SCRIPT = os.path.join(BASE_DIR, "bridge", "bridge_main.py")


def bridge_command(mode, *args):
    """argv for launching the bridge. `mode` is 'tts' or 'plugin';
    `args` are extra argv (e.g. the plugin's .scrugn path, optional port).
    Returns None if neither the exe nor a 32-bit Python is available."""
    if os.path.exists(BRIDGE_EXE):
        return [BRIDGE_EXE, mode] + list(args)
    from synths.registry import _find_32bit_python
    py = _find_32bit_python()
    if not py or not os.path.exists(BRIDGE_SCRIPT):
        return None
    return [py, BRIDGE_SCRIPT, mode] + list(args)


def bridge_available():
    """True if the bridge can be launched at all (exe or script+python)."""
    if os.path.exists(BRIDGE_EXE):
        return True
    if not os.path.exists(BRIDGE_SCRIPT):
        return False
    from synths.registry import _find_32bit_python
    return _find_32bit_python() is not None
