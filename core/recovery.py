import os
import sys
import subprocess
import json
import win32con
import win32api
from core.audio_player import AudioPlayer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQ_PATH = os.path.join(BASE_DIR, 'requirements.txt')
RECOVERY_SOUNDS = os.path.join(BASE_DIR, 'sounds', 'recovery')

PLAYER = AudioPlayer()

RECOVERY_MENU_ITEMS = [
    ("Restore to Stable", "restore_stable"),
    ("Reinstall Requirements", "reinstall_reqs"),
    ("Check Integrity", "check_integrity"),
    ("Recreate Tech-Soft", "recreate_techsoft"),
    ("Exit Recovery", "exit_recovery"),
]

def _sam_speak(phrase):
    fname = phrase.lower().replace(' ', '_').replace('-', '_') + '.wav'
    path = os.path.join(RECOVERY_SOUNDS, fname)
    if os.path.exists(path):
        PLAYER.play_sound_blocking(path)
        return True
    return False

def _sam_announce(phrase):
    _sam_speak(phrase)

def _play_click():
    path = os.path.join(RECOVERY_SOUNDS, 'click.wav')
    if os.path.exists(path):
        PLAYER.play_sound_blocking(path)

def check_repo_integrity():
    issues = []
    if not os.path.exists(os.path.join(BASE_DIR, '.git')):
        issues.append("git_repo_missing")
    for f in ['boot_64.py', 'core/menu.py', 'core/config.py']:
        if not os.path.exists(os.path.join(BASE_DIR, f)):
            issues.append(f"missing_file_{f}")
    return issues

def check_sapi():
    try:
        import comtypes.client
        engine = comtypes.client.CreateObject("SAPI.SpVoice")
        voices = engine.GetVoices()
        return voices.Count > 0
    except Exception:
        return False

def check_requirements():
    if not os.path.exists(REQ_PATH):
        return []
    missing = []
    with open(REQ_PATH, 'r') as f:
        for line in f:
            pkg = line.strip()
            if not pkg or pkg.startswith('#'):
                continue
            pkg_name = pkg.split('==')[0].split('>=')[0].split('<=')[0].strip()
            try:
                __import__(pkg_name)
            except ImportError:
                missing.append(pkg_name)
    return missing

def check_techsoft():
    from core.config import TECH_SOFT, SETTINGS_PATH, ACCOUNT_PATH
    if not os.path.exists(TECH_SOFT):
        return [("techsoft_missing", "Tech-soft directory not found.")]
    issues = []
    if not os.path.exists(SETTINGS_PATH):
        issues.append(("settings_missing", "Settings file not found."))
    return issues

def run_auto_checks():
    issues = []
    repo_issues = check_repo_integrity()
    for i in repo_issues:
        issues.append(("repo", i))
    if not check_sapi():
        issues.append(("sapi", "Speech engine unavailable."))
    missing_reqs = check_requirements()
    if missing_reqs:
        issues.append(("requirements", f"Missing: {', '.join(missing_reqs)}"))
    issues.extend(check_techsoft())
    return issues

def auto_repair_requirements():
    missing = check_requirements()
    if not missing:
        return True
    return repair_requirements()

def repair_clone():
    _sam_announce("restoring to stable")
    remote = _get_remote_url()
    if not remote:
        _sam_announce("no remote configured")
        return False
    parent = os.path.dirname(BASE_DIR)
    backup = BASE_DIR + "_bak"
    try:
        if os.path.exists(backup):
            import shutil
            shutil.rmtree(backup)
        os.rename(BASE_DIR, backup)
        result = subprocess.run(
            ["git", "clone", remote, os.path.basename(BASE_DIR)],
            cwd=parent, capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            _sam_announce("restore complete")
            repair_requirements()
            return True
        os.rename(backup, BASE_DIR)
        _sam_announce("restore failed")
        return False
    except Exception as e:
        _sam_announce("restore error")
        return False

def _get_remote_url():
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None

def repair_requirements():
    req_path = os.path.join(BASE_DIR, 'requirements.txt')
    if not os.path.exists(req_path):
        _sam_announce("no requirements file")
        return False
    _sam_announce("installing requirements")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req_path],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            _sam_announce("requirements installed")
            return True
        _sam_announce("requirements failed")
        return False
    except Exception:
        _sam_announce("requirements error")
        return False

def recreate_techsoft():
    from core.config import TECH_SOFT
    import shutil
    if os.path.exists(TECH_SOFT):
        try:
            shutil.rmtree(TECH_SOFT)
        except Exception:
            pass
    os.makedirs(TECH_SOFT, exist_ok=True)
    for folder in ['documents', 'downloads', 'contacts', 'desktop']:
        os.makedirs(os.path.join(TECH_SOFT, folder), exist_ok=True)
    _sam_announce("tech soft recreated")

class RecoveryMenu:
    def __init__(self, window=None):
        self.items = RECOVERY_MENU_ITEMS
        self.index = 0
        self.active = True
        self.window = window

    def _announce_item(self):
        title = self.items[self.index][0]
        _sam_announce(title)
        if self.window:
            self.window.update_text("Tech-Note Recovery: " + title)

    def next(self):
        self.index = (self.index + 1) % len(self.items)
        _play_click()
        self._announce_item()

    def previous(self):
        self.index = (self.index - 1) % len(self.items)
        _play_click()
        self._announce_item()

    def select(self):
        _play_click()
        action = self.items[self.index][1]
        if action == "restore_stable":
            repair_clone()
        elif action == "reinstall_reqs":
            repair_requirements()
        elif action == "check_integrity":
            self._run_integrity_check()
        elif action == "recreate_techsoft":
            recreate_techsoft()
        elif action == "exit_recovery":
            self.active = False
            _sam_announce("exiting recovery")
        if self.active:
            self._announce_item()

    def _run_integrity_check(self):
        _sam_announce("running integrity check")
        issues = run_auto_checks()
        if not issues:
            _sam_announce("all checks passed")
        else:
            for category, detail in issues:
                _sam_announce(category + " " + detail)

    def handle_key(self, vk):
        if vk in (win32con.VK_UP, win32con.VK_BACK):
            self.previous()
        elif vk in (win32con.VK_DOWN, win32con.VK_SPACE):
            self.next()
        elif vk == win32con.VK_RETURN:
            self.select()

def run_recovery(window):
    menu = RecoveryMenu(window)
    _sam_announce("recovery mode")
    if window:
        window.update_text("Tech-Note Recovery")
    menu._announce_item()
    return menu
