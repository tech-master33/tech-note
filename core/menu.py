import os
from core.audio_player import AudioPlayer

# Standard sound path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOUNDS_DIR = os.path.join(BASE_DIR, 'sounds')

# Global position announcement toggle
ANNOUNCE_POSITION = True
SOUND_SCHEME = "Default"
SOUND_SCHEMES = ["Default", "Minimal", "Classic", "Modern", "Soft", "Loud", "Natural", "None"]

# Braille display patterns for UI elements
BRAILLE_PATTERNS = {
    "menu": " Menu.",
    "submenu": " Submenu.",
    "item": ".",
    "checked": " (checked) ",
    "unchecked": " (unchecked) ",
    "selected": " (selected) ",
    "slider": " Slider.",
    "button": " Button.",
    "edit": " Edit.",
    "list": " List.",
    "tree": " Tree.",
    "progress": " Progress.",
    "link": " Link.",
    "heading": " Heading.",
    "heading_1": " Heading 1.",
    "heading_2": " Heading 2.",
    "heading_3": " Heading 3.",
}

_audio_player = AudioPlayer()

def _get_sound_path(name):
    scheme_dir = os.path.join(SOUNDS_DIR, SOUND_SCHEME.lower())
    path = os.path.join(scheme_dir, name)
    if os.path.exists(path):
        return path
    return os.path.join(SOUNDS_DIR, name)

def _get_scheme_fallback(name):
    default_dir = os.path.join(SOUNDS_DIR, 'default')
    return os.path.join(default_dir, name)

def play_move():
    if SOUND_SCHEME in ("Minimal", "None"):
        return
    path = _get_sound_path('Focus.wav')
    if os.path.exists(path):
        _audio_player.play_file(path)
    elif SOUND_SCHEME != "Default":
        fallback = _get_scheme_fallback('Focus.wav')
        if os.path.exists(fallback):
            _audio_player.play_file(fallback)

def play_click():
    if SOUND_SCHEME in ("Minimal", "None"):
        return
    path = _get_sound_path('clicked.ogg')
    if not os.path.exists(path):
        path = _get_sound_path('clicked.wav')
    if os.path.exists(path):
        _audio_player.play_file(path)
    elif SOUND_SCHEME != "Default":
        fallback = _get_scheme_fallback('clicked.ogg')
        if not os.path.exists(fallback):
            fallback = _get_scheme_fallback('clicked.wav')
        if os.path.exists(fallback):
            _audio_player.play_file(fallback)

class MenuNode:
    def __init__(self, title, action=None, shortcut=None):
        self.title = title
        self.action = action
        self.shortcut = shortcut
        self.children = []
        self.parent = None

    def add_child(self, child):
        child.parent = self
        self.children.append(child)
        return child

class MenuSystem:
    def __init__(self, root_node, speak_func, play_sound=None):
        self.root = root_node
        self.current_node = root_node
        self.current_index = 0
        self.speak = speak_func
        self.play_sound = play_sound

    def get_current_item(self):
        if not self.current_node.children:
            return None
        return self.current_node.children[self.current_index]

    def next(self):
        if not self.current_node.children:
            return
        self.current_index = (self.current_index + 1) % len(self.current_node.children)
        play_move()
        self.announce_current()

    def previous(self):
        if not self.current_node.children:
            return
        self.current_index = (self.current_index - 1) % len(self.current_node.children)
        play_move()
        self.announce_current()

    def select(self):
        item = self.get_current_item()
        if not item:
            return

        # Play sound if callback provided or default
        if self.play_sound:
            self.play_sound()
        else:
            play_click()

        if item.children:
            self.current_node = item
            self.current_index = 0
            self.announce_current()
        elif item.action:
            self.speak(f"Opening {item.title}")
            item.action()

    def back(self):
        if self.current_node.parent:
            parent = self.current_node.parent
            self.current_index = parent.children.index(self.current_node)
            self.current_node = parent
            play_move()
            self.announce_current()
        else:
            self.speak("Main Menu")

    def first_letter_nav(self, char):
        char = char.lower()
        if not self.current_node.children:
            return
        for i in range(1, len(self.current_node.children) + 1):
            idx = (self.current_index + i) % len(self.current_node.children)
            item = self.current_node.children[idx]
            if item.title.lower().startswith(char):
                self.current_index = idx
                play_move()
                self.announce_current()
                return

    def announce_current(self):
        item = self.get_current_item()
        if item:
            if ANNOUNCE_POSITION:
                total = len(self.current_node.children)
                pos = self.current_index + 1
                self.speak(f"{item.title}. {pos} of {total}.")
            else:
                self.speak(item.title)
        else:
            self.speak(self.current_node.title)

def build_braillenote_menu(synth, window, app_callback, on_reset_account=None):
    from apps.tech_edit import TechEdit
    from apps.tech_calc import TechCalc
    from apps.tech_files import TechFiles
    from apps.settings_app import SettingsApp
    from apps.planner import PlannerApp
    from apps.address_list import AddressListApp
    from apps.email_app import EmailApp
    from apps.internet_app import InternetApp
    from apps.media_player import MediaPlayerApp
    from apps.fm_radio import FMRadioApp
    from apps.chat_app import ChatApp
    from apps.tutorial_app import TutorialApp
    from apps.game_center import GameCenter
    from apps.app_store import AppStore
    from apps.notes_app import NotesApp
    
    # Phase 5 apps
    from apps.rss_reader import RSSReader

    # Phase 6 apps
    try:
        from apps.expense_tracker import ExpenseTrackerApp
    except ImportError:
        ExpenseTrackerApp = None
    try:
        from apps.password_manager import PasswordManagerApp
    except ImportError:
        PasswordManagerApp = None
    try:
        from apps.sleep_timer import SleepTimerApp
    except ImportError:
        SleepTimerApp = None
    try:
        from apps.ambient_sound import AmbientSoundApp
    except ImportError:
        AmbientSoundApp = None
    try:
        from apps.pomodoro_timer import PomodoroTimerApp
    except ImportError:
        PomodoroTimerApp = None
    try:
        from apps.network_diag import NetworkDiagApp
    except ImportError:
        NetworkDiagApp = None
    try:
        from apps.app_usage_stats import AppUsageStatsApp
    except ImportError:
        AppUsageStatsApp = None
    try:
        from apps.auto_backup import AutoBackupApp
    except ImportError:
        AutoBackupApp = None
    try:
        from apps.bulk_file_ops import BulkFileOpsApp
    except ImportError:
        BulkFileOpsApp = None
    try:
        from apps.disk_cleanup import DiskCleanupApp
    except ImportError:
        DiskCleanupApp = None

    root = MenuNode("Main Menu")
    
    root.add_child(MenuNode("Word Processor", lambda: app_callback(TechEdit), "w"))
    root.add_child(MenuNode("Calculator", lambda: app_callback(TechCalc), "c"))
    root.add_child(MenuNode("Planner", lambda: app_callback(PlannerApp), "p"))
    root.add_child(MenuNode("Address List", lambda: app_callback(AddressListApp), "a"))
    root.add_child(MenuNode("Notes", lambda: app_callback(NotesApp), "n"))
    root.add_child(MenuNode("Email", lambda: app_callback(EmailApp), "e"))
    root.add_child(MenuNode("Internet", lambda: app_callback(InternetApp), "i"))
    root.add_child(MenuNode("RSS Reader", lambda: app_callback(RSSReader), "r"))
    root.add_child(MenuNode("Chat", lambda: app_callback(ChatApp), "h"))
    media = root.add_child(MenuNode("Media Center", shortcut="m"))
    media.add_child(MenuNode("Media Player", lambda: app_callback(MediaPlayerApp)))
    media.add_child(MenuNode("FM Radio", lambda: app_callback(FMRadioApp)))
    tools = root.add_child(MenuNode("Tools", shortcut="o"))
    if ExpenseTrackerApp:
        tools.add_child(MenuNode("Expense Tracker", lambda: app_callback(ExpenseTrackerApp)))
    if PasswordManagerApp:
        tools.add_child(MenuNode("Password Manager", lambda: app_callback(PasswordManagerApp)))
    if SleepTimerApp:
        tools.add_child(MenuNode("Sleep Timer", lambda: app_callback(SleepTimerApp)))
    if AmbientSoundApp:
        tools.add_child(MenuNode("Ambient Sound", lambda: app_callback(AmbientSoundApp)))
    if PomodoroTimerApp:
        tools.add_child(MenuNode("Pomodoro Timer", lambda: app_callback(PomodoroTimerApp)))
    if NetworkDiagApp:
        tools.add_child(MenuNode("Network Diag", lambda: app_callback(NetworkDiagApp)))
    if AppUsageStatsApp:
        tools.add_child(MenuNode("App Usage Stats", lambda: app_callback(AppUsageStatsApp)))
    if AutoBackupApp:
        tools.add_child(MenuNode("Auto Backup", lambda: app_callback(AutoBackupApp)))
    if BulkFileOpsApp:
        tools.add_child(MenuNode("Bulk File Ops", lambda: app_callback(BulkFileOpsApp)))
    if DiskCleanupApp:
        tools.add_child(MenuNode("Disk Cleanup", lambda: app_callback(DiskCleanupApp)))
    root.add_child(MenuNode("File Manager", lambda: app_callback(TechFiles), "f"))
    root.add_child(MenuNode("Game Center", lambda: app_callback(GameCenter), "g"))
    root.add_child(MenuNode("App Store", lambda: app_callback(AppStore), "l"))
    root.add_child(MenuNode("Settings", lambda: app_callback(
        lambda m, w: SettingsApp(m, w, on_reset_account=on_reset_account)
    ), "s"))
    root.add_child(MenuNode("Tutorial", lambda: app_callback(TutorialApp), "t"))
    
    _add_installed_apps(root, app_callback)
    
    return root


def _add_installed_apps(root, app_callback):
    import os
    import json
    import importlib
    import sys
    from core.config import TECH_SOFT
    INSTALLED_FILE = os.path.join(TECH_SOFT, "installed_apps.json")
    APPS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "apps")
    
    if not os.path.exists(INSTALLED_FILE):
        return
    
    try:
        with open(INSTALLED_FILE, 'r') as f:
            installed = json.load(f)
    except:
        return
    
    if not installed:
        return
    
    for app_id, info in installed.items():
        filename = info.get("filename", "")
        entry_point = info.get("entry_point", "")
        name = info.get("name", app_id)
        category = info.get("category", "Apps").lower()
        filepath = os.path.join(APPS_DIR, filename)
        
        if not os.path.exists(filepath):
            continue
        
        if not filename.endswith('.py'):
            continue
        
        mod_name = filename[:-3]
        
        def make_loader(mn=mod_name, ep=entry_point):
            def load():
                try:
                    if mn not in sys.modules:
                        if APPS_DIR not in sys.path:
                            sys.path.insert(0, APPS_DIR)
                        mod = importlib.import_module(mn)
                    else:
                        mod = sys.modules[mn]
                    
                    if ep and hasattr(mod, ep):
                        cls = getattr(mod, ep)
                    else:
                        classes = [v for v in vars(mod).values()
                                   if isinstance(v, type) and hasattr(v, 'on_key') and hasattr(v, 'exit_app')]
                        cls = classes[0] if classes else None
                    
                    if cls:
                        app_callback(cls)
                except Exception as e:
                    print(f"Failed to load installed app {mn}: {e}")
            return load
        
        if category != "games":
            root.add_child(MenuNode(name, make_loader()))
