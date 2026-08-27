import os
from core.config import TECH_SOFT
from core.systmanau import get_audio_manager

# Standard sound path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOUNDS_DIR = os.path.join(BASE_DIR, 'sounds')

# Global position announcement toggle
ANNOUNCE_POSITION = True
SOUND_SCHEME = "Default"

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
        get_audio_manager().play("ui", path)
    elif SOUND_SCHEME != "Default":
        fallback = _get_scheme_fallback('Focus.wav')
        if os.path.exists(fallback):
            get_audio_manager().play("ui", fallback)

def play_click():
    if SOUND_SCHEME == "Minimal":
        return
    path = _get_sound_path('clicked.ogg')
    if not os.path.exists(path):
        path = _get_sound_path('clicked.wav')
    if os.path.exists(path):
        get_audio_manager().play("ui", path)
    elif SOUND_SCHEME != "Default":
        fallback = _get_scheme_fallback('clicked.ogg')
        if not os.path.exists(fallback):
            fallback = _get_scheme_fallback('clicked.wav')
        if os.path.exists(fallback):
            get_audio_manager().play("ui", fallback)

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
    def __init__(self, root_node, speak_func, play_sound=None, stop_func=None):
        self.root = root_node
        self.current_node = root_node
        self.current_index = 0
        self.speak = speak_func
        self.play_sound = play_sound
        self._stop = stop_func

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
            item.action()

    def back(self):
        if self.current_node.parent:
            parent = self.current_node.parent
            if hasattr(self.current_node, '_return_index'):
                self.current_index = self.current_node._return_index
            else:
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

    def _speak_stopping(self, text):
        """Speak *text*, stopping any in-progress utterance first.

        Calls stop() explicitly so the engine is guaranteed idle before
        speak() begins — the SAPI engine's _engine_stop is synchronous
        (Speak with flag 0), so this eliminates the race where two
        overlapping async Speak calls stack on some engines.
        """
        if self._stop:
            self._stop()
        self.speak(text)

    def announce_current(self):
        item = self.get_current_item()
        if item:
            if ANNOUNCE_POSITION:
                total = len(self.current_node.children)
                pos = self.current_index + 1
                self._speak_stopping(f"{item.title}. {pos} of {total}.")
            else:
                self._speak_stopping(item.title)
        else:
            self._speak_stopping(self.current_node.title)

DEFAULT_MAIN_MENU = [
    {"id": "word_processor", "label": "Word Processor", "shortcut": "w"},
    {"id": "calculator", "label": "Calculator", "shortcut": "c"},
    {"id": "planner", "label": "Planner", "shortcut": "p"},
    {"id": "address_list", "label": "Address List", "shortcut": "a"},
    {"id": "notes", "label": "Notes", "shortcut": "n"},
    {"id": "email", "label": "Email", "shortcut": "e"},
    {"id": "internet", "label": "Internet", "shortcut": "i"},
    {"id": "chat", "label": "Chat", "shortcut": "h"},
    {"id": "terminal", "label": "Terminal", "shortcut": "t"},
    {"id": "media_center", "label": "Media Center", "shortcut": "m", "children": [
        {"id": "media_player", "label": "Media Player"},
        {"id": "fm_radio", "label": "FM Radio"},
    ]},
    {"id": "file_manager", "label": "File Manager", "shortcut": "f"},
    {"id": "game_center", "label": "Game Center", "shortcut": "g"},
    {"id": "app_store", "label": "App Store", "shortcut": "l"},
    {"id": "settings", "label": "Settings", "shortcut": "s"},
]

APP_CLASS_MAP = {}

def _ensure_app_class(app_id):
    if app_id in APP_CLASS_MAP:
        return APP_CLASS_MAP[app_id]
    _APP_IMPORTS = {
        "word_processor": ("apps.tech_edit", "TechEdit"),
        "calculator": ("apps.tech_calc", "TechCalc"),
        "file_manager": ("apps.tech_files", "TechFiles"),
        "settings": ("apps.settings_app", "SettingsApp"),
        "planner": ("apps.planner", "PlannerApp"),
        "address_list": ("apps.address_list", "AddressListApp"),
        "email": ("apps.email_app", "EmailApp"),
        "internet": ("apps.internet_app", "InternetApp"),
        "media_player": ("apps.media_player", "MediaPlayerApp"),
        "fm_radio": ("apps.fm_radio", "FMRadioApp"),
        "chat": ("apps.chat_app", "ChatApp"),
        "terminal": ("apps.terminal_app", "TerminalApp"),
        "game_center": ("apps.game_center", "GameCenter"),
        "app_store": ("apps.app_store", "AppStore"),
        "notes": ("apps.notes_app", "NotesApp"),
        "plugin_manager": ("apps.plugin_manager_app", "PluginManagerApp"),
    }
    import importlib
    path, cls_name = _APP_IMPORTS.get(app_id, (None, None))
    if not path:
        return None
    try:
        mod = importlib.import_module(path)
        cls = getattr(mod, cls_name)
        APP_CLASS_MAP[app_id] = cls
        return cls
    except Exception:
        return None


def _load_main_menu_layout():
    import json as _json
    path = os.path.join(TECH_SOFT, "settings.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                s = _json.load(f)
            layout = s.get("main_menu")
            if isinstance(layout, list) and layout:
                return layout
        except Exception:
            pass
    return None


def _save_main_menu_layout(layout):
    import json as _json
    path = os.path.join(TECH_SOFT, "settings.json")
    s = {}
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                s = _json.load(f)
        except Exception:
            pass
    s["main_menu"] = layout
    with open(path, "w") as f:
        _json.dump(s, f)


def build_braillenote_menu(synth, window, app_callback, on_reset_account=None, safe_mode=False):
    def _add_entry(root, entry, hidden_ids, on_reset):
        app_id = entry.get("id")
        visible = entry.get("visible", True)
        children = entry.get("children")
        if children is not None:
            if visible and not hidden_ids.get(app_id):
                folder = MenuNode(entry.get("label", app_id),
                                 shortcut=entry.get("shortcut"))
                for child_entry in children:
                    cid = child_entry.get("id")
                    if child_entry.get("visible", True) and not hidden_ids.get(cid):
                        cls = _ensure_app_class(cid)
                        if cls:
                            lbl = child_entry.get("label", cid)
                            folder.add_child(MenuNode(
                                lbl, lambda c=cls: app_callback(c)))
                if folder.children:
                    root.add_child(folder)
        else:
            if visible and not hidden_ids.get(app_id):
                cls = _ensure_app_class(app_id)
                if cls:
                    label = entry.get("label", app_id)
                    shortcut = entry.get("shortcut")
                    def _make_cb(c, reset):
                        if app_id == "settings":
                            return lambda: app_callback(
                                lambda m, w: c(m, w, on_reset_account=reset))
                        return lambda: app_callback(c)
                    root.add_child(MenuNode(label, _make_cb(cls, on_reset), shortcut))

    root = MenuNode("Main Menu")
    try:
        layout = _load_main_menu_layout()
    except Exception as e:
        import core.error_handler
        core.error_handler.log(e, "Loading main menu layout")
        layout = None
    listed_ids = set()
    hidden_ids = {}

    if layout:
        for item in layout:
            listed_ids.add(item.get("id"))
            if item.get("hidden"):
                hidden_ids[item["id"]] = True
            for c in item.get("children", []):
                cid = c.get("id")
                if cid:
                    listed_ids.add(cid)
                    if c.get("hidden"):
                        hidden_ids[cid] = True
        for entry in layout:
            _add_entry(root, entry, hidden_ids, on_reset_account)
    else:
        for entry in DEFAULT_MAIN_MENU:
            # Must track these as listed too, or the "unlisted defaults"
            # pass below re-adds every built-in a second time.
            listed_ids.add(entry["id"])
            _add_entry(root, entry, hidden_ids, on_reset_account)

    if not safe_mode:
        try:
            import importlib
            import json as _json
            for entry in DEFAULT_MAIN_MENU:
                eid = entry["id"]
                if eid not in listed_ids:
                    _add_entry(root, entry, {}, on_reset_account)
                    listed_ids.add(eid)
            _add_installed_apps(root, app_callback)
        except Exception:
            pass

    return root


def _add_installed_apps(root, app_callback):
    import json
    import importlib
    import sys
    from core.config import TECH_SOFT
    INSTALLED_FILE = os.path.join(TECH_SOFT, "installed_apps.json")
    APPS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "apps")
    
    if not os.path.exists(INSTALLED_FILE):
        _scan_apps_folder(root, app_callback, APPS_DIR)
        return
    
    try:
        with open(INSTALLED_FILE, 'r') as f:
            installed = json.load(f)
    except:
        _scan_apps_folder(root, app_callback, APPS_DIR)
        return
    
    if not installed:
        _scan_apps_folder(root, app_callback, APPS_DIR)
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
    
    _scan_apps_folder(root, app_callback, APPS_DIR)


def _scan_apps_folder(root, app_callback, apps_dir):
    import json
    import importlib
    import sys
    
    if not os.path.isdir(apps_dir):
        return
    
    for entry in os.listdir(apps_dir):
        entry_path = os.path.join(apps_dir, entry)
        
        if not os.path.isdir(entry_path):
            continue
        
        manifest_path = os.path.join(entry_path, "manifest.json")
        if not os.path.exists(manifest_path):
            continue
        
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
        except Exception:
            continue
        
        name = manifest.get("name", entry)
        entry_point = manifest.get("entry_point", "")
        
        if not entry_point:
            continue
        
        mod_name = entry_point.replace('.py', '')
        
        def make_folder_loader(mn=mod_name, ep=entry_point, app_dir=entry_path):
            def load():
                try:
                    if app_dir not in sys.path:
                        sys.path.insert(0, app_dir)
                    if mn not in sys.modules:
                        mod = importlib.import_module(mn)
                    else:
                        mod = sys.modules[mn]
                    
                    cls = getattr(mod, ep, None) if ep else None
                    if not cls:
                        classes = [v for v in vars(mod).values()
                                   if isinstance(v, type) and hasattr(v, 'on_key') and hasattr(v, 'exit_app')]
                        cls = classes[0] if classes else None
                    
                    if cls:
                        app_callback(cls)
                except Exception as e:
                    print(f"Failed to load folder app {mn}: {e}")
            return load
        
        root.add_child(MenuNode(name, make_folder_loader()))
