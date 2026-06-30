import win32con
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.settings_manager import settings_manager

DEFAULT_BINDINGS = {
    "next_item": "Space",
    "prev_item": "Backspace",
    "select": "Enter",
    "back": "Escape",
    "help": "F1",
    "status": "F5",
    "power_menu": "Backtick",
}

VK_NAMES = {
    8: "Backspace", 9: "Tab", 13: "Enter", 27: "Escape",
    32: "Space", 33: "PageUp", 34: "PageDown", 35: "End", 36: "Home",
    37: "Left", 38: "Up", 39: "Right", 40: "Down",
    112: "F1", 113: "F2", 114: "F3", 115: "F4", 116: "F5",
    117: "F6", 118: "F7", 119: "F8", 120: "F9", 121: "F10",
    122: "F11", 123: "F12",
    0xC0: "Backtick", 0xDF: "Backtick(UK)",
}


def _vk_name(vk):
    return VK_NAMES.get(vk, chr(vk) if 0x41 <= vk <= 0x5A else f"0x{vk:02X}")


class KeyBindingsManagerApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._bindings = dict(settings_manager.get("custom", "key_bindings", {}))
        self._rebind_target = None
        self._build_menu()

    def _build_menu(self):
        root = MenuNode("Key Bindings")
        for action, default_key in DEFAULT_BINDINGS.items():
            bound_keys = self._bindings.get(action, [])
            label = f"{action.replace('_', ' ').title()}: {_vk_name(bound_keys[0]) if bound_keys else default_key}"
            root.add_child(MenuNode(label, lambda a=action: self._start_rebind(a)))
        root.add_child(MenuNode("Reset to Defaults", lambda: self._reset()))
        self.menu = MenuSystem(root, self.speak)

    def _start_rebind(self, action):
        self._rebind_target = action
        self.speak(f"Press new key for {action}")

    def on_focus(self):
        self._build_menu()
        self.menu.announce_current()

    def on_key(self, vk):
        if self._rebind_target:
            if vk == win32con.VK_ESCAPE:
                self._rebind_target = None
                self.speak("Cancelled")
                return
            self._bindings[self._rebind_target] = [vk]
            settings_manager.set("custom", "key_bindings", self._bindings)
            settings_manager.save()
            name = _vk_name(vk)
            self.speak(f"{self._rebind_target.replace('_', ' ')} bound to {name}")
            self._rebind_target = None
            self._build_menu()
            self.menu.announce_current()
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
        self._update_display()

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            self._update_display()

    def _reset(self):
        self._bindings = {}
        settings_manager.set("custom", "key_bindings", {})
        settings_manager.save()
        self.speak("Key bindings reset to defaults")
        self._build_menu()
        self.menu.announce_current()

    def _update_display(self):
        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Bindings: " + item.title)
