import os
import json
import win32con
from core.app_base import SoftApp
from core.config import TECH_SOFT
from core.menu import MenuNode, MenuSystem

class AddressListApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.data_file = os.path.join(TECH_SOFT, 'contacts', 'contacts.json')
        self.contacts = {}
        self.menu = None
        self.load_contacts()

    def load_contacts(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    self.contacts = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.contacts = {}
        else:
            self.contacts = {"John Doe": "555-0101", "Jane Smith": "555-0102"}
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            self.save_contacts()

    def save_contacts(self):
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, 'w') as f:
            json.dump(self.contacts, f)

    def _build_menu(self):
        root = MenuNode("Address List")
        keys = sorted(self.contacts.keys())
        for name in keys:
            phone = self.contacts[name]
            root.add_child(MenuNode(name, lambda n=name, p=phone: self.speak(f"{n}, {p}")))
        
        if not keys:
            root.add_child(MenuNode("No contacts"))
            
        self.menu = MenuSystem(root, self.speak)

    def on_focus(self):
        self._build_menu()
        self.speak("Address List. " + self.menu.get_current_item().title)
        self.window.update_text("Contacts: " + self.menu.get_current_item().title)

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        if vk in (win32con.VK_SPACE, win32con.VK_DOWN):
            self.menu.next()
        elif vk in (win32con.VK_BACK, win32con.VK_UP):
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))

        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Contacts: " + item.title)
