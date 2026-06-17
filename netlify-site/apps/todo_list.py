import os
import json
import datetime
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode
from core.config import TECH_SOFT

TODO_FILE = os.path.join(TECH_SOFT, "todo.json")


class TodoList(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.items = self._load_items()
        self.editing = False
        self.edit_text = ""
        self.cursor = 0
        self._build_menu()

    def _load_items(self):
        if os.path.exists(TODO_FILE):
            try:
                with open(TODO_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return []

    def _save_items(self):
        try:
            os.makedirs(os.path.dirname(TODO_FILE), exist_ok=True)
            with open(TODO_FILE, 'w') as f:
                json.dump(self.items, f, indent=2)
        except:
            pass

    def _build_menu(self):
        root = MenuNode("Todo List")
        pending = [i for i in self.items if not i.get("done")]
        done = [i for i in self.items if i.get("done")]

        root.add_child(MenuNode(f"Add Task", self._add_task))

        if pending:
            for idx, item in enumerate(self.items):
                if not item.get("done"):
                    text = item.get("text", "")
                    root.add_child(MenuNode(f"[ ] {text}", lambda i=idx: self._toggle_task(i)))

        if done:
            root.add_child(MenuNode(f"Completed ({len(done)})", self._show_done))

        if self.items:
            root.add_child(MenuNode("Clear Completed", self._clear_done))

        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _add_task(self):
        self.editing = True
        self.edit_text = ""
        self.speak("Type your task. Press Enter to save.")
        self.window.update_text("Task: ")

    def _toggle_task(self, idx):
        item = self.items[idx]
        item["done"] = not item.get("done", False)
        if item["done"]:
            item["completed"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            self.speak(f"Completed: {item.get('text', '')}")
        else:
            self.speak(f"Uncompleted: {item.get('text', '')}")
        self._save_items()
        self._build_menu()
        self.menu.announce_current()

    def _show_done(self):
        done = [i for i in self.items if i.get("done")]
        if not done:
            self.speak("No completed tasks.")
            return
        root = MenuNode("Completed Tasks")
        for item in done:
            text = item.get("text", "")
            completed = item.get("completed", "")
            root.add_child(MenuNode(f"[x] {text} ({completed})"))
        root.add_child(MenuNode("Back", self._build_menu_back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _clear_done(self):
        self.items = [i for i in self.items if not i.get("done")]
        self._save_items()
        self.speak("Completed tasks cleared.")
        self._build_menu()
        self.menu.announce_current()

    def _build_menu_back(self):
        self._build_menu()
        self.menu.announce_current()

    def on_focus(self):
        pending = len([i for i in self.items if not i.get("done")])
        self.speak(f"Todo List. {pending} tasks remaining.")
        self.window.update_text(f"{pending} tasks remaining")

    def on_key(self, vk):
        if self.editing:
            if vk == win32con.VK_ESCAPE:
                self.editing = False
                self._build_menu()
                self.menu.announce_current()
                return
            if vk == win32con.VK_RETURN:
                if self.edit_text.strip():
                    self.items.append({"text": self.edit_text.strip(), "done": False})
                    self._save_items()
                    self.speak(f"Added: {self.edit_text.strip()}")
                self.editing = False
                self._build_menu()
                self.menu.announce_current()
                return
            if vk == win32con.VK_BACK:
                if self.edit_text:
                    self.edit_text = self.edit_text[:-1]
                self.window.update_text(self.edit_text if self.edit_text else "Task: ")
                return
            ch = self._vk_to_char(vk)
            if ch:
                self.edit_text += ch
                self.window.update_text(self.edit_text)
            return

        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))

        item = self.menu.get_current_item()
        if item:
            self.window.update_text(item.title)

    def on_key_up(self, vk):
        if self.editing:
            return
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text(item.title)

    def get_help_text(self):
        if self.editing:
            return "Type your task. Enter to save, Escape to cancel."
        return "Todo List. Add tasks, mark complete. Space for next, Backspace for previous."
