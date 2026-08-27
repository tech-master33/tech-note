import os
import datetime
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode
from core.config import TECH_SOFT

NOTES_FILE = os.path.join(TECH_SOFT, "notes.json")


class NotesApp(SoftApp):
    app_id = "notes"
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.notes = self._load_json(NOTES_FILE, [])
        self.editing = False
        self.edit_text = ""
        self.edit_title = ""
        self.current_note = None
        self.input_mode = None
        self.input_buf = ""
        self._filter_tag = None
        self._search_results = None
        self._build_menu()

    def _note_label(self, note):
        title = note.get("title", "Untitled")
        pinned = note.get("pinned", False)
        tags = note.get("tags", [])
        date = note.get("date", "")
        prefix = "★ " if pinned else ""
        tag_str = f" [{', '.join(tags)}]" if tags else ""
        return f"{prefix}{title}{tag_str} ({date})"

    def _all_tags(self):
        tags = set()
        for n in self.notes:
            for t in n.get("tags", []):
                tags.add(t)
        return sorted(tags)

    def _build_menu(self):
        root = MenuNode("Notes")
        root.add_child(MenuNode("New Note", self._new_note))
        shown = []
        for i, note in enumerate(self.notes):
            pinned = note.get("pinned", False)
            tags = note.get("tags", [])
            if self._filter_tag and self._filter_tag not in tags:
                continue
            if self._search_results is not None and i not in self._search_results:
                continue
            shown.append((i, note))
        shown.sort(key=lambda x: (0 if x[1].get("pinned", False) else 1, x[1].get("title", "").lower()))
        for idx, note in shown:
            root.add_child(MenuNode(self._note_label(note), lambda i=idx: self._open_note(i)))
        if self._filter_tag:
            root.add_child(MenuNode(f"[Filter: {self._filter_tag}]", self._clear_filter))
        if not [n for n in shown]:
            root.add_child(MenuNode("No notes"))
        self.menu = MenuSystem(root, self.speak, stop_func=self.stop)

    def _clear_filter(self):
        self._filter_tag = None
        self._build_menu()
        self.menu.announce_current()

    def _new_note(self):
        self.editing = True
        self.edit_title = ""
        self.edit_text = ""
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
        root.add_child(MenuNode("Export TXT", lambda: self._export_note_txt(idx)))
        root.add_child(MenuNode("Back", self._build_menu_back))
        self.menu = MenuSystem(root, self.speak, stop_func=self.stop)
        self.menu.announce_current()

    def _start_edit(self, idx):
        note = self.notes[idx]
        self.editing = True
        self.edit_title = note.get("title", "")
        self.edit_text = note.get("text", "")
        self.speak("Editing note. Type to add text. Enter for new line. Escape to save and exit.")
        self.window.update_text(self.edit_text if self.edit_text else " ")

    def _delete_note(self, idx):
        title = self.notes[idx].get("title", "Note")
        self.notes.pop(idx)
        self._save_json(NOTES_FILE, self.notes)
        self.speak(f"{title} deleted.")
        self._build_menu()
        self.menu.announce_current()

    def _export_note_txt(self, idx):
        if idx >= len(self.notes):
            return
        note = self.notes[idx]
        title = note.get("title", "Untitled")
        text = note.get("text", "")
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)
        path = os.path.join(TECH_SOFT, f"{safe}.txt")
        try:
            with open(path, 'w') as f:
                f.write(f"{title}\n{'=' * len(title)}\n\n{text}")
            self.speak(f"Exported to {safe}.txt")
        except Exception:
            self.speak("Export failed.")

    def _export_all_txt(self):
        try:
            path = os.path.join(TECH_SOFT, "notes_export.txt")
            with open(path, 'w') as f:
                for note in self.notes:
                    f.write(f"# {note.get('title', 'Untitled')}\n")
                    f.write(f"Date: {note.get('date', '')}\n")
                    tags = note.get("tags", [])
                    if tags:
                        f.write(f"Tags: {', '.join(tags)}\n")
                    f.write(f"\n{note.get('text', '')}\n\n---\n\n")
            self.speak(f"Exported {len(self.notes)} notes.")
        except Exception:
            self.speak("Export failed.")

    def _build_menu_back(self):
        self._build_menu()
        self.menu.announce_current()

    def _finish_title(self):
        if not self.edit_title.strip():
            self.edit_title = "Untitled"
        self.speak("Title saved. Now type your note. Press Escape when done.")
        self.window.update_text(self.edit_text if self.edit_text else " ")

    def _finish_edit(self):
        old_data = {}
        if self.current_note is not None and self.current_note < len(self.notes):
            old_data = self.notes[self.current_note]
        note = {
            "title": self.edit_title.strip() or "Untitled",
            "text": self.edit_text,
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "tags": old_data.get("tags", []),
            "pinned": old_data.get("pinned", False),
        }
        if self.current_note is not None:
            self.notes[self.current_note] = note
        else:
            self.notes.append(note)
        self._save_json(NOTES_FILE, self.notes)
        self.editing = False
        self.current_note = None
        self.input_mode = None
        self.speak("Note saved.")
        self._build_menu()
        self.menu.announce_current()

    def _toggle_pin(self):
        item = self.menu.get_current_item()
        if not item or item.title.startswith("New Note") or item.title.startswith("No notes") or item.title.startswith("[Filter"):
            return
        for i, note in enumerate(self.notes):
            if self._note_label(note) == item.title:
                note["pinned"] = not note.get("pinned", False)
                self._save_json(NOTES_FILE, self.notes)
                status = "pinned" if note["pinned"] else "unpinned"
                self.speak(f"{note.get('title', '')} {status}.")
                self._build_menu()
                self.menu.announce_current()
                return

    def _start_search(self):
        self.input_mode = "search"
        self.input_buf = ""
        self._search_results = None
        self._filter_tag = None
        self.speak("Search notes. Type a word to search titles and text.")
        self.window.update_text("Search: ")

    def _do_search(self):
        q = self.input_buf.strip().lower()
        if not q:
            self.speak("No search text.")
            return
        results = []
        for i, note in enumerate(self.notes):
            title = note.get("title", "").lower()
            text = note.get("text", "").lower()
            if q in title or q in text:
                results.append(i)
        if results:
            self._search_results = set(results)
            self.input_mode = None
            self._build_menu()
            self.menu.announce_current()
            self.speak(f"Found {len(results)} notes.")
        else:
            self.speak("No matches.")

    def _cycle_tags(self):
        item = self.menu.get_current_item()
        if not item or item.title.startswith("New Note") or item.title.startswith("No notes") or item.title.startswith("[Filter"):
            return
        for i, note in enumerate(self.notes):
            if self._note_label(note) == item.title:
                tags = self._all_tags()
                if not tags:
                    self.input_mode = "add_tag"
                    self.input_buf = ""
                    self.current_note = i
                    self.speak("No tags exist. Type a tag name.")
                    self.window.update_text("Tag: ")
                    return
                cur_tags = note.get("tags", [])
                available = [t for t in tags if t not in cur_tags]
                if available:
                    note.setdefault("tags", []).append(available[0])
                    self.speak(f"Tagged: {available[0]}")
                elif cur_tags:
                    removed = cur_tags.pop()
                    self.speak(f"Removed tag: {removed}")
                self._save_json(NOTES_FILE, self.notes)
                self._build_menu()
                self.menu.announce_current()
                return

    def _tag_filter_menu(self):
        tags = self._all_tags()
        if not tags:
            self.speak("No tags.")
            return
        root = MenuNode("Filter by Tag")
        for t in tags:
            root.add_child(MenuNode(t, lambda tag=t: self._apply_filter(tag)))
        root.add_child(MenuNode("All Notes", self._clear_filter))
        self.menu = MenuSystem(root, self.speak, stop_func=self.stop)
        self.menu.announce_current()

    def _apply_filter(self, tag):
        self._filter_tag = tag
        self._search_results = None
        self._build_menu()
        self.menu.announce_current()

    def on_focus(self):
        if self.editing:
            self.window.update_text(self.edit_title if not self.edit_text else self.edit_text)
        else:
            self._announce(f"Notes. {len(self.notes)} notes.")

    def on_key(self, vk):
        if self.input_mode and not self.editing:
            self._handle_input(vk)
            return

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
        if vk == win32con.VK_F5:
            self._start_search()
            return
        if vk == win32con.VK_F6:
            self._cycle_tags()
            return
        if vk == win32con.VK_F7:
            self._tag_filter_menu()
            return
        if vk == win32con.VK_F8:
            if self.notes:
                self._export_all_txt()
            else:
                self.speak("No notes to export.")
            return
        if vk == win32con.VK_F9:
            self._toggle_pin()
            return
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        else:
            self._handle_first_letter_nav(vk, self.menu)
        item = self.menu.get_current_item()
        if item:
            self.window.update_text(item.title)

    def _handle_input(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.input_mode = None
            self._build_menu()
            self.menu.announce_current()
            return
        if vk == win32con.VK_RETURN:
            if self.input_mode == "search":
                self.input_mode = None
                self._do_search()
                return
            if self.input_mode == "add_tag":
                tag = self.input_buf.strip()
                if tag:
                    if self.current_note is not None and self.current_note < len(self.notes):
                        self.notes[self.current_note].setdefault("tags", []).append(tag)
                        self._save_json(NOTES_FILE, self.notes)
                        self.speak(f"Tagged: {tag}")
                self.input_mode = None
                self._build_menu()
                self.menu.announce_current()
                return
        if vk == win32con.VK_BACK:
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                self.window.update_text(f"{'Search' if self.input_mode == 'search' else 'Tag'}: {self.input_buf}")
            return
        ch = self._vk_to_char(vk)
        if ch:
            self.input_buf += ch
            self.window.update_text(f"{'Search' if self.input_mode == 'search' else 'Tag'}: {self.input_buf}")

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
        return "Notes. Space/Backspace browse. F5 search, F6 tags, F7 filter by tag, F8 export all, F9 pin/unpin."
