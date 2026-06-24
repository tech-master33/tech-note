import os
from core.audio_player import AudioPlayer

# Standard sound path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOUNDS_DIR = os.path.join(BASE_DIR, 'sounds')

# Global position announcement toggle
ANNOUNCE_POSITION = True
SOUND_SCHEME = "Default"

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
    if SOUND_SCHEME == "Minimal":
        return
    path = _get_sound_path('Focus.wav')
    if os.path.exists(path):
        _audio_player.play_file(path)
    elif SOUND_SCHEME != "Default":
        fallback = _get_scheme_fallback('Focus.wav')
        if os.path.exists(fallback):
            _audio_player.play_file(fallback)

def play_click():
    if SOUND_SCHEME == "Minimal":
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
        self.speak(f"No apps starting with {char}")

    def search(self, query):
        if not hasattr(self, '_original_children') or self._original_children is None:
            self._original_children = self.current_node.children[:]
        q = query.lower()
        filtered = [item for item in self._original_children if q in item.title.lower()]
        self.current_node.children = filtered
        self.current_index = 0
        if filtered:
            self.announce_current()
            pos = self.current_index + 1
            self.speak(f"{pos} of {len(filtered)}.")
        else:
            self.speak(f"No matches for {query}.")

    def clear_search(self):
        if hasattr(self, '_original_children') and self._original_children is not None:
            self.current_node.children = self._original_children
            self._original_children = None

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

def build_braillenote_menu(synth, window, app_callback, on_reset_account=None, safe_mode=False):
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
    
    # Optional apps
    try:
        from apps.book_reader import BookReaderApp
    except ImportError:
        BookReaderApp = None
    try:
        from apps.voice_memo import VoiceMemoApp
    except ImportError:
        VoiceMemoApp = None
    try:
        from apps.calendar_app import CalendarApp
    except ImportError:
        CalendarApp = None

    root = MenuNode("Main Menu")
    
    root.add_child(MenuNode("Word Processor", lambda: app_callback(TechEdit), "w"))
    if BookReaderApp:
        root.add_child(MenuNode("Book Reader", lambda: app_callback(BookReaderApp), "b"))
    if VoiceMemoApp:
        root.add_child(MenuNode("Voice Memos", lambda: app_callback(VoiceMemoApp), "v"))
    root.add_child(MenuNode("Calculator", lambda: app_callback(TechCalc), "c"))
    if CalendarApp:
        root.add_child(MenuNode("Calendar", lambda: app_callback(CalendarApp), "d"))
    root.add_child(MenuNode("Planner", lambda: app_callback(PlannerApp), "p"))
    root.add_child(MenuNode("Address List", lambda: app_callback(AddressListApp), "a"))
    root.add_child(MenuNode("Notes", lambda: app_callback(NotesApp), "n"))
    root.add_child(MenuNode("Email", lambda: app_callback(EmailApp), "e"))
    root.add_child(MenuNode("Internet", lambda: app_callback(InternetApp), "i"))
    root.add_child(MenuNode("Chat", lambda: app_callback(ChatApp), "h"))
    media = root.add_child(MenuNode("Media Center", shortcut="m"))
    media.add_child(MenuNode("Media Player", lambda: app_callback(MediaPlayerApp)))
    media.add_child(MenuNode("FM Radio", lambda: app_callback(FMRadioApp)))
    root.add_child(MenuNode("File Manager", lambda: app_callback(TechFiles), "f"))
    root.add_child(MenuNode("Game Center", lambda: app_callback(GameCenter), "g"))
    root.add_child(MenuNode("App Store", lambda: app_callback(AppStore), "l"))
    root.add_child(MenuNode("Settings", lambda: app_callback(
        lambda m, w: SettingsApp(m, w, on_reset_account=on_reset_account)
    ), "s"))
    root.add_child(MenuNode("Tutorial", lambda: app_callback(TutorialApp), "t"))
    
    if not safe_mode:
        _add_installed_apps(root, app_callback)
    
    return root


def _add_installed_apps(root, app_callback):
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
