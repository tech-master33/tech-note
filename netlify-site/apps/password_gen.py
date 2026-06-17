import random
import string
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode


class PasswordGenerator(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.length = 16
        self.use_upper = True
        self.use_lower = True
        self.use_digits = True
        self.use_symbols = True
        self.generated = ""
        self.cursor = 0
        self._build_menu()

    def _build_menu(self):
        root = MenuNode("Password Generator")
        opts = []
        opts.append(MenuNode(f"Length: {self.length}", self._adjust_length))
        opts.append(MenuNode(f"Uppercase: {'On' if self.use_upper else 'Off'}", self._toggle_upper))
        opts.append(MenuNode(f"Lowercase: {'On' if self.use_lower else 'Off'}", self._toggle_lower))
        opts.append(MenuNode(f"Digits: {'On' if self.use_digits else 'Off'}", self._toggle_digits))
        opts.append(MenuNode(f"Symbols: {'On' if self.use_symbols else 'Off'}", self._toggle_symbols))
        opts.append(MenuNode("Generate", self._generate))
        if self.generated:
            opts.append(MenuNode(f"Last: {self.generated}"))
        opts.append(MenuNode("Back", self.exit_app))
        for o in opts:
            root.add_child(o)
        self.menu = MenuSystem(root, self.speak)

    def _adjust_length(self):
        opts = [8, 12, 16, 20, 24, 32]
        idx = opts.index(self.length) if self.length in opts else 2
        self.length = opts[(idx + 1) % len(opts)]
        self.speak(f"Length {self.length}.")
        self._build_menu()
        self.menu.announce_current()

    def _toggle_upper(self):
        self.use_upper = not self.use_upper
        self.speak(f"Uppercase {'on' if self.use_upper else 'off'}.")
        self._build_menu()
        self.menu.announce_current()

    def _toggle_lower(self):
        self.use_lower = not self.use_lower
        self.speak(f"Lowercase {'on' if self.use_lower else 'off'}.")
        self._build_menu()
        self.menu.announce_current()

    def _toggle_digits(self):
        self.use_digits = not self.use_digits
        self.speak(f"Digits {'on' if self.use_digits else 'off'}.")
        self._build_menu()
        self.menu.announce_current()

    def _toggle_symbols(self):
        self.use_symbols = not self.use_symbols
        self.speak(f"Symbols {'on' if self.use_symbols else 'off'}.")
        self._build_menu()
        self.menu.announce_current()

    def _generate(self):
        pool = ""
        if self.use_upper:
            pool += string.ascii_uppercase
        if self.use_lower:
            pool += string.ascii_lowercase
        if self.use_digits:
            pool += string.digits
        if self.use_symbols:
            pool += "!@#$%^&*()-_=+[]{}|;:,.<>?"

        if not pool:
            self.speak("Enable at least one character type.")
            return

        self.generated = "".join(random.choice(pool) for _ in range(self.length))
        self.speak(f"Generated. {self.generated}")
        self._build_menu()
        self.window.update_text(self.generated)

    def on_focus(self):
        self.speak("Password Generator. Choose options and generate.")
        self.window.update_text("Password Generator")

    def on_key(self, vk):
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
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text(item.title)

    def get_help_text(self):
        return "Password Generator. Choose length and character types, then Generate."
