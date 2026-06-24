import os
import json
import re
import math
import win32con
import win32api
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode
from core.config import TECH_SOFT

HISTORY_FILE = os.path.join(TECH_SOFT, "calc_history.json")

MODE_BASIC = 0
MODE_SCIENTIFIC = 1
MODE_PROGRAMMER = 2


class TechCalc(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.expression = ""
        self.history = self._load_history()
        self.mode = MODE_BASIC
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
        allowed = re.compile(r'^[\d\s\+\-\*\/\(\)\.\%e]+$')
        if not allowed.match(expr):
            raise ValueError("Invalid characters")
        result = eval(expr, {"__builtins__": {}}, {})
        return result

    def _mode_name(self):
        return ["Basic", "Scientific", "Programmer"][self.mode]

    def _build_menu(self):
        title = f"Calculator ({self._mode_name()})"
        root = MenuNode(title)
        if self.expression:
            root.add_child(MenuNode(f"Expression: {self.expression}"))
        root.add_child(MenuNode("Clear Entry", self._clear_entry))
        root.add_child(MenuNode("Clear All", self._clear_all))
        if self.mode == MODE_SCIENTIFIC:
            root.add_child(MenuNode("sin", lambda: self._insert_fn("sin(")))
            root.add_child(MenuNode("cos", lambda: self._insert_fn("cos(")))
            root.add_child(MenuNode("tan", lambda: self._insert_fn("tan(")))
            root.add_child(MenuNode("log", lambda: self._insert_fn("log(")))
            root.add_child(MenuNode("ln", lambda: self._insert_fn("ln(")))
            root.add_child(MenuNode("sqrt", lambda: self._insert_fn("sqrt(")))
            root.add_child(MenuNode("pi", lambda: self._insert_fn("pi")))
            root.add_child(MenuNode("e", lambda: self._insert_fn("e")))
            root.add_child(MenuNode("x^y", lambda: self._insert_fn("**")))
        elif self.mode == MODE_PROGRAMMER:
            root.add_child(MenuNode("AND", lambda: self._insert_fn(" & ")))
            root.add_child(MenuNode("OR", lambda: self._insert_fn(" | ")))
            root.add_child(MenuNode("XOR", lambda: self._insert_fn(" ^ ")))
            root.add_child(MenuNode("NOT", lambda: self._insert_fn("~")))
            root.add_child(MenuNode("LSHIFT", lambda: self._insert_fn(" << ")))
            root.add_child(MenuNode("RSHIFT", lambda: self._insert_fn(" >> ")))
            root.add_child(MenuNode("to Hex", self._to_hex))
            root.add_child(MenuNode("to Binary", self._to_bin))
            root.add_child(MenuNode("to Dec", self._to_dec))
        root.add_child(MenuNode("Back", self.exit_app))
        if self.history:
            root.add_child(MenuNode(f"History ({len(self.history)})", self._show_history))
        self.menu = MenuSystem(root, self.speak)

    def _insert_fn(self, fn_text):
        self.expression += fn_text
        self.speak(fn_text)
        self._build_menu()
        self.window.update_text(f"Calc: {self.expression}")

    def _to_hex(self):
        try:
            val = self._safe_eval(self.expression)
            self.expression = hex(int(val))
            self.speak(f"Hex: {self.expression}")
            self.window.update_text(f"Calc: {self.expression}")
        except:
            self.speak("Error.")

    def _to_bin(self):
        try:
            val = self._safe_eval(self.expression)
            self.expression = bin(int(val))
            self.speak(f"Binary: {self.expression}")
            self.window.update_text(f"Calc: {self.expression}")
        except:
            self.speak("Error.")

    def _to_dec(self):
        exp = self.expression.strip().lower()
        try:
            if exp.startswith("0x"):
                val = int(exp, 16)
            elif exp.startswith("0b"):
                val = int(exp, 2)
            else:
                val = int(exp)
            self.expression = str(val)
            self.speak(f"Decimal: {self.expression}")
            self.window.update_text(f"Calc: {self.expression}")
        except:
            self.speak("Error.")

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
            '%': 'percent', '&': 'and', '|': 'or', '^': 'xor',
            '~': 'not', '<': 'left shift', '>': 'right shift',
        }
        if ch in names:
            self.speak(names[ch])
        elif ch.isdigit():
            self.speak(ch)
        else:
            self.speak(ch)

    def on_focus(self):
        self._build_menu()
        self.speak(f"Calculator ({self._mode_name()}). Type numbers and operators. Enter to calculate. F5 switch mode.")
        self.window.update_text("Calc:")

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return True

        if vk == win32con.VK_F5:
            self.mode = (self.mode + 1) % 3
            self.speak(f"Mode: {self._mode_name()}")
            self._build_menu()
            return True

        if vk == win32con.VK_BACK:
            if self.expression:
                removed = self.expression[-1]
                self.expression = self.expression[:-1]
                self._speak_char(removed)
                self.window.update_text(f"Calc: {self.expression}")
                return True
            if self.menu:
                self.menu.previous()
                item = self.menu.get_current_item()
                if item:
                    self.window.update_text(item.title)
            return True

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
            return True

        if vk == win32con.VK_DELETE:
            self.expression = ""
            self.speak("Cleared.")
            self.window.update_text("Calc:")
            return True

        char = None
        if 0x60 <= vk <= 0x69:
            char = chr(vk - 0x30)
        elif vk == 0x6E:
            char = "."
        elif vk == 0x6A:
            char = "*"
        elif vk == 0x6B:
            char = "+"
        elif vk == 0x6D:
            char = "-"
        elif vk == 0x6F:
            char = "/"
        else:
            ch = self._vk_to_char(vk)
            if ch and ch in '0123456789+-*/().%':
                char = ch
            elif ch and ch in '&|^~<>':
                if self.mode == MODE_PROGRAMMER:
                    char = ch

        if char:
            self.expression += char
            self._speak_char(char)
            self.window.update_text(f"Calc: {self.expression}")

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            if self.menu:
                self.menu.next()
                item = self.menu.get_current_item()
                if item:
                    self.window.update_text(item.title)

    def get_help_text(self):
        return f"Calculator ({self._mode_name()}). Type numbers and operators. Enter to calculate. F5 switch mode. Backspace to delete. Delete to clear."
