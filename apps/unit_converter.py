import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode

CATEGORIES = {
    "Length": {
        "units": ["Meters", "Kilometers", "Centimeters", "Millimeters", "Miles", "Yards", "Feet", "Inches"],
        "base": "Meters",
        "to_base": {
            "Meters": 1, "Kilometers": 1000, "Centimeters": 0.01,
            "Millimeters": 0.001, "Miles": 1609.344, "Yards": 0.9144,
            "Feet": 0.3048, "Inches": 0.0254
        }
    },
    "Weight": {
        "units": ["Kilograms", "Grams", "Milligrams", "Pounds", "Ounces", "Tons"],
        "base": "Kilograms",
        "to_base": {
            "Kilograms": 1, "Grams": 0.001, "Milligrams": 0.000001,
            "Pounds": 0.453592, "Ounces": 0.0283495, "Tons": 907.185
        }
    },
    "Temperature": {
        "units": ["Celsius", "Fahrenheit", "Kelvin"],
        "base": "Celsius",
        "special": True
    },
    "Speed": {
        "units": ["km/h", "mph", "m/s", "knots"],
        "base": "km/h",
        "to_base": {
            "km/h": 1, "mph": 1.60934, "m/s": 3.6, "knots": 1.852
        }
    },
    "Volume": {
        "units": ["Liters", "Milliliters", "Gallons", "Quarts", "Cups", "Fluid Oz"],
        "base": "Liters",
        "to_base": {
            "Liters": 1, "Milliliters": 0.001, "Gallons": 3.78541,
            "Quarts": 0.946353, "Cups": 0.236588, "Fluid Oz": 0.0295735
        }
    },
    "Data": {
        "units": ["Bytes", "KB", "MB", "GB", "TB"],
        "base": "Bytes",
        "to_base": {
            "Bytes": 1, "KB": 1024, "MB": 1048576,
            "GB": 1073741824, "TB": 1099511627776
        }
    }
}


class UnitConverter(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.state = "category"
        self.cat_cursor = 0
        self.unit_cursor = 0
        self.from_unit = 0
        self.to_unit = 1
        self.input_buf = ""
        self.result = ""
        self.categories = list(CATEGORIES.keys())
        self.menu = None
        self._build_category_menu()

    def _build_category_menu(self):
        root = MenuNode("Unit Converter")
        for cat in self.categories:
            root.add_child(MenuNode(cat, lambda c=cat: self._select_category(c)))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _select_category(self, cat_name):
        self.cat_cursor = self.categories.index(cat_name)
        self.state = "units"
        self.unit_cursor = 0
        self.from_unit = 0
        self.to_unit = min(1, len(CATEGORIES[cat_name]["units"]) - 1)
        units = CATEGORIES[cat_name]["units"]
        self.speak(f"{cat_name}. Select units. FROM: {units[self.from_unit]}, TO: {units[self.to_unit]}.")
        self.window.update_text(self._render_units())

    def _build_unit_menu(self):
        cat_name = self.categories[self.cat_cursor]
        units = CATEGORIES[cat_name]["units"]
        root = MenuNode(cat_name)
        for i, u in enumerate(units):
            markers = []
            if i == self.from_unit:
                markers.append("FROM")
            if i == self.to_unit:
                markers.append("TO")
            tag = f" [{', '.join(markers)}]" if markers else ""
            root.add_child(MenuNode(f"{u}{tag}", lambda idx=i: self._toggle_unit(idx)))
        root.add_child(MenuNode("Convert", self._start_input))
        root.add_child(MenuNode("Back", self._back_to_category))
        self.menu = MenuSystem(root, self.speak)

    def _toggle_unit(self, idx):
        if idx == self.from_unit:
            self.to_unit = (self.to_unit + 1) % len(CATEGORIES[self.categories[self.cat_cursor]]["units"])
        elif idx == self.to_unit:
            self.from_unit = (self.from_unit + 1) % len(CATEGORIES[self.categories[self.cat_cursor]]["units"])
        else:
            self.from_unit = idx
        units = CATEGORIES[self.categories[self.cat_cursor]]["units"]
        self.speak(f"FROM: {units[self.from_unit]}, TO: {units[self.to_unit]}.")
        self._build_unit_menu()
        self.window.update_text(self._render_units())

    def _start_input(self):
        self.state = "input"
        self.input_buf = ""
        self.result = ""
        units = CATEGORIES[self.categories[self.cat_cursor]]["units"]
        self.speak(f"Convert from {units[self.from_unit]} to {units[self.to_unit]}. Enter value.")
        self.window.update_text(self._render_input())

    def _back_to_category(self):
        self.state = "category"
        self._build_category_menu()
        self.speak("Select category.")
        self.window.update_text("Unit Converter")

    def _convert(self, value, from_u, to_u, cat_name):
        cat = CATEGORIES[cat_name]
        if cat.get("special"):
            return self._convert_temp(value, from_u, to_u)
        base_val = value * cat["to_base"][from_u]
        return base_val / cat["to_base"][to_u]

    def _convert_temp(self, value, from_u, to_u):
        if from_u == to_u:
            return value
        celsius = value
        if from_u == "Fahrenheit":
            celsius = (value - 32) * 5 / 9
        elif from_u == "Kelvin":
            celsius = value - 273.15
        if to_u == "Celsius":
            return celsius
        elif to_u == "Fahrenheit":
            return celsius * 9 / 5 + 32
        elif to_u == "Kelvin":
            return celsius + 273.15

    def _render_units(self):
        cat_name = self.categories[self.cat_cursor]
        units = CATEGORIES[cat_name]["units"]
        lines = [f"{cat_name} Converter", ""]
        for i, u in enumerate(units):
            markers = []
            if i == self.from_unit:
                markers.append("FROM")
            if i == self.to_unit:
                markers.append("TO")
            tag = f" [{', '.join(markers)}]" if markers else ""
            lines.append(f"  {u}{tag}")
        lines.append("")
        lines.append("Enter to convert. Escape to go back.")
        return "\n".join(lines)

    def _render_input(self):
        cat_name = self.categories[self.cat_cursor]
        units = CATEGORIES[cat_name]["units"]
        lines = [f"{cat_name}: {units[self.from_unit]} to {units[self.to_unit]}", ""]
        lines.append(f"Value: {self.input_buf}_")
        if self.result:
            lines.append("")
            lines.append(f"Result: {self.result}")
        return "\n".join(lines)

    def on_focus(self):
        self.state = "category"
        self._build_category_menu()
        self.speak("Unit Converter. Select a category.")
        self.window.update_text("Unit Converter")

    def on_key(self, vk):
        if self.state == "input":
            units = CATEGORIES[self.categories[self.cat_cursor]]["units"]
            if vk == win32con.VK_ESCAPE:
                self.state = "units"
                self._build_unit_menu()
                self.window.update_text(self._render_units())
            elif vk == win32con.VK_RETURN:
                try:
                    val = float(self.input_buf)
                    cat_name = self.categories[self.cat_cursor]
                    res = self._convert(val, units[self.from_unit], units[self.to_unit], cat_name)
                    if abs(res) >= 1000000 or (abs(res) < 0.001 and res != 0):
                        self.result = f"{res:.6g}"
                    else:
                        self.result = f"{res:.4g}"
                    self.speak(f"{val} {units[self.from_unit]} is {self.result} {units[self.to_unit]}.")
                except ValueError:
                    self.speak("Invalid number.")
            elif vk == win32con.VK_BACK:
                if self.input_buf:
                    self.input_buf = self.input_buf[:-1]
                    self.result = ""
            elif vk == 0x2E or (0x30 <= vk <= 0x39) or vk == 0x6B or vk == 0x6D:
                if vk == 0x2E:
                    ch = "."
                elif vk == 0x6B:
                    ch = "+"
                elif vk == 0x6D:
                    ch = "-"
                else:
                    ch = chr(vk)
                if ch not in self.input_buf or ch in "+-":
                    self.input_buf += ch
                    self.result = ""
            self.window.update_text(self._render_input())
            return

        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        elif vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_SPACE:
            if self.manager.space_used_in_chord:
                return
            self.menu.next()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))

    def get_help_text(self):
        return "Unit Converter. Convert between length, weight, temperature, speed, volume, and data units."
