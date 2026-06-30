import os
import json
import win32con
from core.app_base import SoftApp
from core.command_registry import get_command_registry
from core.config import TECH_SOFT

HISTORY_FILE = os.path.join(TECH_SOFT, "terminal_history.json")


class TerminalApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._history = self._load_history()
        self._history_index = -1
        self._pending = ""
        self._last_result = ""
        self._tab_matches = []
        self._tab_index = 0
        self._start_text_input("Command:", self._on_command, initial="")

    def _load_history(self):
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r') as f:
                    return json.load(f)
        except:
            pass
        return []

    def _save_history(self):
        try:
            os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
            with open(HISTORY_FILE, 'w') as f:
                json.dump(self._history[-200:], f)
        except:
            pass

    def on_focus(self):
        self._announce("Terminal. Type a command and press enter.")

    def on_key(self, vk):
        if vk == win32con.VK_TAB:
            self._do_tab_complete()
            return

        self._tab_matches = []

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
        super().on_key(vk)

    def _do_tab_complete(self):
        buf = getattr(self, '_input_buf', '')
        if not buf:
            return
        if not self._tab_matches:
            registry = get_command_registry()
            names = registry.list_commands() if hasattr(registry, 'list_commands') else []
            if not names:
                names = ["help", "time", "date", "echo", "calc", "weather", "news", "define", "joke", "fact"]
            self._tab_matches = [n for n in names if n.startswith(buf.lower())]
            self._tab_matches.sort()
            self._tab_index = 0
        if self._tab_matches:
            match = self._tab_matches[self._tab_index % len(self._tab_matches)]
            self._tab_index += 1
            self._input_buf = match
            self.speak(match)
            self.window.update_text(f"Command: {match}")

    def _on_command(self, cmd_text):
        if cmd_text:
            self._history.append(cmd_text)
            self._save_history()
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
        return "Terminal: type commands and press Enter. Up/Down for history. Tab for auto-complete. Escape to exit."
