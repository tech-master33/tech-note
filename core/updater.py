import os
import sys
import subprocess
import threading
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_version():
    try:
        from core.version import VERSION
        return VERSION
    except ImportError:
        return "unknown"


def _git_run(args, timeout=30):
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        result = subprocess.run(
            ["git"] + args,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            startupinfo=si
        )
        return result
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _git_local_hash():
    result = _git_run(["rev-parse", "HEAD"], timeout=10)
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None


def _git_remote_hash(branch="main"):
    result = _git_run(["rev-parse", f"origin/{branch}"], timeout=10)
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None


def _git_fetch():
    result = _git_run(["fetch", "origin"], timeout=15)
    return result is not None and result.returncode == 0


def _git_pull(branch="main"):
    result = _git_run(["pull", "origin", branch], timeout=60)
    if result and result.returncode != 0:
        _git_run(["branch", "--set-upstream-to", f"origin/{branch}", branch], timeout=30)
        result = _git_run(["pull", "origin", branch], timeout=60)
    return result


def _install_requirements():
    req_path = os.path.join(BASE_DIR, 'requirements.txt')
    if not os.path.exists(req_path):
        return
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req_path],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=120
        )
    except Exception:
        pass


def _restart():
    try:
        subprocess.Popen(
            [sys.executable] + sys.argv,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception:
        subprocess.Popen([sys.executable] + sys.argv)
    os._exit(0)


def check_on_startup(synth=None, window=None):
    try:
        from core.config import SETTINGS_PATH
        import json
        settings = {}
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, 'r') as f:
                settings = json.load(f)

        if not settings.get("auto_update_on_startup", False):
            return

        branch = "main" if settings.get("update_channel") == "stable" else "testing"

        if not _git_fetch():
            return

        local = _git_local_hash()
        remote = _git_remote_hash(branch)

        if not local or not remote:
            return

        if local == remote:
            return

        if synth:
            synth.speak("Update found. Downloading...")
        if window:
            window.update_text("Updating Tech-Note...")

        result = _git_pull(branch)
        if result and result.returncode == 0 and "Already up to date" not in result.stdout:
            _install_requirements()
            _restart()

    except Exception:
        pass


def check_now(synth=None, window=None):
    if synth:
        synth.speak("Checking for updates. Please wait.")
    if window:
        window.update_text("Checking for updates...")

    try:
        from core.config import SETTINGS_PATH
        import json
        settings = {}
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, 'r') as f:
                settings = json.load(f)

        branch = "main" if settings.get("update_channel") == "stable" else "testing"

        if not _git_fetch():
            if synth:
                synth.speak("Could not connect to update server.")
            return False

        local = _git_local_hash()
        remote = _git_remote_hash(branch)

        if not local or not remote:
            if synth:
                synth.speak("Could not check for updates.")
            return False

        if local == remote:
            if synth:
                synth.speak("Already up to date.")
            return False

        result = _git_pull(branch)
        if result and result.returncode == 0:
            out = result.stdout.strip()
            if "Already up to date" in out:
                if synth:
                    synth.speak("Already up to date.")
                return False
            _install_requirements()
            if synth:
                synth.speak("Update downloaded. Restarting.")
            _restart()
            return True
        else:
            if synth:
                synth.speak("Update failed. Check your internet.")
            return False

    except FileNotFoundError:
        if synth:
            synth.speak("Git not found. Cannot update.")
        return False
    except subprocess.TimeoutExpired:
        if synth:
            synth.speak("Update timed out.")
        return False
    except Exception:
        if synth:
            synth.speak("Update error.")
        return False
