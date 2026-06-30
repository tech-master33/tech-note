import win32con
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.clipboard_history import clipboard_history


class ClipboardHistoryApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._build_menu()

    def _build_menu(self):
        root = MenuNode("Clipboard History")
        items = clipboard_history.items
        if not items:
            root.add_child(MenuNode("Clipboard history is empty"))
        else:
            for text in items:
                display = text[:60].replace('\n', ' | ') + ('...' if len(text) > 60 else '')
                root.add_child(MenuNode(display, lambda t=text: self._copy(t)))
            root.add_child(MenuNode("Clear History", lambda: self._clear()))
        self.menu = MenuSystem(root, self.speak)

    def _copy(self, text):
        ok = clipboard_history.copy_to_clipboard(text)
        if ok:
            preview = text[:40].replace('\n', ' ')
            self.speak(f"Copied: {preview}")
        else:
            self.speak("Failed to copy")
        self.exit_app()

    def _clear(self):
        clipboard_history.clear()
        self.speak("Clipboard history cleared")
        self.exit_app()

    def on_focus(self):
        self._build_menu()
        self.menu.announce_current()

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
        self._update_display()

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            self._update_display()

    def _update_display(self):
        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Clipboard: " + item.title)
