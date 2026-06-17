import os
import json
import win32con
from core.app_base import SoftApp
from core.config import TECH_SOFT
from core.menu import MenuNode, MenuSystem

class PlannerApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.data_file = os.path.join(TECH_SOFT, 'planner.json')
        self.tasks = []
        self.menu = None
        self.input_mode = None
        self.input_buf = ""
        self.load_tasks()

    def load_tasks(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    self.tasks = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.tasks = []
        else:
            self.tasks = []

    def save_tasks(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.tasks, f)

    def _build_menu(self):
        root = MenuNode("Planner")
        root.add_child(MenuNode("Add Task", self._start_add_task, "n"))
        for i, task in enumerate(self.tasks):
            root.add_child(MenuNode(task, lambda t=task: self.speak(t)))
        
        if not self.tasks:
            root.add_child(MenuNode("No tasks"))
            
        self.menu = MenuSystem(root, self.speak)

    def _start_add_task(self):
        self.input_mode = "add"
        self.input_buf = ""
        self.speak("Enter task name.")
        self.window.update_text("Task: ")

    def on_focus(self):
        self._build_menu()
        item = self.menu.get_current_item()
        self.speak("Planner. " + item.title)
        self.window.update_text("Planner: " + item.title)

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
            self._delete_task()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))

        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Planner: " + item.title)

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
            self.tasks.append(val)
            self.save_tasks()
            self.input_mode = None
            self.speak(f"Added: {val}")
            self.on_focus()
            return

        if vk == win32con.VK_BACK:
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                self.window.update_text(f"Task: {self.input_buf}")
            return

        ch = self._vk_to_char(vk)
        if ch:
            self.input_buf += ch
            self.window.update_text(f"Task: {self.input_buf}")

    def _delete_task(self):
        item = self.menu.get_current_item()
        if not item or item.title in ("No tasks", "Add Task"):
            return
        task = item.title
        self.tasks.remove(task)
        self.save_tasks()
        self.speak(f"Deleted: {task}")
        self._build_menu()
        if self.menu.get_current_item():
            self.window.update_text("Planner: " + self.menu.get_current_item().title)
        else:
            self.window.update_text("Planner: Empty")

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text("Planner: " + item.title)
            
    def get_help_text(self):
        return "Planner. Space for next, Backspace for previous. Enter to select. Delete to remove task. Escape to exit."
