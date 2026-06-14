import os
import sys
import subprocess
import win32con

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQ_PATH = os.path.join(BASE_DIR, 'requirements.txt')

_SPEAKER = None

def _get_speaker():
    global _SPEAKER
    if _SPEAKER is not None:
        return _SPEAKER
    try:
        import comtypes.client
        import pythoncom
        pythoncom.CoInitialize()
        _SPEAKER = comtypes.client.CreateObject("SAPI.SpVoice")
    except Exception:
        _SPEAKER = False
    return _SPEAKER

def _speak(text):
    sp = _get_speaker()
    if sp:
        try:
            sp.Speak(text, 1)
        except Exception:
            pass

RECOVERY_MENU_ITEMS = [
    ("Reinstall Requirements", "reinstall_reqs"),
    ("Check Integrity", "check_integrity"),
    ("Recreate Tech-Soft", "recreate_techsoft"),
    ("Exit Recovery", "exit_recovery"),
]

def check_repo_integrity():
    issues = []
    for f in ['boot_64.py', 'core/menu.py', 'core/config.py']:
        if not os.path.exists(os.path.join(BASE_DIR, f)):
            issues.append(f"missing_file_{f}")
    return issues

def check_requirements():
    if not os.path.exists(REQ_PATH):
        return []
    missing = []
    import importlib.metadata
    installed = set()
    for dist in importlib.metadata.distributions():
        try:
            name = dist.metadata.get('Name', '')
            if name:
                installed.add(name.lower())
        except Exception:
            pass
    PACKAGE_MAP = {"pywin32": "pywin32", "pycryptodome": "pycryptodome", "beautifulsoup4": "beautifulsoup4"}
    with open(REQ_PATH, 'r') as f:
        for line in f:
            pkg = line.strip()
            if not pkg or pkg.startswith('#'):
                continue
            pkg_name = pkg.split('==')[0].split('>=')[0].split('<=')[0].strip().lower()
            lookup = PACKAGE_MAP.get(pkg_name, pkg_name)
            if lookup not in installed:
                missing.append(pkg_name)
    return missing

def check_techsoft():
    from core.config import TECH_SOFT, SETTINGS_PATH
    if not os.path.exists(TECH_SOFT):
        return [("techsoft_missing", "Tech-soft directory not found.")]
    issues = []
    if not os.path.exists(SETTINGS_PATH):
        issues.append(("settings_missing", "Settings file not found."))
    return issues

def run_auto_checks():
    issues = []
    issues.extend([("repo", i) for i in check_repo_integrity()])
    missing_reqs = check_requirements()
    if missing_reqs:
        issues.append(("requirements", f"Missing: {', '.join(missing_reqs)}"))
    issues.extend(check_techsoft())
    return issues

def repair_requirements():
    if not os.path.exists(REQ_PATH):
        return False
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        result = subprocess.run(
            f'cmd /c "{sys.executable}" -m pip install -r "{REQ_PATH}"',
            shell=True, capture_output=True, text=True, timeout=120, startupinfo=si
        )
        return result.returncode == 0 and not check_requirements()
    except Exception:
        return False

def recreate_techsoft():
    from core.config import TECH_SOFT
    import shutil
    if os.path.exists(TECH_SOFT):
        shutil.rmtree(TECH_SOFT)
    os.makedirs(TECH_SOFT, exist_ok=True)
    for folder in ['documents', 'downloads', 'contacts', 'desktop']:
        os.makedirs(os.path.join(TECH_SOFT, folder), exist_ok=True)

class RecoveryMenu:
    def __init__(self, window=None):
        self.index = 0
        self.active = True
        self.window = window
        self.items = RECOVERY_MENU_ITEMS

    def _announce(self, text):
        _speak(text)
        if self.window:
            self.window.update_text("Tech-Note Recovery: " + text)

    def next(self):
        self.index = (self.index + 1) % len(self.items)
        self._announce(self.items[self.index][0])

    def previous(self):
        self.index = (self.index - 1) % len(self.items)
        self._announce(self.items[self.index][0])

    def select(self):
        action = self.items[self.index][1]
        if action == "reinstall_reqs":
            self._announce("Reinstalling requirements.")
            ok = repair_requirements()
            self._announce("Success" if ok else "Failed")
        elif action == "check_integrity":
            issues = run_auto_checks()
            if not issues:
                self._announce("All checks passed.")
            else:
                self._announce("Issues: " + "; ".join(d for _, d in issues))
        elif action == "recreate_techsoft":
            self._announce("Recreating folders.")
            recreate_techsoft()
            self._announce("Folders recreated.")
        elif action == "exit_recovery":
            self.active = False
            self._announce("Exiting.")
            if self.window:
                self.window.close()
        if self.active:
            self._announce(self.items[self.index][0])

    def handle_key(self, vk):
        if vk in (win32con.VK_UP, win32con.VK_BACK):
            self.previous()
        elif vk in (win32con.VK_DOWN, win32con.VK_SPACE):
            self.next()
        elif vk == win32con.VK_RETURN:
            self.select()

def run_recovery(window):
    menu = RecoveryMenu(window)
    if window:
        window.update_text("Tech-Note Recovery")
    _speak("Recovery Menu")
    menu._announce(menu.items[menu.index][0])
    return menu
