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
        self.groups_file = os.path.join(TECH_SOFT, 'contacts', 'groups.json')
        self.contacts = {}
        self.groups = {}
        self.menu = None
        self.input_mode = None
        self.input_buf = ""
        self.editing_name = None
        self._search_results = []
        self._search_index = 0
        self.load_contacts()

    def load_contacts(self):
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                self.contacts = {}
                for name, info in data.items():
                    if isinstance(info, str):
                        self.contacts[name] = {"phone": info, "groups": []}
                    else:
                        info.setdefault("groups", [])
                        self.contacts[name] = info
            except (json.JSONDecodeError, IOError):
                self.contacts = {}
        else:
            self.contacts = {}
            self.save_contacts()
        if os.path.exists(self.groups_file):
            try:
                with open(self.groups_file, 'r') as f:
                    self.groups = json.load(f)
            except Exception:
                self.groups = {}
        else:
            self.groups = {}

    def save_contacts(self):
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, 'w') as f:
            json.dump(self.contacts, f, indent=2)

    def save_groups(self):
        os.makedirs(os.path.dirname(self.groups_file), exist_ok=True)
        with open(self.groups_file, 'w') as f:
            json.dump(self.groups, f, indent=2)

    def _build_menu(self, results=None):
        root = MenuNode("Address List")
        root.add_child(MenuNode("Add Contact", self._start_add, "n"))
        keys = sorted(results) if results else sorted(self.contacts.keys())
        for name in keys:
            info = self.contacts.get(name, {})
            phone = info.get("phone", "") if isinstance(info, dict) else info
            groups = info.get("groups", []) if isinstance(info, dict) else []
            label = f"{name}: {phone}"
            if groups:
                label += f" [{', '.join(groups)}]"
            root.add_child(MenuNode(label, lambda n=name, p=phone: self.speak(f"{n}, phone {p}")))
        
        if not keys:
            root.add_child(MenuNode("No contacts"))

        if self.groups:
            root.add_child(MenuNode("- Groups -"))
            for gname in sorted(self.groups.keys()):
                root.add_child(MenuNode(f"Group: {gname}", lambda g=gname: self.speak(f"Group {g}: {len(self.groups[g])} members")))
            
        root.add_child(MenuNode("Search", self._start_search))
        root.add_child(MenuNode("Import CSV", self._import_csv))
        root.add_child(MenuNode("Export CSV", self._export_csv))
            
        self.menu = MenuSystem(root, self.speak)

    def _start_add(self):
        self.input_mode = "name"
        self.input_buf = ""
        self.speak("Enter contact name.")
        self.window.update_text("Name: ")

    def _start_search(self):
        self.input_mode = "search"
        self.input_buf = ""
        self.speak("Search contacts. Type name or phone.")
        self.window.update_text("Search: ")

    def _do_search(self):
        q = self.input_buf.strip().lower()
        if not q:
            self.speak("No search text.")
            return
        results = []
        for name, info in self.contacts.items():
            phone = info.get("phone", "") if isinstance(info, dict) else info
            if q in name.lower() or q in phone.lower():
                results.append(name)
        if results:
            self._search_results = results
            self._build_menu(results)
            self.menu.announce_current()
            self.speak(f"Found {len(results)} contacts.")
        else:
            self.speak("No matches.")

    def _export_csv(self):
        path = os.path.join(TECH_SOFT, "contacts", "contacts_export.csv")
        try:
            with open(path, 'w') as f:
                f.write("Name,Phone,Groups\n")
                for name, info in sorted(self.contacts.items()):
                    phone = info.get("phone", "") if isinstance(info, dict) else info
                    groups = ";".join(info.get("groups", [])) if isinstance(info, dict) else ""
                    f.write(f'"{name}","{phone}","{groups}"\n')
            self.speak(f"Exported {len(self.contacts)} contacts.")
        except Exception:
            self.speak("Export failed.")

    def _import_csv(self):
        path = os.path.join(TECH_SOFT, "contacts", "contacts_export.csv")
        if not os.path.exists(path):
            self.speak("No contacts_export.csv found.")
            return
        try:
            imported = 0
            with open(path, 'r') as f:
                lines = f.readlines()
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue
                parts = [p.strip('"') for p in line.split(',')]
                name = parts[0] if len(parts) > 0 else ""
                phone = parts[1] if len(parts) > 1 else ""
                groups_str = parts[2] if len(parts) > 2 else ""
                if name and name not in self.contacts:
                    groups = [g.strip() for g in groups_str.split(";") if g.strip()]
                    self.contacts[name] = {"phone": phone, "groups": groups}
                    for g in groups:
                        self.groups.setdefault(g, []).append(name)
                    imported += 1
            self.save_contacts()
            self.save_groups()
            self.speak(f"Imported {imported} contacts.")
            self._build_menu()
        except Exception:
            self.speak("Import failed.")

    def _handle_search_results(self, vk):
        if vk == win32con.VK_ESCAPE:
            self._search_results = []
            self._build_menu()
            self.menu.announce_current()
            return
        if vk == win32con.VK_RETURN:
            item = self.menu.get_current_item()
            if item:
                name = item.title.split(":")[0].strip()
                if name in self.contacts:
                    info = self.contacts[name]
                    phone = info.get("phone", "") if isinstance(info, dict) else info
                    self.speak(f"{name}, phone {phone}. Press F8 to dial.")
            return

    def _quick_dial(self, name):
        info = self.contacts.get(name, {})
        phone = info.get("phone", "") if isinstance(info, dict) else ""
        if phone:
            self.speak(f"Dialing {phone} for {name}.")
        else:
            self.speak(f"No phone for {name}.")

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

        if vk == win32con.VK_F5:
            self._start_search()
            return

        if vk == win32con.VK_F6:
            self._manage_groups()
            return

        if vk == win32con.VK_F8:
            item = self.menu.get_current_item()
            if item and ":" in item.title:
                name = item.title.split(":")[0].strip()
                self._quick_dial(name)
            return

        if vk == win32con.VK_F9:
            self._toggle_group_membership()
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

    def _manage_groups(self):
        self.input_mode = "group_name"
        self.input_buf = ""
        self.speak("Enter new group name, or press Enter for group list.")
        self.window.update_text("Group: ")

    def _show_groups(self):
        if not self.groups:
            self.speak("No groups.")
            return
        root = MenuNode("Groups")
        for gname in sorted(self.groups.keys()):
            root.add_child(MenuNode(f"{gname} ({len(self.groups[gname])})"))
        root.add_child(MenuNode("Back", lambda: self._build_menu()))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _toggle_group_membership(self):
        item = self.menu.get_current_item()
        if not item or ":" not in item.title:
            return
        name = item.title.split(":")[0].strip()
        if name not in self.contacts:
            return
        if not self.groups:
            self.speak("No groups. Create one with F6.")
            return
        info = self.contacts[name]
        gnames = sorted(self.groups.keys())
        cur = info.get("groups", [])
        next_g = [g for g in gnames if g not in cur]
        if next_g:
            g = next_g[0]
            info.setdefault("groups", []).append(g)
            self.groups.setdefault(g, []).append(name)
            self.speak(f"{name} added to {g}.")
        else:
            g = gnames[0]
            info.get("groups", []).remove(g)
            self.groups[g].remove(name)
            self.speak(f"{name} removed from {g}.")
        self.save_contacts()
        self.save_groups()
        self._build_menu()

    def _handle_input(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.input_mode = None
            self.on_focus()
            return

        if vk == win32con.VK_RETURN:
            val = self.input_buf.strip()
            if self.input_mode == "search":
                self.input_mode = None
                self._do_search()
                return
            if self.input_mode == "group_name":
                if val:
                    self.groups[val] = []
                    self.save_groups()
                    self.speak(f"Group {val} created.")
                self.input_mode = None
                self._show_groups()
                return
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
                self.contacts[self.editing_name] = {"phone": val, "groups": []}
                self.save_contacts()
                self.input_mode = None
                self.speak(f"Added {self.editing_name}.")
                self.on_focus()
            elif self.input_mode == "edit_name":
                old_name = self.editing_name
                old_info = self.contacts.pop(old_name)
                old_phone = old_info.get("phone", old_info) if isinstance(old_info, dict) else old_info
                old_groups = old_info.get("groups", []) if isinstance(old_info, dict) else []
                self.editing_name = val
                self.input_mode = "edit_phone"
                self.input_buf = old_phone
                self.speak(f"Enter new phone for {val}. Current: {old_phone}")
                self.window.update_text(f"Phone: {old_phone}")
            elif self.input_mode == "edit_phone":
                old_info = self.contacts.get(self.editing_name, {})
                old_groups = old_info.get("groups", []) if isinstance(old_info, dict) else []
                self.contacts[self.editing_name] = {"phone": val, "groups": old_groups}
                self.save_contacts()
                self.input_mode = None
                self.speak(f"Updated {self.editing_name}.")
                self.on_focus()
            return

        if vk == win32con.VK_BACK:
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                label_map = {"name": "Name", "edit_name": "Name", "phone": "Phone", "edit_phone": "Phone", "search": "Search", "group_name": "Group"}
                label = label_map.get(self.input_mode, "Input")
                self.window.update_text(f"{label}: {self.input_buf}")
            return

        ch = self._vk_to_char(vk)
        if ch:
            self.input_buf += ch
            label_map = {"name": "Name", "edit_name": "Name", "phone": "Phone", "edit_phone": "Phone", "search": "Search", "group_name": "Group"}
            label = label_map.get(self.input_mode, "Input")
            self.window.update_text(f"{label}: {self.input_buf}")

    def _delete_contact(self):
        item = self.menu.get_current_item()
        if not item or item.title in ("No contacts", "Add Contact", "Search", "Import CSV", "Export CSV", "- Groups -"):
            return
        if item.title.startswith("Group:"):
            return
        name = item.title.rsplit(":", 1)[0].strip()
        # skip if the name starts with a label we don't want to delete
        if name in self.contacts:
            info = self.contacts.pop(name)
            for g in info.get("groups", []):
                if name in self.groups.get(g, []):
                    self.groups[g].remove(name)
            self.save_contacts()
            self.save_groups()
            self._build_menu()
            if self.menu.get_current_item():
                self.window.update_text("Contacts: " + self.menu.get_current_item().title)
            else:
                self.window.update_text("Contacts: Empty")

    def _start_edit(self):
        item = self.menu.get_current_item()
        if not item or item.title in ("No contacts", "Add Contact", "Search", "Import CSV", "Export CSV", "- Groups -"):
            return
        if item.title.startswith("Group:"):
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
        return "Address List. Space/Backspace browse, Enter select. F5 search, F6 groups, F8 quick dial, F9 add/remove group, F2 edit, Delete remove. Escape exit."
