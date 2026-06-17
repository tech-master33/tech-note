import os
import json
import win32con
from core.app_base import SoftApp
from core.config import TECH_SOFT

STATE_EDIT = 0
STATE_OPEN = 1
STATE_SAVE_AS = 2

class TechEdit(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.text = ""
        self.cursor = 0
        self.filename = None
        self.state = STATE_EDIT
        self.doc_dir = os.path.join(TECH_SOFT, 'documents')
        os.makedirs(self.doc_dir, exist_ok=True)
        
        self.file_list = []
        self.file_index = 0
        self.input_buf = ""

    def on_focus(self):
        if self.state == STATE_EDIT:
            self._update_display()
            self.speak("Word Processor. F1 Save, F2 Save As, F3 Open.")
        elif self.state == STATE_OPEN:
            self._enter_open_state()
        elif self.state == STATE_SAVE_AS:
            self._enter_save_as_state()

    def _update_display(self):
        if not self.text:
            self.window.update_text("Word Processor - Empty document")
            return
        before = self.text[:self.cursor]
        at_cursor = self.text[self.cursor] if self.cursor < len(self.text) else " "
        after = self.text[self.cursor + 1:]
        display = f"{before}[{at_cursor}]{after}"
        lines = display.count('\n') + 1
        pos = f"Line {lines}, Col {len(before.split(chr(10))[-1]) + 1}"
        self.window.update_text(f"{pos} - {display}")

    def _enter_open_state(self):
        self.state = STATE_OPEN
        self.file_list = sorted([f for f in os.listdir(self.doc_dir) if f.endswith('.json')])
        self.file_index = 0
        if not self.file_list:
            self.speak("No files found. Press Escape to return.")
            self.window.update_text("Open: No files")
        else:
            self.speak(f"Open file. {self.file_list[0]}")
            self.window.update_text(f"Open: {self.file_list[0]}")

    def _enter_save_as_state(self):
        self.state = STATE_SAVE_AS
        self.input_buf = ""
        self.speak("Save as. Enter filename.")
        self.window.update_text("Save As:")

    def save_file(self):
        if not self.filename:
            self._enter_save_as_state()
        else:
            try:
                with open(os.path.join(self.doc_dir, self.filename), 'w') as f:
                    json.dump({"text": self.text}, f)
                self.speak("File saved.")
            except Exception:
                self.speak("Failed to save file.")

    def on_key(self, vk):
        if self.state == STATE_EDIT:
            self._handle_edit_key(vk)
        elif self.state == STATE_OPEN:
            self._handle_open_key(vk)
        elif self.state == STATE_SAVE_AS:
            self._handle_save_as_key(vk)

    def _handle_edit_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        
        if vk == win32con.VK_F1:
            self.save_file()
            return
        elif vk == win32con.VK_F2:
            self._enter_save_as_state()
            return
        elif vk == win32con.VK_F3:
            self._enter_open_state()
            return

        if vk == win32con.VK_BACK:
            if self.cursor > 0:
                self.text = self.text[:self.cursor - 1] + self.text[self.cursor:]
                self.cursor -= 1
                self._update_display()
            return

        if vk == win32con.VK_HOME:
            self.cursor = 0
            self._update_display()
            return

        if vk == win32con.VK_END:
            self.cursor = len(self.text)
            self._update_display()
            return

        if vk == win32con.VK_LEFT:
            if self.cursor > 0:
                self.cursor -= 1
                self._update_display()
            return

        if vk == win32con.VK_RIGHT:
            if self.cursor < len(self.text):
                self.cursor += 1
                self._update_display()
            return

        if vk == win32con.VK_RETURN:
            self.text = self.text[:self.cursor] + '\n' + self.text[self.cursor:]
            self.cursor += 1
            self._update_display()
            return

        ch = self._vk_to_char(vk)
        if ch:
            self.text = self.text[:self.cursor] + ch + self.text[self.cursor:]
            self.cursor += 1
            self._update_display()

    def _handle_open_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.state = STATE_EDIT
            self.on_focus()
            return

        if not self.file_list:
            return

        if vk == win32con.VK_BACK:
            self.file_index = (self.file_index - 1) % len(self.file_list)
            self._announce_file()
        elif vk == win32con.VK_RETURN:
            filename = self.file_list[self.file_index]
            self._load_file(filename)

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if self.manager.space_used_in_chord:
                return
            
            if self.state == STATE_EDIT:
                self.text = self.text[:self.cursor] + ' ' + self.text[self.cursor:]
                self.cursor += 1
                self._update_display()
            elif self.state == STATE_OPEN:
                if self.file_list:
                    self.file_index = (self.file_index + 1) % len(self.file_list)
                    self._announce_file()

    def _announce_file(self):
        f = self.file_list[self.file_index]
        self.speak(f)
        self.window.update_text(f"Open: {f}")

    def _load_file(self, filename):
        try:
            with open(os.path.join(self.doc_dir, filename), 'r') as f:
                data = json.load(f)
                self.text = data.get("text", "")
            self.filename = filename
            self.cursor = len(self.text)
            self.state = STATE_EDIT
            self.speak(f"Opened {filename}. {len(self.text)} characters.")
            self._update_display()
        except Exception:
            self.speak("Failed to open file.")

    def _handle_save_as_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.state = STATE_EDIT
            self.on_focus()
            return

        if vk == win32con.VK_RETURN:
            if not self.input_buf.strip():
                self.speak("Filename cannot be empty.")
                return
            filename = self.input_buf.strip()
            if not filename.endswith('.json'):
                filename += '.json'
            self.filename = filename
            self.state = STATE_EDIT
            self.save_file()
            return

        if vk == win32con.VK_BACK:
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                self.window.update_text(f"Save As: {self.input_buf}")
            return

        ch = self._vk_to_char(vk)
        if ch:
            self.input_buf += ch
            self.window.update_text(f"Save As: {self.input_buf}")
            self.speak(ch)

    def get_help_text(self):
        return "Word Processor. Type to enter text. Home/End for start/end of line. Left/Right to move cursor. F1 Save, F2 Save As, F3 Open. Escape to exit."
