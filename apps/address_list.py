import os
import json
import win32con
from core.app_base import SoftApp
from core.config import TECH_SOFT

class AddressListApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.data_file = os.path.join(TECH_SOFT, 'contacts', 'contacts.json')
        self.contacts = {}
        self.load_contacts()
        self.keys = list(self.contacts.keys())
        self.index = 0

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

    def on_focus(self):
        self.keys = list(self.contacts.keys())
        if self.index >= len(self.keys):
            self.index = 0
        self.speak("Address List. " + (self.keys[self.index] if self.keys else "No contacts"))
        self.window.update_text("Contacts: " + (self.keys[self.index] if self.keys else "Empty"))

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        
        if not self.keys:
            self.speak("No contacts")
            return

        if vk == win32con.VK_SPACE or vk == win32con.VK_DOWN:
            self.index = (self.index + 1) % len(self.keys)
            self.announce()
        elif vk == win32con.VK_BACK or vk == win32con.VK_UP:
            self.index = (self.index - 1) % len(self.keys)
            self.announce()
        elif vk == win32con.VK_RETURN:
            name = self.keys[self.index]
            self.speak(f"{name}, {self.contacts[name]}")

    def announce(self):
        name = self.keys[self.index]
        self.speak(name)
        self.window.update_text(name)
