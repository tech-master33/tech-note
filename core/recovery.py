import os
import sys
import subprocess
import json
import win32con
import win32api
from synths.nvda import Synth as NVDASynth

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQ_PATH = os.path.join(BASE_DIR, 'requirements.txt')



def check_repo_integrity():
    issues = []
    if not os.path.exists(os.path.join(BASE_DIR, '.git')):
        issues.append("git_repo_missing")
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
    from core.config import TECH_SOFT, SETTINGS_PATH, ACCOUNT_PATH
    if not os.path.exists(TECH_SOFT):
        return [("techsoft_missing", "Tech-soft directory not found.")]
    issues = []
    if not os.path.exists(SETTINGS_PATH):
        issues.append(("settings_missing", "Settings file not found."))
    return issues

def run_auto_checks():
    issues = []
    for i in check_repo_integrity():
        issues.append(("repo", i))
    missing_reqs = check_requirements()
    if missing_reqs:
        issues.append(("requirements", f"Missing: {', '.join(missing_reqs)}"))
    issues.extend(check_techsoft())
    return issues

def get_current_git_branch():
    if not os.path.exists(os.path.join(BASE_DIR, '.git')):
        return "Not a Git Repo"
    try:
        # Use git to get current branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            print(f"RecoveryMenu: Detected branch: {branch}")
            return branch
        else:
            return "Unknown Branch"
    except Exception as e:
        print(f"RecoveryMenu: Error getting branch: {e}")
        return "Error"

def restore_stable_branch():
    if not os.path.exists(os.path.join(BASE_DIR, '.git')):
        print("Error: Not a git repository.", file=sys.stderr)
        return False
    try:
        print("RecoveryMenu: Attempting to restore to 'bada' branch.")
        # Fetch latest
        subprocess.run(["git", "fetch", "--all"], cwd=BASE_DIR, check=True, capture_output=True, text=True)
        # Reset hard to origin/bada
        subprocess.run(["git", "reset", "--hard", "origin/bada"], cwd=BASE_DIR, check=True, capture_output=True, text=True)
        # Clean
        subprocess.run(["git", "clean", "-df"], cwd=BASE_DIR, check=True, capture_output=True, text=True)
        
        repair_requirements()
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during stable restore: {e.stderr}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Exception during stable restore: {e}", file=sys.stderr)
        return False

def switch_to_main_branch():
    if not os.path.exists(os.path.join(BASE_DIR, '.git')):
        print("Error: Not a git repository.", file=sys.stderr)
        return False
    try:
        # Fetch all branches
        result = subprocess.run(
            ["git", "fetch", "--all"],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            print(f"Error fetching branches: {result.stderr}", file=sys.stderr)
            return False

        # Checkout the main branch
        result = subprocess.run(
            ["git", "checkout", "main"],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            print(f"Error checking out main branch: {result.stderr}", file=sys.stderr)
            return False

        # Pull latest changes from origin/main
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            print(f"Error pulling from origin/main: {result.stderr}", file=sys.stderr)
            return False
            
        repair_requirements()
        return True
    except Exception as e:
        print(f"Exception during main branch switch: {e}", file=sys.stderr)
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
    if not os.path.exists(REQ_PATH):
        print(f"Error: requirements.txt not found at {REQ_PATH}", file=sys.stderr)
        return False
    try:
        print("RepairRequirements: Starting installation.")
        # Use CREATE_NO_WINDOW to hide the console window (Windows only)
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        
        command = [sys.executable, "-m", "pip", "install", "-r", REQ_PATH]
        result = subprocess.run(
            command,
            capture_output=True, text=True, timeout=300, # Increased timeout
            creationflags=creationflags
        )
        if result.returncode != 0:
            print(f"Error reinstalling requirements:", file=sys.stderr)
            print(f"STDOUT: {result.stdout}", file=sys.stderr)
            print(f"STDERR: {result.stderr}", file=sys.stderr)
            return False
        
        print("RepairRequirements: Pip install finished, verifying packages.")
        # Post-install verification
        missing = check_requirements()
        if missing:
            print(f"RepairRequirements: Verification failed, still missing: {', '.join(missing)}", file=sys.stderr)
            return False
            
        print("RepairRequirements: Requirements installed and verified successfully.", file=sys.stderr)
        return True
    except Exception as e:
        print(f"Exception during requirements installation: {e}", file=sys.stderr)
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

class RecoveryMenu:
    def __init__(self, window=None):
        print("RecoveryMenu: Initializing.")
        self.index = 0
        self.active = True
        self.window = window
        self.synth = NVDASynth()

        # Dynamically build menu items
        self.items = [
            ("Reinstall Stable Build", "restore_stable"),
            ("Reinstall Requirements", "reinstall_reqs"),
            ("Check Integrity", "check_integrity"),
            ("Recreate Tech-Soft", "recreate_techsoft"),
            ("Exit Recovery", "exit_recovery"),
        ]
        
        current_branch = get_current_git_branch()
        print(f"RecoveryMenu: Current branch is {current_branch}")
        if current_branch == "testing":
            # Insert "Switch to Main Branch" if currently on 'testing'
            self.items.insert(1, ("Switch to Main Branch", "switch_to_main")) # Insert after "Reinstall Stable Build"
            print("RecoveryMenu: Added 'Switch to Main Branch' option.")

    def _speak(self, text):
        if self.synth and self.synth.is_valid:
            self.synth.speak(text)

    def _update_display(self):
        if self.window:
            title = self.items[self.index][0]
            current_branch = get_current_git_branch()
            branch_info = f" (Branch: {current_branch}"
            if current_branch == "testing":
                branch_info += " - TESTING)"
            else:
                branch_info += ")"
            
            display_text = f"Tech-Note Recovery: {title}{branch_info}"
            self.window.update_text(display_text)
            self._speak(f"{title}. Current branch {current_branch}")
            print(f"RecoveryMenu: Displaying '{title}' (Index: {self.index})")

    def next(self):
        self.index = (self.index + 1) % len(self.items)
        print(f"RecoveryMenu: Navigated to next. New index: {self.index}")
        self._update_display()

    def previous(self):
        self.index = (self.index - 1) % len(self.items)
        print(f"RecoveryMenu: Navigated to previous. New index: {self.index}")
        self._update_display()

    def select(self):
        action = self.items[self.index][1]
        print(f"RecoveryMenu: Selected action: {action}")
        if action == "restore_stable":
            self._speak("Attempting to restore to stable version.")
            if restore_stable_branch():
                self._speak("Restore successful.")
            else:
                self._speak("Restore failed.")
        elif action == "switch_to_main":
            self._speak("Attempting to switch to main branch.")
            if switch_to_main_branch():
                self._speak("Switch to main successful.")
            else:
                self._speak("Switch to main failed.")
        elif action == "reinstall_reqs":
            self._speak("Attempting to reinstall requirements.")
            if repair_requirements():
                self._speak("Requirements reinstalled successfully.")
            else:
                self._speak("Failed to reinstall requirements.")
        elif action == "check_integrity":
            self._run_integrity_check()
        elif action == "recreate_techsoft":
            self._speak("Attempting to recreate Tech-Soft directories.")
            recreate_techsoft()
            self._speak("Tech-Soft directories recreated.")
        elif action == "exit_recovery":
            self.active = False
            self._speak("Exiting recovery menu.")
            print("RecoveryMenu: Exiting.")
            if self.window:
                self.window.close() # Ensure window is explicitly closed
        if self.active:
            self._update_display()
        elif self.window:
            self.window.update_text("Tech-Note Recovery")
            # Ensure window is closed if inactive
            self.window.close() 

    def _run_integrity_check(self):
        print("RecoveryMenu: Running integrity check.")
        issues = run_auto_checks()
        if self.window:
            if not issues:
                self.window.update_text("All checks passed.")
                self._speak("All checks passed.")
                print("RecoveryMenu: Integrity check passed.")
            else:
                issue_text = "Issues: " + "; ".join(d for _, d in issues)
                self.window.update_text(issue_text)
                self._speak(issue_text)
                print(f"RecoveryMenu: Integrity check found issues: {issue_text}")

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