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
    def __init__(self, root_node, speak_func):
        self.root = root_node
        self.current_node = root_node
        self.current_index = 0
        self.speak = speak_func

    def get_current_item(self):
        if not self.current_node.children:
            return None
        return self.current_node.children[self.current_index]

    def next(self):
        if not self.current_node.children:
            return
        self.current_index = (self.current_index + 1) % len(self.current_node.children)
        self.announce_current()

    def previous(self):
        if not self.current_node.children:
            return
        self.current_index = (self.current_index - 1) % len(self.current_node.children)
        self.announce_current()

    def select(self):
        item = self.get_current_item()
        if not item:
            return

        if item.children:
            self.current_node = item
            self.current_index = 0
            self.announce_current()
        elif item.action:
            self.speak(f"Opening {item.title}")
            item.action()

    def back(self):
        if self.current_node.parent:
            # Find index of current_node in parent
            parent = self.current_node.parent
            self.current_index = parent.children.index(self.current_node)
            self.current_node = parent
            self.announce_current()
        else:
            self.speak("Main Menu")

    def first_letter_nav(self, char):
        char = char.lower()
        if not self.current_node.children:
            return
            
        # Start searching from next item
        for i in range(1, len(self.current_node.children) + 1):
            idx = (self.current_index + i) % len(self.current_node.children)
            item = self.current_node.children[idx]
            if item.title.lower().startswith(char):
                self.current_index = idx
                self.announce_current()
                return

    def announce_current(self):
        item = self.get_current_item()
        if item:
            self.speak(item.title)
        else:
            self.speak(self.current_node.title)

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


def build_braillenote_menu(synth, window, app_callback, on_reset_account=None):
    root = MenuNode("Main Menu")
    
    # Word Processor
    root.add_child(MenuNode("Word Processor", lambda: app_callback(TechEdit), "w"))
    
    # Settings App
    root.add_child(MenuNode("Settings App", lambda: app_callback(
        lambda m, w: SettingsApp(m, w, on_reset_account=on_reset_account)
    ), "s"))
    
    # Planner
    root.add_child(MenuNode("Planner", lambda: app_callback(PlannerApp), "p"))
    
    # Address List
    root.add_child(MenuNode("Address List", lambda: app_callback(AddressListApp), "a"))
    
    # Email
    root.add_child(MenuNode("Email", lambda: app_callback(EmailApp), "e"))
    
    # Internet
    root.add_child(MenuNode("Internet", lambda: app_callback(InternetApp), "i"))
    
    # Media Center
    media = root.add_child(MenuNode("Media Center", shortcut="m"))
    media.add_child(MenuNode("Media Player", lambda: app_callback(MediaPlayerApp)))
    media.add_child(MenuNode("FM Radio", lambda: app_callback(FMRadioApp)))
    
    # Calculator
    root.add_child(MenuNode("Scientific Calculator", lambda: app_callback(TechCalc), "c"))
    
    # File Manager
    root.add_child(MenuNode("File Manager", lambda: app_callback(TechFiles), "f"))
    
    return root
