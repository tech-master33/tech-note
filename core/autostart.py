import os
import sys
import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "Tech-Note"


def _boot_command():
    """Return the quoted command used to launch Tech-Note at login."""
    exe = sys.executable
    base, ext = os.path.splitext(exe)
    pythonw = base + "w" + ext
    if os.path.exists(pythonw):
        exe = pythonw  # no console window at login
    boot = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "boot_64.py")
    return f'"{exe}" "{boot}"'


def is_autostart_enabled():
    """Return True if the Tech-Note Run entry exists."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
            return True
    except (FileNotFoundError, OSError):
        return False


def enable_autostart():
    """Register Tech-Note to start when the user logs in. Returns True on success."""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _boot_command())
        return True
    except OSError:
        return False


def disable_autostart():
    """Remove the Tech-Note Run entry. Returns True on success (or if already absent)."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, VALUE_NAME)
        return True
    except FileNotFoundError:
        return True  # already disabled
    except OSError:
        return False
