import os
import json
import re
import win32con
import win32api
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode
from core.config import TECH_SOFT

HISTORY_FILE = os.path.join(TECH_SOFT, "calc_history.json")


class TechCalc(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.expression = ""
        self.history = self._load_history()
        self.menu = None
        self._build_menu()

    def _load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_history(self):
        try:
            os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
            with open(HISTORY_FILE, 'w') as f:
                json.dump(self.history[-50:], f)
        except Exception:
            pass

    def _safe_eval(self, expr):
        allowed = re.compile(r'^[\d\s\+\-\*\/\(\)\.\%]+$')
        if not allowed.match(expr):
            raise ValueError("Invalid characters")
        result = eval(expr, {"__builtins__": {}}, {})
        return result

    def _build_menu(self):
        root = MenuNode("Calculator")
        if self.expression:
            root.add_child(MenuNode(f"Expression: {self.expression}"))
        root.add_child(MenuNode("Clear Entry", self._clear_entry))
        root.add_child(MenuNode("Clear All", self._clear_all))
        if self.history:
            root.add_child(MenuNode(f"History ({len(self.history)})", self._show_history))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _clear_entry(self):
        self.expression = ""
        self.speak("Cleared.")
        self._build_menu()
        self.window.update_text("Calc:")

    def _clear_all(self):
        self.expression = ""
        self.history.clear()
        self._save_history()
        self.speak("All cleared.")
        self._build_menu()
        self.window.update_text("Calc:")

    def _show_history(self):
        if not self.history:
            self.speak("No history.")
            return
        root = MenuNode("History")
        for entry in reversed(self.history[-20:]):
            root.add_child(MenuNode(entry))
        root.add_child(MenuNode("Back", self._build_menu_back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _build_menu_back(self):
        self._build_menu()
        self.menu.announce_current()

    def _speak_char(self, ch):
        names = {
            '+': 'plus', '-': 'minus', '*': 'times', '/': 'divided by',
            '.': 'point', '(': 'open paren', ')': 'close paren',
            '%': 'percent'
        }
        if ch in names:
            self.speak(names[ch])
        elif ch.isdigit():
            self.speak(ch)
        else:
            self.speak(ch)

    def on_focus(self):
        self._build_menu()
        self.speak("Calculator. Type numbers and operators. Enter to calculate.")
        self.window.update_text("Calc:")

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        if vk == win32con.VK_BACK:
            if self.expression:
                removed = self.expression[-1]
                self.expression = self.expression[:-1]
                self._speak_char(removed)
                self.window.update_text(f"Calc: {self.expression}")
                return

        if vk == win32con.VK_RETURN:
            if self.expression:
                try:
                    result = self._safe_eval(self.expression)
                    result_str = f"{result}" if isinstance(result, int) else f"{result:.10g}"
                    entry = f"{self.expression} = {result_str}"
                    self.history.append(entry)
                    self._save_history()
                    self.speak(f"Equals {result_str}")
                    self.expression = result_str
                    self.window.update_text(f"Calc: {self.expression}")
                except Exception:
                    self.speak("Error. Invalid expression.")
            return

        if vk == win32con.VK_BACK and self.menu:
            self.menu.previous()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text(item.title)
            return

        if vk == win32con.VK_SPACE:
            if self.manager.space_used_in_chord:
                return
            if self.menu:
                self.menu.next()
                item = self.menu.get_current_item()
                if item:
                    self.window.update_text(item.title)
            return

        if vk == win32con.VK_DELETE:
            self.expression = ""
            self.speak("Cleared.")
            self.window.update_text("Calc:")
            return

        char = None
        if 0x30 <= vk <= 0x39:
            char = chr(vk)
        elif vk == 0x6B:
            char = "+"
        elif vk == 0x6D:
            char = "-"
        elif vk == 0x6A:
            char = "*"
        elif vk == 0x6F:
            char = "/"
        elif vk == 0x6E:
            char = "."
        elif vk == 0x37:
            shift = bool(win32api.GetKeyState(win32con.VK_SHIFT) & 0x8000)
            char = "%" if shift else "7"
        elif vk == 0x38:
            char = "*"
        elif vk == 0x39:
            char = "("
        elif vk == 0x30:
            shift = bool(win32api.GetKeyState(win32con.VK_SHIFT) & 0x8000)
            char = ")" if shift else "0"
        elif vk == 0xDB:
            char = "("
        elif vk == 0xDD:
            char = ")"
        elif vk == 0xBA:
            char = "+"
        elif vk == 0xBC:
            char = ","
        elif vk == 0xBE:
            char = "."

        if char:
            self.expression += char
            self._speak_char(char)
            self.window.update_text(f"Calc: {self.expression}")

    def get_help_text(self):
        return "Calculator. Type numbers and operators. Enter to calculate. Backspace to delete. Delete to clear all."
