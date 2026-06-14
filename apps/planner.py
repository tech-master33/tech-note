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
        self.load_tasks()

    def load_tasks(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    self.tasks = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.tasks = []
        else:
            self.tasks = ["Check Email", "Write Report", "Call John"]
            self.save_tasks()

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
        # Implementation for adding tasks can be added later
        self.speak("Add task feature coming soon.")

    def on_focus(self):
        self._build_menu()
        item = self.menu.get_current_item()
        self.speak("Planner. " + item.title)
        self.window.update_text("Planner: " + item.title)

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        if vk in (win32con.VK_SPACE):
            self.menu.next()
        elif vk in (win32con.VK_BACK):
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))

        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Planner: " + item.title)
            
    def get_help_text(self):
        return "Planner. Space for next, Backspace for previous. Enter to select. Press Escape to exit."
