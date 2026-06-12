import os
import json
import win32con
import tkinter as tk
from tkinter import filedialog
from core.app_base import SoftApp

class TechEdit(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.text = ""
        self.filename = None
        self._tk_root = None

    def _get_tk_root(self):
        if self._tk_root is None:
            self._tk_root = tk.Tk()
            self._tk_root.withdraw()
            self._tk_root.attributes("-topmost", True)
        return self._tk_root

    def on_focus(self):
        self.speak("Word Processor. F1 Save, F2 Save As, F3 Open.")
        self.window.update_text("Tech Edit")

    def save_file(self):
        if not self.filename:
            self.save_as_file()
        else:
            with open(self.filename, 'w') as f:
                json.dump({"text": self.text}, f)
            self.speak("File saved.")

    def save_as_file(self):
        root = self._get_tk_root()
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save File"
        )
        if path:
            self.filename = path
            self.save_file()
            self.speak("File saved as " + os.path.basename(path))

    def open_file(self):
        root = self._get_tk_root()
        path = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Open File"
        )
        if path:
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    self.text = data.get("text", "")
            except (json.JSONDecodeError, IOError):
                self.speak("Failed to open file.")
            self.filename = path
            self.speak("File opened: " + os.path.basename(path))
            self.window.update_text("Editing: " + os.path.basename(path))

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        
        # File Operations
        if vk == win32con.VK_F1:
            self.save_file()
            return
        elif vk == win32con.VK_F2:
            self.save_as_file()
            return
        elif vk == win32con.VK_F3:
            self.open_file()
            return

        if vk == win32con.VK_BACK:
            if self.text:
                self.text = self.text[:-1]
                self.speak("Deleted")
            return

        if vk == win32con.VK_SPACE:
            self.text += " "
            self.speak("Space")
            return

        # Numbers
        if 0x30 <= vk <= 0x39:
            char = chr(vk)
            self.text += char
            self.speak(char)
            return

        # Punctuation
        punctuation = {
            0xBA: ";", 0xBB: "=", 0xBC: ",", 0xBD: "-",
            0xBE: ".", 0xBF: "/", 0xC0: "`",
            0xDB: "[", 0xDC: "\\", 0xDD: "]", 0xDE: "'",
        }
        if vk in punctuation:
            char = punctuation[vk]
            self.text += char
            self.speak(char)
            return

        # Letter input
        if 0x41 <= vk <= 0x5A:
            char = chr(vk).lower()
            self.text += char
            self.speak(char)
