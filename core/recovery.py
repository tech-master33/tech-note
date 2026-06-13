import os
import sys
import subprocess
import json
import win32con
import win32api
from synths.nvda import Synth as NVDASynth

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQ_PATH = os.path.join(BASE_DIR, 'requirements.txt')
LOG_PATH = os.path.join(BASE_DIR, "recovery.log")

def _log(message):
    try:
        with open(LOG_PATH, "a") as f:
            f.write(message + "
")
        print(f"RecoveryMenu: {message}")
    except Exception as e:
        print(f"Logging failed: {e}")

def check_repo_integrity():
    issues = []
    # Simplified integrity check
    for f in ['boot_64.py', 'core/menu.py', 'core/config.py']:
        if not os.path.exists(os.path.join(BASE_DIR, f)):
            issues.append(f"missing_file_{f}")
    return issues

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
    _log("Repairing requirements via cmd.")
    try:
        # Using startupinfo to guarantee the cmd window is hidden
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        command = f'cmd /c {sys.executable} -m pip install -r "{REQ_PATH}"'
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=300, 
            startupinfo=startupinfo
        )
        if result.returncode != 0:
            _log(f"Pip error: {result.stderr}")
            return False
        return not check_requirements()
    except Exception as e:
        _log(f"Repair requirements failed: {e}")
        return False

def recreate_techsoft():
    from core.config import TECH_SOFT
    import shutil
    _log("Recreating Tech-Soft directories.")
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
        self.synth = NVDASynth()

        self.items = [
            ("Reinstall Requirements", "reinstall_reqs"),
            ("Check Integrity", "check_integrity"),
            ("Recreate Tech-Soft", "recreate_techsoft"),
            ("Exit Recovery", "exit_recovery"),
        ]

    def _log(self, message):
        _log(message)

    def _speak(self, text):
        self._log(f"Speaking: {text}")
        if self.synth and self.synth.is_valid:
            self.synth.speak(text)

    def _update_display(self):
        title = self.items[self.index][0]
        display_text = f"Recovery: {title}"
        
        if self.window:
            self.window.update_text(display_text)
        
        self._speak(title)
        self._log(f"Displaying: {display_text}")

    def next(self):
        self.index = (self.index + 1) % len(self.items)
        self._update_display()

    def previous(self):
        self.index = (self.index - 1) % len(self.items)
        self._update_display()

    def select(self):
        action = self.items[self.index][1]
        self._log(f"Selected action: {action}")
        
        if action == "reinstall_reqs":
            self._speak("Reinstalling requirements.")
            self._speak("Success" if repair_requirements() else "Failed")
        elif action == "check_integrity":
            self._run_integrity_check()
        elif action == "recreate_techsoft":
            self._speak("Recreating folders.")
            recreate_techsoft()
            self._speak("Folders recreated.")
        elif action == "exit_recovery":
            self.active = False
            self._speak("Exiting.")
            if self.window:
                self.window.close()
        
        if self.active:
            self._update_display()

    def _run_integrity_check(self):
        self._log("Running integrity check.")
        issues = run_auto_checks()
        if not issues:
            self._speak("All checks passed.")
            if self.window: self.window.update_text("All checks passed.")
        else:
            issue_text = "Issues: " + "; ".join(d for _, d in issues)
            self._speak(issue_text)
            if self.window: self.window.update_text(issue_text)

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
    menu._speak("Recovery Menu")
    menu._update_display()
    return menu
