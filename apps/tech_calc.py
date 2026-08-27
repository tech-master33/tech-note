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
MEMORY_FILE = os.path.join(TECH_SOFT, "calc_memory.json")
CONVERSION_FILE = os.path.join(TECH_SOFT, "calc_conversions.json")

MODE_BASIC = 0
MODE_SCIENTIFIC = 1
MODE_PROGRAMMER = 2

STATE_CALC = 0
STATE_HISTORY = 1
STATE_CONVERT = 2

CONVERSION_CATEGORIES = {
    "Length": {
        "meters": 1.0, "kilometers": 1000.0, "centimeters": 0.01,
        "millimeters": 0.001, "miles": 1609.344, "yards": 0.9144,
        "feet": 0.3048, "inches": 0.0254,
    },
    "Mass": {
        "grams": 1.0, "kilograms": 1000.0, "milligrams": 0.001,
        "pounds": 453.592, "ounces": 28.3495, "tons": 1000000.0,
    },
    "Volume": {
        "liters": 1.0, "milliliters": 0.001, "gallons": 3.78541,
        "quarts": 0.946353, "pints": 0.473176, "cups": 0.236588,
        "fluid ounces": 0.0295735,
    },
    "Temperature": {
        "celsius": 1.0, "fahrenheit": 1.0, "kelvin": 1.0,
    },
}


class TechCalc(SoftApp):
    app_id = "calculator"
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.expression = ""
        self.history = self._load_history()
        self.memory = self._load_memory()
        self.mode = MODE_BASIC
        self.state = STATE_CALC
        self._deg_mode = True
        self._conversion_category = "Length"
        self._conversion_from = 0
        self._conversion_to = 0
        self._conversion_value = ""
        self._conversion_step = 0
        self._history_index = 0
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
                json.dump(self.history[-100:], f)
        except Exception:
            pass

    def _load_memory(self):
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return 0.0

    def _save_memory(self):
        try:
            os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
            with open(MEMORY_FILE, 'w') as f:
                json.dump(self.memory, f)
        except Exception:
            pass

    def _safe_eval(self, expr):
        ns = {"__builtins__": {}}
        if self.mode == MODE_SCIENTIFIC:
            ns.update({
                "sin": math.sin, "cos": math.cos, "tan": math.tan,
                "asin": math.asin, "acos": math.acos, "atan": math.atan,
                "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
                "log": math.log10, "ln": math.log, "sqrt": math.sqrt,
                "exp": math.exp, "pi": math.pi, "e": math.e,
                "radians": math.radians, "degrees": math.degrees,
                "factorial": math.factorial, "floor": math.floor, "ceil": math.ceil,
                "abs": abs, "round": round,
            })
        match = re.match(r'^([\d\.eE+\-]+)\s*!\s*$', expr.strip())
        if match:
            n = int(float(match.group(1)))
            return math.factorial(n)
        allowed = re.compile(r'^[\d\s\+\-\*\/\(\)\.\%e\w]+$')
        if not allowed.match(expr):
            raise ValueError("Invalid characters")
        result = eval(expr, ns, {})
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
            root.add_child(MenuNode("asin", lambda: self._insert_fn("asin(")))
            root.add_child(MenuNode("acos", lambda: self._insert_fn("acos(")))
            root.add_child(MenuNode("atan", lambda: self._insert_fn("atan(")))
            root.add_child(MenuNode("sinh", lambda: self._insert_fn("sinh(")))
            root.add_child(MenuNode("cosh", lambda: self._insert_fn("cosh(")))
            root.add_child(MenuNode("tanh", lambda: self._insert_fn("tanh(")))
            root.add_child(MenuNode("log", lambda: self._insert_fn("log(")))
            root.add_child(MenuNode("ln", lambda: self._insert_fn("ln(")))
            root.add_child(MenuNode("sqrt", lambda: self._insert_fn("sqrt(")))
            root.add_child(MenuNode("pi", lambda: self._insert_fn("pi")))
            root.add_child(MenuNode("e", lambda: self._insert_fn("e")))
            root.add_child(MenuNode("x^y", lambda: self._insert_fn("**")))
            root.add_child(MenuNode("x!", lambda: self._insert_fn("!")))
            root.add_child(MenuNode("Deg/Rad", self._toggle_angle_mode))
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
        root.add_child(MenuNode("Memory+", lambda: self._memory_add()))
        root.add_child(MenuNode("Memory-", lambda: self._memory_sub()))
        root.add_child(MenuNode("Memory Recall", lambda: self._memory_recall()))
        root.add_child(MenuNode("Memory Clear", lambda: self._memory_clear()))
        root.add_child(MenuNode("Unit Convert", self._enter_convert))
        root.add_child(MenuNode("Back", self.exit_app))
        if self.history:
            root.add_child(MenuNode(f"History ({len(self.history)})", self._show_history))
        self.menu = MenuSystem(root, self.speak, stop_func=self.stop)

    def _insert_fn(self, fn_text):
        self.expression += fn_text
        self.speak(fn_text)
        self._build_menu()
        self.window.update_text(f"Calc: {self.expression}")

    def _toggle_angle_mode(self):
        self._deg_mode = not self._deg_mode
        self.speak(f"{'Degrees' if self._deg_mode else 'Radians'} mode.")
        self._build_menu()

    def _memory_add(self):
        if self.expression:
            try:
                val = self._safe_eval(self.expression)
            except Exception:
                val = 0.0
            self.memory = self.memory + val
            self._save_memory()
            self.speak(f"Memory plus. Memory: {self.memory:.10g}")
        else:
            self.speak("No expression to add.")

    def _memory_sub(self):
        if self.expression:
            try:
                val = self._safe_eval(self.expression)
            except Exception:
                val = 0.0
            self.memory = self.memory - val
            self._save_memory()
            self.speak(f"Memory minus. Memory: {self.memory:.10g}")
        else:
            self.speak("No expression to subtract.")

    def _memory_recall(self):
        self.expression = f"{self.memory:.10g}"
        self.speak(f"Memory recalled: {self.expression}")
        self.window.update_text(f"Calc: {self.expression}")

    def _memory_clear(self):
        self.memory = 0.0
        self._save_memory()
        self.speak("Memory cleared.")
        self._build_menu()

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
        for entry in reversed(self.history[-50:]):
            root.add_child(MenuNode(entry))
        root.add_child(MenuNode("Back", self._build_menu_back))
        self.menu = MenuSystem(root, self.speak, stop_func=self.stop)
        self.menu.announce_current()

    def _enter_history(self):
        if not self.history:
            self.speak("No history.")
            return
        self.state = STATE_HISTORY
        self._history_index = len(self.history) - 1
        item = self._format_history(self._history_index)
        self.speak(f"History: {item}")
        self.window.update_text(f"History: {item}")

    def _format_history(self, idx):
        if idx < 0 or idx >= len(self.history):
            return ""
        return self.history[idx]

    def _recall_history(self, idx):
        if idx < 0 or idx >= len(self.history):
            return
        entry = self.history[idx]
        match = re.search(r'=\s*([\d\.\-eE+]+)', entry)
        if match:
            self.expression = match.group(1)
            self.speak(f"Recalled: {self.expression}")
            self.window.update_text(f"Calc: {self.expression}")
        self.state = STATE_CALC

    def _build_menu_back(self):
        self.state = STATE_CALC
        self._build_menu()
        self.menu.announce_current()

    def _enter_convert(self):
        self.state = STATE_CONVERT
        self._conversion_category = "Length"
        self._conversion_from = 0
        self._conversion_to = 0
        self._conversion_value = ""
        self._conversion_step = 0
        cats = list(CONVERSION_CATEGORIES.keys())
        self.speak(f"Unit convert. Category: {cats[0]}.")
        self.window.update_text(f"Convert: {cats[0]}")

    def _convert_do(self):
        cats = list(CONVERSION_CATEGORIES.keys())
        cat = self._conversion_category
        units = CONVERSION_CATEGORIES[cat]
        try:
            val = float(self._conversion_value)
        except ValueError:
            self.speak("Invalid number.")
            return
        unit_names = list(units.keys())
        from_unit = unit_names[self._conversion_from]
        to_unit = unit_names[self._conversion_to]
        if cat == "Temperature":
            result = self._convert_temperature(val, from_unit, to_unit)
        else:
            result = val * units[from_unit] / units[to_unit]
        result_str = f"{result:.10g}".rstrip('0').rstrip('.')
        self.speak(f"{val} {from_unit} = {result_str} {to_unit}")
        self.window.update_text(f"{val} {from_unit} = {result_str} {to_unit}")
        self.state = STATE_CALC

    def _convert_temperature(self, val, from_unit, to_unit):
        if from_unit == to_unit:
            return val
        if from_unit == "celsius":
            if to_unit == "fahrenheit":
                return val * 9/5 + 32
            return val + 273.15
        if from_unit == "fahrenheit":
            if to_unit == "celsius":
                return (val - 32) * 5/9
            return (val - 32) * 5/9 + 273.15
        if from_unit == "kelvin":
            if to_unit == "celsius":
                return val - 273.15
            return (val - 273.15) * 9/5 + 32

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
        self.state = STATE_CALC
        self._build_menu()
        self.speak(f"Calculator ({self._mode_name()}). Type numbers and operators. Enter to calculate. F5 mode, F6 history, F7 memory, F8 convert.")
        self.window.update_text("Calc:")

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            if self.state == STATE_HISTORY or self.state == STATE_CONVERT:
                self.state = STATE_CALC
                self._build_menu()
                self.menu.announce_current()
                return True
            self.exit_app()
            return True

        if self.state == STATE_HISTORY:
            return self._handle_history_key(vk)
        if self.state == STATE_CONVERT:
            return self._handle_convert_key(vk)

        if vk == win32con.VK_F5:
            self.mode = (self.mode + 1) % 3
            self.speak(f"Mode: {self._mode_name()}")
            self._build_menu()
            return True

        if vk == win32con.VK_F6:
            self._enter_history()
            return True

        if vk == win32con.VK_F7:
            if self.expression:
                try:
                    val = self._safe_eval(self.expression)
                    self.memory = self.memory + val
                    self._save_memory()
                    self.speak(f"Memory plus. Memory: {self.memory:.10g}")
                except Exception:
                    self.speak("Error adding to memory.")
            else:
                self._memory_recall()
            return True

        if vk == win32con.VK_F8:
            if self._is_shift_pressed():
                if self.expression:
                    try:
                        val = self._safe_eval(self.expression)
                        self.memory = self.memory - val
                        self._save_memory()
                        self.speak(f"Memory minus. Memory: {self.memory:.10g}")
                    except Exception:
                        self.speak("Error subtracting.")
                return True
            self._enter_convert()
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

    def _handle_history_key(self, vk):
        if vk == win32con.VK_ESCAPE or vk == win32con.VK_F6:
            self.state = STATE_CALC
            self._build_menu()
            self.menu.announce_current()
            return True
        if vk == win32con.VK_UP or vk == win32con.VK_BACK:
            if self._history_index > 0:
                self._history_index -= 1
                item = self._format_history(self._history_index)
                self.speak(item)
                self.window.update_text(f"History: {item}")
        if vk == win32con.VK_DOWN or vk == win32con.VK_SPACE:
            if self._history_index < len(self.history) - 1:
                self._history_index += 1
                item = self._format_history(self._history_index)
                self.speak(item)
                self.window.update_text(f"History: {item}")
        if vk == win32con.VK_RETURN:
            self._recall_history(self._history_index)
        return True

    def _handle_convert_key(self, vk):
        cats = list(CONVERSION_CATEGORIES.keys())
        if vk == win32con.VK_ESCAPE or vk == win32con.VK_F8:
            self.state = STATE_CALC
            self._build_menu()
            self.menu.announce_current()
            return True
        if vk == win32con.VK_F5:
            ci = cats.index(self._conversion_category)
            self._conversion_category = cats[(ci + 1) % len(cats)]
            self._conversion_from = 0
            self._conversion_to = 1 if len(CONVERSION_CATEGORIES[self._conversion_category]) > 1 else 0
            self.speak(f"Category: {self._conversion_category}")
            self.window.update_text(f"Convert: {self._conversion_category}")
            return True
        if vk == win32con.VK_F6:
            units = list(CONVERSION_CATEGORIES[self._conversion_category].keys())
            self._conversion_from = (self._conversion_from + 1) % len(units)
            unit_names = list(CONVERSION_CATEGORIES[self._conversion_category].keys())
            self.speak(f"From: {unit_names[self._conversion_from]}")
            self.window.update_text(f"Convert from: {unit_names[self._conversion_from]}")
            return True
        if vk == win32con.VK_F7:
            units = list(CONVERSION_CATEGORIES[self._conversion_category].keys())
            self._conversion_to = (self._conversion_to + 1) % len(units)
            unit_names = list(CONVERSION_CATEGORIES[self._conversion_category].keys())
            self.speak(f"To: {unit_names[self._conversion_to]}")
            self.window.update_text(f"Convert to: {unit_names[self._conversion_to]}")
            return True
        if vk == win32con.VK_BACK:
            if self._conversion_value:
                self._conversion_value = self._conversion_value[:-1]
                self.window.update_text(f"Value: {self._conversion_value}")
            return True
        if vk == win32con.VK_RETURN:
            self._convert_do()
            return True
        ch = self._vk_to_char(vk)
        if ch and ch in '0123456789.-':
            self._conversion_value += ch
            self.window.update_text(f"Value: {self._conversion_value}")
            return True
        return True

    def _is_shift_pressed(self):
        return win32api.GetAsyncKeyState(win32con.VK_SHIFT) & 0x8000

    def on_key_up(self, vk):
        if self.state != STATE_CALC:
            return
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            if self.menu:
                self.menu.next()
                item = self.menu.get_current_item()
                if item:
                    self.window.update_text(item.title)

    def get_help_text(self):
        base = f"Calculator ({self._mode_name()}). Type numbers and operators. Enter to calculate. F5 mode, F6 history, F7 memory+, F8 convert, Shift+F8 memory-."
        if self.state == STATE_CONVERT:
            cats = list(CONVERSION_CATEGORIES.keys())
            unit_names = list(CONVERSION_CATEGORIES[self._conversion_category].keys())
            return f"Unit convert. {self._conversion_category}: {unit_names[self._conversion_from]} to {unit_names[self._conversion_to]}. F5 category, F6 from, F7 to. Type value, Enter convert. Escape back."
        if self.state == STATE_HISTORY:
            return f"History: {len(self.history)} entries. Up/Down browse, Enter recall. Escape back."
        return base
