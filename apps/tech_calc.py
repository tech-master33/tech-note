import json
import win32con
import re
from core.app_base import SoftApp
from core.config import TECH_SOFT

class TechCalc(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.expression = ""
        self.history_file = os.path.join(TECH_SOFT, 'calc_history.json')
        self.history = self.load_history()

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def save_history(self):
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f)

    def _safe_eval(self, expr):
        allowed = re.compile(r'^[\d\s\+\-\*\/\(\)\.]+$')
        if not allowed.match(expr):
            raise ValueError("Invalid characters")
        return eval(expr, {"__builtins__": {}}, {})

    def on_focus(self):
        self.speak("Calculator. Enter expression and press Enter.")
        self.window.update_text("Calc: ")

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
        elif vk == win32con.VK_BACK:
            if self.expression:
                self.expression = self.expression[:-1]
                self.window.update_text(self.expression)
        elif vk == win32con.VK_RETURN:
            try:
                result = self._safe_eval(self.expression)
                self.history.append(f"{self.expression} = {result}")
                self.save_history()
                self.speak(f"Result is {result}")
                self.expression = ""
                self.window.update_text("Calc: ")
            except Exception:
                self.speak("Error")
        else:
            char = None
            if 0x30 <= vk <= 0x39: char = chr(vk)
            elif vk == 0x6B: char = "+"
            elif vk == 0x6D: char = "-"
            elif vk == 0x6A: char = "*"
            elif vk == 0x6F: char = "/"
            elif vk == 0x6E: char = "."
            
            if char:
                self.expression += char
                self.window.update_text(self.expression)
                self.speak(char)
