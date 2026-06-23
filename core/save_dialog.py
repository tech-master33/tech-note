import os
import win32con
from core.file_dialog import FileDialog
from core.menu import MenuNode, MenuSystem
from core.config import TECH_SOFT


class SaveDialog(FileDialog):
    def __init__(self, manager, window, callback, start_path=None, default_name="", vk_to_char=None):
        super().__init__(manager, window, self._dummy_callback, start_path)
        self.user_callback = callback
        self.default_name = default_name
        self._input_buf = ""
        self._in_input = False
        self._vk_to_char_func = vk_to_char or (lambda v: None)

    def _dummy_callback(self, path):
        pass

    def start(self):
        self.active = True
        self._show_drives()

    def cancel(self):
        self.active = False
        self.user_callback(None)

    def _show_dir(self):
        try:
            items = self._list_dir(self.current_dir)
        except Exception:
            self.speak("Cannot access folder.")
            self._go_up()
            return
        title = os.path.basename(self.current_dir.rstrip('\\')) or self.current_dir
        if os.path.abspath(self.current_dir) == os.path.abspath(TECH_SOFT):
            title = "Tech-Note"
        root = MenuNode(title)
        root.add_child(MenuNode("Save here...", self._start_input))
        root.add_child(MenuNode("..", lambda: self._go_up()))
        for item in items:
            if item['is_dir']:
                root.add_child(MenuNode(item['name'], lambda i=item: self._enter_dir(i)))
            else:
                root.add_child(MenuNode(item['name'], lambda i=item: self._select_file(i)))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _start_input(self):
        self._in_input = True
        self._input_buf = self.default_name
        self.window.update_text(f"Filename: {self._input_buf}")
        self.speak("Enter filename.")

    def _select_file(self, item):
        self.default_name = item['name']
        self._start_input()

    def _confirm_save(self):
        name = self._input_buf.strip()
        if name:
            path = os.path.join(self.current_dir, name)
            self.active = False
            self.user_callback(path)
        else:
            self.speak("Filename cannot be empty.")

    def on_key(self, vk):
        if not self.active:
            return False

        if self._in_input:
            if vk == win32con.VK_ESCAPE:
                self._in_input = False
                self._show_dir()
                return True
            if vk == win32con.VK_RETURN:
                self._confirm_save()
                return True
            if vk == win32con.VK_BACK:
                if self._input_buf:
                    self._input_buf = self._input_buf[:-1]
                    self.window.update_text(f"Filename: {self._input_buf}")
                return True
            ch = self._vk_to_char_func(vk)
            if ch is not None:
                self._input_buf += ch
                self.window.update_text(f"Filename: {self._input_buf}")
            return True

        return super().on_key(vk)

    def on_key_up(self, vk):
        if not self.active:
            return False
        if self._in_input:
            return True
        return super().on_key_up(vk)
