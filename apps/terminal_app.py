import win32con
from core.app_base import SoftApp
from core.command_registry import get_command_registry


class TerminalApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._history = []
        self._history_index = -1
        self._pending = ""
        self._last_result = ""
        self._start_text_input("Command:", self._on_command, initial="")

    def on_focus(self):
        self._announce("Terminal. Type a command and press enter.")

    def on_key(self, vk):
        if vk == win32con.VK_UP:
            if self._history:
                current = getattr(self, '_input_buf', '')
                if self._history_index < 0:
                    self._pending = current
                new_idx = min(self._history_index + 1, len(self._history) - 1)
                if new_idx != self._history_index:
                    self._history_index = new_idx
                    self._input_buf = self._history[-(new_idx + 1)]
                    self.speak(self._input_buf)
                    self.window.update_text(f"Command: {self._input_buf}")
            return
        if vk == win32con.VK_DOWN:
            if self._history_index >= 0:
                self._history_index -= 1
                if self._history_index < 0:
                    self._history_index = -1
                    self._input_buf = self._pending if self._pending else ""
                else:
                    self._input_buf = self._history[-(self._history_index + 1)]
                self.speak(self._input_buf if self._input_buf else "blank")
                self.window.update_text(f"Command: {self._input_buf}")
            return
        if vk == win32con.VK_F1:
            result = get_command_registry().execute("help")
            self.speak(result)
            self._last_result = result
            self.window.update_text(result)
            return
        super().on_key(vk)

    def _on_command(self, cmd_text):
        if cmd_text:
            self._history.append(cmd_text)
            if len(self._history) > 50:
                self._history.pop(0)
            self._history_index = -1
            self._pending = ""
            result = get_command_registry().execute(cmd_text)
            if result:
                self.speak(result)
                self._last_result = result
                self.window.update_text(result)
            else:
                self._last_result = ""
                self.window.update_text("")
        self._start_text_input("Command:", self._on_command, initial="")
        self.window.update_text("Command:")

    def get_help_text(self):
        return "Terminal: type commands and press Enter. Up/Down for history. F1 for command list. Escape to exit."