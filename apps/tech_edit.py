import os
import json
import win32con
import win32api
from core.app_base import SoftApp
from core.config import TECH_SOFT

STATE_EDIT = 0
STATE_OPEN = 1
STATE_SAVE_AS = 2

class TechEdit(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.text = ""
        self.filename = None
        self.state = STATE_EDIT
        self.doc_dir = os.path.join(TECH_SOFT, 'documents')
        os.makedirs(self.doc_dir, exist_ok=True)
        
        # For Open dialog
        self.file_list = []
        self.file_index = 0
        
        # For Save As dialog
        self.input_buf = ""

    def on_focus(self):
        if self.state == STATE_EDIT:
            self.speak("Word Processor. F1 Save, F2 Save As, F3 Open.")
            self.window.update_text("Tech Edit")
        elif self.state == STATE_OPEN:
            self._enter_open_state()
        elif self.state == STATE_SAVE_AS:
            self._enter_save_as_state()

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
            except Exception as e:
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
            if self.text:
                self.text = self.text[:-1]
                # Optional: speak the deleted character or "Deleted"
                self.speak("Deleted")
            return

        if vk == win32con.VK_SPACE:
            self.text += " "
            self.speak("Space")
            return

        # Simple text input for demo (can be expanded)
        ch = self._vk_to_char(vk)
        if ch:
            self.text += ch
            self.speak(ch)

    def _handle_open_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.state = STATE_EDIT
            self.on_focus()
            return

        if not self.file_list:
            return

        if vk in (win32con.VK_SPACE):
            self.file_index = (self.file_index + 1) % len(self.file_list)
            self._announce_file()
        elif vk in (win32con.VK_BACK):
            self.file_index = (self.file_index - 1) % len(self.file_list)
            self._announce_file()
        elif vk == win32con.VK_RETURN:
            filename = self.file_list[self.file_index]
            self._load_file(filename)

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
            self.state = STATE_EDIT
            self.speak(f"Opened {filename}")
            self.window.update_text(f"Editing: {filename}")
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

    def _vk_to_char(self, vk):
        shift = win32api.GetAsyncKeyState(win32con.VK_SHIFT) & 0x8000
        caps = win32api.GetAsyncKeyState(win32con.VK_CAPITAL) & 1
        if 0x41 <= vk <= 0x5A:
            upper = shift ^ caps
            return chr(vk).upper() if upper else chr(vk).lower()
        if 0x30 <= vk <= 0x39:
            shift_syms = {0x30: ')', 0x31: '!', 0x32: '@', 0x33: '#',
                          0x34: '$', 0x35: '%', 0x36: '^', 0x37: '&',
                          0x38: '*', 0x39: '('}
            return shift_syms[vk] if shift else chr(vk)
        if vk == win32con.VK_SPACE:
            return ' '
        sym_map = {
            0xBD: ('-', '_'), 0xBB: ('=', '+'), 0xC0: ('`', '~'),
            0xDB: ('[', '{'), 0xDD: (']', '}'), 0xDC: ('\\', '|'),
            0xBA: (';', ':'), 0xDE: ("'", '"'),
            0xBC: (',', '<'), 0xBE: ('.', '>'), 0xBF: ('/', '?'),
        }
        if vk in sym_map:
            return sym_map[vk][1] if shift else sym_map[vk][0]
        return None

    def get_help_text(self):
        return "Word Processor. Type to enter text. F1 to Save, F2 for Save As, F3 to Open. Press Escape to exit."
