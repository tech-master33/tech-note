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
        self.input_mode = None
        self.input_buf = ""
        self.editing_name = None
        self.load_contacts()

    def load_contacts(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    self.contacts = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.contacts = {}
        else:
            self.contacts = {}
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            self.save_contacts()

    def save_contacts(self):
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, 'w') as f:
            json.dump(self.contacts, f, indent=2)

    def _build_menu(self):
        root = MenuNode("Address List")
        root.add_child(MenuNode("Add Contact", self._start_add, "n"))
        keys = sorted(self.contacts.keys())
        for name in keys:
            phone = self.contacts[name]
            root.add_child(MenuNode(f"{name}: {phone}", lambda n=name, p=phone: self.speak(f"{n}, phone {p}")))
        
        if not keys:
            root.add_child(MenuNode("No contacts"))
            
        self.menu = MenuSystem(root, self.speak)

    def _start_add(self):
        self.input_mode = "name"
        self.input_buf = ""
        self.speak("Enter contact name.")
        self.window.update_text("Name: ")

    def on_focus(self):
        self._build_menu()
        item = self.menu.get_current_item()
        self.speak("Address List. " + item.title)
        self.window.update_text("Contacts: " + item.title)

    def on_key(self, vk):
        if self.input_mode:
            self._handle_input(vk)
            return

        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        if vk in (win32con.VK_BACK):
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif vk == win32con.VK_DELETE:
            self._delete_contact()
        elif vk == win32con.VK_F2:
            self._start_edit()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))

        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Contacts: " + item.title)

    def _handle_input(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.input_mode = None
            self.speak("Cancelled.")
            self.on_focus()
            return

        if vk == win32con.VK_RETURN:
            val = self.input_buf.strip()
            if not val:
                self.speak("Cannot be empty.")
                return
            if self.input_mode == "name":
                self.editing_name = val
                self.input_mode = "phone"
                self.input_buf = ""
                self.speak("Enter phone number.")
                self.window.update_text("Phone: ")
            elif self.input_mode == "phone":
                self.contacts[self.editing_name] = val
                self.save_contacts()
                self.input_mode = None
                self.speak(f"Added {self.editing_name}.")
                self.on_focus()
            elif self.input_mode == "edit_name":
                old_name = self.editing_name
                old_phone = self.contacts.pop(old_name)
                self.editing_name = val
                self.input_mode = "edit_phone"
                self.input_buf = old_phone
                self.speak(f"Enter new phone for {val}. Current: {old_phone}")
                self.window.update_text(f"Phone: {old_phone}")
            elif self.input_mode == "edit_phone":
                self.contacts[self.editing_name] = val
                self.save_contacts()
                self.input_mode = None
                self.speak(f"Updated {self.editing_name}.")
                self.on_focus()
            return

        if vk == win32con.VK_BACK:
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                if self.input_mode in ("name", "edit_name"):
                    self.window.update_text(f"Name: {self.input_buf}")
                else:
                    self.window.update_text(f"Phone: {self.input_buf}")
            return

        ch = self._vk_to_char(vk)
        if ch:
            self.input_buf += ch
            if "name" in self.input_mode:
                self.window.update_text(f"Name: {self.input_buf}")
            else:
                self.window.update_text(f"Phone: {self.input_buf}")

    def _delete_contact(self):
        item = self.menu.get_current_item()
        if not item or item.title in ("No contacts", "Add Contact"):
            return
        name = item.title.rsplit(":", 1)[0].strip()
        if name in self.contacts:
            del self.contacts[name]
            self._build_menu()
            if self.menu.get_current_item():
                self.window.update_text("Contacts: " + self.menu.get_current_item().title)
            else:
                self.window.update_text("Contacts: Empty")

    def _start_edit(self):
        item = self.menu.get_current_item()
        if not item or item.title in ("No contacts", "Add Contact"):
            return
        name = item.title.split(":")[0].strip()
        if name in self.contacts:
            self.editing_name = name
            self.input_mode = "edit_name"
            self.input_buf = name
            self.speak(f"Editing {name}. Enter new name.")
            self.window.update_text(f"Name: {name}")

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text("Contacts: " + item.title)

    def get_help_text(self):
        return "Address List. Space for next, Backspace for previous. Enter to select. Delete to remove. F2 to edit. Escape to exit."
