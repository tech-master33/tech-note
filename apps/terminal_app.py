import os
import win32con
from core.app_base import SoftApp
from core.command_registry import get_command_registry
from core.config import TECH_SOFT

HISTORY_FILE = os.path.join(TECH_SOFT, 'terminal_history.json')
HISTORY_MAX = 50


class TerminalApp(SoftApp):
    app_id = "terminal"
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._history = self._load_json(HISTORY_FILE, []) or []
        if len(self._history) > HISTORY_MAX:
            self._history = self._history[-HISTORY_MAX:]
        self._history_index = -1
        self._pending = ""
        self._last_result = ""
        self._start_text_input("Command:", self._on_command, initial="")

    def on_focus(self):
        self._announce("Terminal. Type a command and press enter.")

    def on_key(self, vk):
        if vk == win32con.VK_UP:
            if self._history:
                current = self.input_buf
                if self._history_index < 0:
                    self._pending = current
                new_idx = min(self._history_index + 1, len(self._history) - 1)
                if new_idx != self._history_index:
                    self._history_index = new_idx
                    self.input_buf = self._history[-(new_idx + 1)]
                    self.speak(self.input_buf)
                    self.window.update_text(f"Command: {self.input_buf}")
            return
        if vk == win32con.VK_DOWN:
            if self._history_index >= 0:
                self._history_index -= 1
                if self._history_index < 0:
                    self._history_index = -1
                    self.input_buf = self._pending if self._pending else ""
                else:
                    self.input_buf = self._history[-(self._history_index + 1)]
                self.speak(self.input_buf if self.input_buf else "blank")
                self.window.update_text(f"Command: {self.input_buf}")
            return
        if vk == win32con.VK_F1:
            result = get_command_registry().execute("help")
            self.speak(result)
            self._last_result = result
            self.window.update_text(result)
            return
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        if self._handle_text_input(vk):
            return
        super().on_key(vk)

    def _on_command(self, cmd_text):
        cmd = cmd_text.strip()
        if not cmd and self._history:
            # Enter on an empty line re-runs the last command (without re-recording it)
            self._execute_command(self._history[-1], record=False)
        elif cmd:
            self._execute_command(cmd, record=True)
        self._start_text_input("Command:", self._on_command, initial="")
        self.window.update_text("Command:")

    def _execute_command(self, cmd_text, record):
        if record:
            self._history.append(cmd_text)
            if len(self._history) > HISTORY_MAX:
                self._history.pop(0)
            self._save_json(HISTORY_FILE, self._history)
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

    def get_help_text(self):
        return "Terminal: type commands and press Enter. Up/Down for history. F1 for command list. Escape to exit."