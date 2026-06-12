import os
import json
import win32con
from core.app_base import SoftApp

class PlannerApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.data_file = os.path.join(os.environ['USERPROFILE'], '.tech-soft', 'planner.json')
        self.tasks = []
        self.load_tasks()
        self.index = 0

    def load_tasks(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                self.tasks = json.load(f)
        else:
            self.tasks = ["Task 1", "Task 2"]
            self.save_tasks()

    def save_tasks(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.tasks, f)

    def on_focus(self):
        if self.index >= len(self.tasks):
            self.index = 0
        self.speak("Planner. " + (self.tasks[self.index] if self.tasks else "No tasks"))
        self.window.update_text("Planner: " + (self.tasks[self.index] if self.tasks else "Empty"))

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        
        if not self.tasks:
            self.speak("No tasks")
            return

        if vk == win32con.VK_SPACE or vk == win32con.VK_DOWN:
            self.index = (self.index + 1) % len(self.tasks)
            self.speak(self.tasks[self.index])
            self.window.update_text(self.tasks[self.index])
        elif vk == win32con.VK_BACK or vk == win32con.VK_UP:
            self.index = (self.index - 1) % len(self.tasks)
            self.speak(self.tasks[self.index])
            self.window.update_text(self.tasks[self.index])
        elif vk == win32con.VK_RETURN:
            self.speak("Selected " + self.tasks[self.index])
