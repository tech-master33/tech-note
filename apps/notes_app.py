import os
import json
import datetime
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode
from core.config import TECH_SOFT

NOTES_FILE = os.path.join(TECH_SOFT, "notes.json")


class NotesApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.notes = self._load_notes()
        self.editing = False
        self.edit_text = ""
        self.edit_title = ""
        self.cursor = 0
        self.current_note = None
        self._build_menu()

    def _load_notes(self):
        if os.path.exists(NOTES_FILE):
            try:
                with open(NOTES_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return []

    def _save_notes(self):
        try:
            os.makedirs(os.path.dirname(NOTES_FILE), exist_ok=True)
            with open(NOTES_FILE, 'w') as f:
                json.dump(self.notes, f, indent=2)
        except:
            pass

    def _build_menu(self):
        root = MenuNode("Notes")
        root.add_child(MenuNode("New Note", self._new_note))
        for i, note in enumerate(self.notes):
            title = note.get("title", f"Note {i+1}")
            preview = note.get("text", "")[:30]
            root.add_child(MenuNode(f"{title}: {preview}", lambda idx=i: self._open_note(idx)))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _new_note(self):
        self.editing = True
        self.edit_title = ""
        self.edit_text = ""
        self.cursor = 0
        self.current_note = None
        self.speak("New note. Type your title, press Enter when done.")
        self.window.update_text("Title: ")

    def _open_note(self, idx):
        if idx >= len(self.notes):
            return
        note = self.notes[idx]
        self.current_note = idx
        root = MenuNode(note.get("title", "Note"))
        root.add_child(MenuNode(f"Text: {note.get('text', '')[:50]}..."))
        root.add_child(MenuNode("Edit", lambda: self._start_edit(idx)))
        root.add_child(MenuNode("Delete", lambda: self._delete_note(idx)))
        root.add_child(MenuNode("Back", self._build_menu_back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _start_edit(self, idx):
        note = self.notes[idx]
        self.editing = True
        self.edit_title = note.get("title", "")
        self.edit_text = note.get("text", "")
        self.cursor = len(self.edit_text)
        self.speak("Editing note. Type to add text. Enter for new line. Escape to save and exit.")
        self.window.update_text(self.edit_text if self.edit_text else " ")

    def _delete_note(self, idx):
        title = self.notes[idx].get("title", "Note")
        self.notes.pop(idx)
        self._save_notes()
        self.speak(f"{title} deleted.")
        self._build_menu()
        self.menu.announce_current()

    def _build_menu_back(self):
        self._build_menu()
        self.menu.announce_current()

    def _finish_title(self):
        if not self.edit_title.strip():
            self.edit_title = "Untitled"
        self.speak("Title saved. Now type your note. Press Escape when done.")
        self.window.update_text(self.edit_text if self.edit_text else " ")

    def _finish_edit(self):
        note = {
            "title": self.edit_title.strip() or "Untitled",
            "text": self.edit_text,
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        if self.current_note is not None:
            self.notes[self.current_note] = note
        else:
            self.notes.append(note)
        self._save_notes()
        self.editing = False
        self.current_note = None
        self.speak("Note saved.")
        self._build_menu()
        self.menu.announce_current()

    def on_focus(self):
        if self.editing:
            self.window.update_text(self.edit_title if not self.edit_text else self.edit_text)
        else:
            self.speak(f"Notes. {len(self.notes)} notes.")
            self.window.update_text(f"{len(self.notes)} notes")

    def on_key(self, vk):
        if self.editing:
            if vk == win32con.VK_ESCAPE:
                if not self.edit_text and not self.edit_title:
                    self.editing = False
                    self._build_menu()
                    self.menu.announce_current()
                elif not self.edit_text:
                    self._finish_title()
                else:
                    self._finish_edit()
                return

            if self.edit_title:
                if vk == win32con.VK_RETURN:
                    self._finish_title()
                    return
                if vk == win32con.VK_BACK:
                    self.edit_title = self.edit_title[:-1]
                    self.window.update_text(f"Title: {self.edit_title}")
                    return
                ch = self._vk_to_char(vk)
                if ch:
                    self.edit_title += ch
                    self.window.update_text(f"Title: {self.edit_title}")
                return

            if vk == win32con.VK_BACK:
                if self.edit_text:
                    self.edit_text = self.edit_text[:-1]
                self.window.update_text(self.edit_text if self.edit_text else " ")
                return
            if vk == win32con.VK_RETURN:
                self.edit_text += "\n"
                self.window.update_text(self.edit_text)
                return
            ch = self._vk_to_char(vk)
            if ch:
                self.edit_text += ch
                self.window.update_text(self.edit_text)
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

        item = self.menu.get_current_item()
        if item:
            self.window.update_text(item.title)

    def on_key_up(self, vk):
        if self.editing:
            return
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text(item.title)

    def get_help_text(self):
        if self.editing:
            return "Type your note. Enter for new line. Escape to save."
        return "Notes. Create and manage notes. Space for next, Backspace for previous."
