import os
import json
import random
import string
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode
from core.config import TECH_SOFT

DATA_FILE = os.path.join(TECH_SOFT, "passwords.json")


def generate_password(length=16):
    chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
    return ''.join(random.choice(chars) for _ in range(length))


class PasswordManager(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.entries = self._load_data()
        self._input_mode = None
        self._input_text = ""
        self._new_entry = {}
        self._viewing_password = False
        self._build_menu()

    def _load_data(self):
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r') as f:
                    return json.load(f)
        except:
            pass
        return []

    def _save_data(self):
        try:
            os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
            with open(DATA_FILE, 'w') as f:
                json.dump(self.entries, f, indent=2)
        except:
            pass

    def _build_menu(self):
        root = MenuNode("Password Manager")
        root.add_child(MenuNode("Add Entry", self._start_add))
        root.add_child(MenuNode("Generate Password", self._generate_show))
        for i, e in enumerate(self.entries):
            label = f"{e.get('service', 'Unknown')}: {e.get('username', '')}"
            root.add_child(MenuNode(label, lambda idx=i: self._show_entry(idx)))
        if not self.entries:
            root.add_child(MenuNode("No entries"))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _show_entry(self, idx):
        if idx >= len(self.entries):
            return
        e = self.entries[idx]
        root = MenuNode(e.get("service", "Entry"))
        root.add_child(MenuNode(f"Service: {e.get('service', '')}"))
        root.add_child(MenuNode(f"Username: {e.get('username', '')}"))
        pw = e.get("password", "")
        root.add_child(MenuNode(f"Password: {pw[:3]}... ({len(pw)} chars)", lambda: self._reveal_password(idx)))
        root.add_child(MenuNode("Copy to Clipboard", lambda: self._copy_password(idx)))
        root.add_child(MenuNode("Delete", lambda: self._delete_entry(idx)))
        root.add_child(MenuNode("Back", self._build_menu_back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _reveal_password(self, idx):
        if idx < len(self.entries):
            pw = self.entries[idx].get("password", "")
            self.speak(f"Password: {pw}")
            self._viewing_password = True

    def _copy_password(self, idx):
        if idx < len(self.entries):
            pw = self.entries[idx].get("password", "")
            try:
                import win32clipboard
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(pw)
                win32clipboard.CloseClipboard()
                self.speak("Password copied to clipboard.")
            except:
                self.speak("Clipboard copy failed.")

    def _delete_entry(self, idx):
        if idx < len(self.entries):
            name = self.entries[idx].get("service", "Entry")
            self.entries.pop(idx)
            self._save_data()
            self.speak(f"{name} deleted.")
            self._build_menu()
            self.menu.announce_current()

    def _start_add(self):
        self._input_mode = "service"
        self._input_text = ""
        self._new_entry = {}
        self.speak("Enter service name.")
        self.window.update_text("Service: ")

    def _generate_show(self):
        pw = generate_password()
        self.speak(f"Generated: {pw}")
        self.window.update_text(f"Generated: {pw}")

    def _build_menu_back(self):
        self._build_menu()
        self.menu.announce_current()

    def on_focus(self):
        self._build_menu()
        item = self.menu.get_current_item()
        self.speak("Password Manager. " + (item.title if item else ""))

    def on_key(self, vk):
        if self._input_mode:
            if vk == win32con.VK_ESCAPE:
                self._input_mode = None
                self._build_menu()
                self.menu.announce_current()
                return
            if vk == win32con.VK_RETURN:
                if self._input_mode == "service":
                    self._new_entry["service"] = self._input_text.strip()
                    self._input_mode = "username"
                    self._input_text = ""
                    self.speak("Enter username.")
                    self.window.update_text("Username: ")
                elif self._input_mode == "username":
                    self._new_entry["username"] = self._input_text.strip()
                    self._input_mode = "password"
                    self._input_text = ""
                    self.speak("Enter password, or press Enter to generate.")
                    self.window.update_text("Password (Enter=generate): ")
                elif self._input_mode == "password":
                    pw = self._input_text.strip()
                    if not pw:
                        pw = generate_password()
                    self._new_entry["password"] = pw
                    self.entries.append(self._new_entry)
                    self._save_data()
                    self.speak(f"Entry added for {self._new_entry.get('service', '')}.")
                    self._input_mode = None
                    self._build_menu()
                    self.menu.announce_current()
                return
            if vk == win32con.VK_BACK:
                self._input_text = self._input_text[:-1]
                self.window.update_text(f"{self._input_mode}: {self._input_text}")
                return
            ch = self._vk_to_char(vk)
            if ch:
                self._input_text += ch
                self.window.update_text(f"{self._input_mode}: {self._input_text}")
            return
        if vk == win32con.VK_ESCAPE:
            if self._viewing_password:
                self._viewing_password = False
                self._build_menu()
                self.menu.announce_current()
                return
            self.exit_app()
            return
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        else:
            self._handle_first_letter_nav(vk, self.menu)
        item = self.menu.get_current_item()
        if item:
            self.window.update_text(item.title)

    def on_key_up(self, vk):
        if self._input_mode:
            return
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text(item.title)

    def get_help_text(self):
        return "Password Manager. Store and generate passwords. Space next, Backspace previous. Enter select. Escape exit."
