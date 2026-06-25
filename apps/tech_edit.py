import os
import json
import win32con
import re
from core.app_base import SoftApp
from core.config import TECH_SOFT
from core.file_dialog import FileDialog
from core.save_dialog import SaveDialog
import core.auto_save

try:
    from spellchecker import SpellChecker
    HAS_SPELLCHECK = True
except ImportError:
    HAS_SPELLCHECK = False

STATE_EDIT = 0
STATE_SPELL = 3
STATE_FIND = 4
STATE_REPLACE = 5

class TechEdit(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.text = ""
        self.cursor = 0
        self.filename = None
        self.state = STATE_EDIT
        self.doc_dir = os.path.join(TECH_SOFT, 'documents')
        os.makedirs(self.doc_dir, exist_ok=True)

        self._file_dialog = None
        self._save_dialog = None
        self._spell_misspelled = []
        self._spell_index = 0
        self._spell_suggestions = []
        self._spell_sug_index = 0
        self._spell_sug_active = False
        self._dirty = False
        self._autosave_registered = False
        self._find_query = ""
        self._replace_query = ""
        self._find_results = []
        self._find_index = 0

    def _mark_dirty(self):
        self._dirty = True

    def _get_autosave_name(self):
        if self.filename:
            return f"_autosave_{self.filename}"
        return "_autosave_untitled.json"

    def _do_autosave(self):
        try:
            path = core.auto_save.get_recovery_path(self._get_autosave_name())
            with open(path, 'w') as f:
                json.dump({"text": self.text, "filename": self.filename}, f)
        except Exception:
            pass

    def _clear_autosave(self):
        core.auto_save.clear_recovery(self._get_autosave_name())

    def on_focus(self):
        if not self._autosave_registered:
            self._autosave_registered = True
            core.auto_save.register(
                "tech_edit",
                lambda: self._dirty,
                self._do_autosave,
                interval=30
            )
        if self.state == STATE_EDIT:
            self._update_display()
            self.speak("Word Processor. F1 Save, F2 Save As, F3 Open, F5 Find, F6 Replace, F7 Spell, F8 Count.")

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
        self._file_dialog = FileDialog(self.manager, self.window, self._on_open_file)
        self._file_dialog.start()

    def _enter_save_as_state(self):
        default_name = self.filename or ""
        self._save_dialog = SaveDialog(
            self.manager, self.window, self._on_save_file,
            default_name=default_name, vk_to_char=self._vk_to_char
        )
        self._save_dialog.start()

    def save_file(self):
        if not self.filename:
            self._enter_save_as_state()
        else:
            try:
                with open(os.path.join(self.doc_dir, self.filename), 'w') as f:
                    json.dump({"text": self.text}, f)
                self._clear_autosave()
                self._dirty = False
                self.speak("File saved.")
            except Exception:
                self.speak("Failed to save file.")

    def _on_save_file(self, path):
        self._save_dialog = None
        if not path:
            self.state = STATE_EDIT
            self.on_focus()
            return
        try:
            with open(path, 'w') as f:
                json.dump({"text": self.text}, f)
            self.filename = os.path.basename(path)
            self._clear_autosave()
            self._dirty = False
            self.speak(f"Saved to {path}.")
            self.state = STATE_EDIT
            self._update_display()
        except Exception:
            self.speak("Failed to save file.")
            self.state = STATE_EDIT

    def on_key(self, vk):
        if self._file_dialog and self._file_dialog.active:
            self._file_dialog.on_key(vk)
            return
        if self._save_dialog and self._save_dialog.active:
            self._save_dialog.on_key(vk)
            return
        if self.state == STATE_EDIT:
            self._handle_edit_key(vk)
        elif self.state == STATE_SPELL:
            self._handle_spell_key(vk)
        elif self.state == STATE_FIND:
            self._handle_find_key(vk)
        elif self.state == STATE_REPLACE:
            self._handle_replace_key(vk)

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
        elif vk == win32con.VK_F5:
            self._enter_find()
            return
        elif vk == win32con.VK_F6:
            self._enter_replace()
            return
        elif vk == win32con.VK_F7:
            self._do_spell_check()
            return
        elif vk == win32con.VK_F8:
            self._show_count()
            return

        if vk == win32con.VK_BACK:
            if self.cursor > 0:
                self.text = self.text[:self.cursor - 1] + self.text[self.cursor:]
                self.cursor -= 1
                self._mark_dirty()
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
            self._mark_dirty()
            self._update_display()
            return

        ch = self._vk_to_char(vk)
        if ch:
            self.text = self.text[:self.cursor] + ch + self.text[self.cursor:]
            self.cursor += 1
            self._mark_dirty()
            self._update_display()

    def _on_open_file(self, path):
        self._file_dialog = None
        if path:
            self._load_file(path)
        else:
            self.state = STATE_EDIT
            self.on_focus()

    def _load_file(self, path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                self.text = data.get("text", "")
            self.filename = os.path.basename(path)
            self.cursor = len(self.text)
            self.state = STATE_EDIT
            self._check_recovery()
            self.speak(f"Opened {self.filename}. {len(self.text)} characters.")
            self._update_display()
        except Exception:
            self.speak("Failed to open file.")

    def _check_recovery(self):
        rname = self._get_autosave_name()
        files = core.auto_save.get_recovery_files()
        if rname in files:
            try:
                path = core.auto_save.get_recovery_path(rname)
                with open(path, 'r') as f:
                    data = json.load(f)
                recovered_text = data.get("text", "")
                if recovered_text and recovered_text != self.text:
                    self.text = recovered_text
                    self._dirty = True
                    self.speak("Unsaved changes recovered.")
            except Exception:
                pass

    def _show_count(self):
        chars = len(self.text)
        words = len(self.text.split()) if self.text.strip() else 0
        lines = self.text.count('\n') + 1 if self.text else 0
        self.speak(f"{chars} characters, {words} words, {lines} lines.")

    def _enter_find(self):
        self.state = STATE_FIND
        self._find_query = ""
        self._find_results = []
        self._find_index = 0
        self.speak("Find. Type search text.")
        self.window.update_text("Find: ")

    def _do_find(self):
        q = self._find_query
        if not q:
            self._find_results = []
            self.speak("No search text.")
            return
        self._find_results = [m.start() for m in re.finditer(re.escape(q), self.text)]
        self._find_index = 0
        if self._find_results:
            self.cursor = self._find_results[0]
            self._update_display()
            self.speak(f"Found {len(self._find_results)} matches.")
        else:
            self.speak("No matches.")

    def _next_find(self):
        if not self._find_results:
            return
        self._find_index = (self._find_index + 1) % len(self._find_results)
        self.cursor = self._find_results[self._find_index]
        self._update_display()
        self.speak(f"Match {self._find_index + 1} of {len(self._find_results)}.")

    def _enter_replace(self):
        self.state = STATE_REPLACE
        self._find_query = ""
        self._replace_query = ""
        self._find_results = []
        self._find_index = 0
        self._replace_step = 0
        self.speak("Replace. Type text to find.")
        self.window.update_text("Find: ")

    def _do_replace_find(self):
        q = self._find_query
        if not q:
            self._find_results = []
            self.speak("No search text.")
            return
        self._find_results = [m.start() for m in re.finditer(re.escape(q), self.text)]
        self._find_index = 0
        if self._find_results:
            self.cursor = self._find_results[0]
            self._update_display()
            self.speak(f"Found {len(self._find_results)} matches. Enter replacement text.")
        else:
            self.speak("No matches.")

    def _do_replace_all(self):
        q = self._find_query
        if not q:
            return
        count = self.text.count(q)
        self.text = self.text.replace(q, self._replace_query)
        self.cursor = min(self.cursor, len(self.text))
        self._mark_dirty()
        self._update_display()
        self.speak(f"Replaced {count} occurrence{'s' if count != 1 else ''}.")

    def _handle_find_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.state = STATE_EDIT
            self._update_display()
            self.speak("Find cancelled.")
            return
        if vk == win32con.VK_RETURN:
            self._do_find()
            self.state = STATE_EDIT
            self.speak("Press F5 to find again, or F6 to replace.")
            self._update_display()
            return
        if vk == win32con.VK_F5:
            self._next_find()
            return
        if 0x20 <= vk <= 0x5A or 0x30 <= vk <= 0x39:
            ch = self._vk_to_char(vk)
            if ch:
                self._find_query += ch
                self.window.update_text(f"Find: {self._find_query}")
            return
        if vk == win32con.VK_BACK:
            if self._find_query:
                self._find_query = self._find_query[:-1]
                self.window.update_text(f"Find: {self._find_query}")

    def _handle_replace_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.state = STATE_EDIT
            self._update_display()
            self.speak("Replace cancelled.")
            return
        if self._replace_step == 0:
            if vk == win32con.VK_RETURN:
                self._replace_step = 1
                self._do_replace_find()
                self.window.update_text("Replace with: ")
                return
            if 0x20 <= vk <= 0x5A or 0x30 <= vk <= 0x39:
                ch = self._vk_to_char(vk)
                if ch:
                    self._find_query += ch
                    self.window.update_text(f"Find: {self._find_query}")
                return
            if vk == win32con.VK_BACK:
                if self._find_query:
                    self._find_query = self._find_query[:-1]
                    self.window.update_text(f"Find: {self._find_query}")
        elif self._replace_step == 1:
            if vk == win32con.VK_RETURN:
                self._do_replace_all()
                self.state = STATE_EDIT
                self._update_display()
                return
            if 0x20 <= vk <= 0x5A or 0x30 <= vk <= 0x39:
                ch = self._vk_to_char(vk)
                if ch:
                    self._replace_query += ch
                    self.window.update_text(f"Replace with: {self._replace_query}")
                return
            if vk == win32con.VK_BACK:
                if self._replace_query:
                    self._replace_query = self._replace_query[:-1]
                    self.window.update_text(f"Replace with: {self._replace_query}")

    def is_text_input_active(self):
        return self.state == STATE_EDIT

    def get_help_text(self):
        if self.state == STATE_SPELL:
            if self._spell_sug_active:
                return "Suggestions. Press number 1-9 to select a suggestion. Escape to cancel."
            return "Spell Check. Space for next, Backspace for previous. F8 suggestions, F9 ignore, F7 exit. Escape to cancel."
        if self.state == STATE_FIND:
            return "Find. Type text and press Enter. F5 for next match. Escape to exit."
        if self.state == STATE_REPLACE:
            return "Replace. Enter text to find, then replacement. Escape to cancel."
        return "Word Processor. Type to enter text. Home/End for start/end of line. Left/Right to move cursor. F1 Save, F2 Save As, F3 Open. F5 Find, F6 Replace, F7 Spell, F8 Count. Escape to exit."

    def _do_spell_check(self):
        if not HAS_SPELLCHECK:
            self.speak("Spell check requires pyspellchecker.")
            return
        if not self.text.strip():
            self.speak("No text to check.")
            return
        self.speak("Checking spelling.")
        try:
            spell = SpellChecker()
            words = self.text.split()
            if not words:
                self.speak("No words to check.")
                return
            unique_misspelled = spell.unknown(set(words))
            seen = set()
            self._spell_misspelled = []
            idx = 0
            for w in words:
                next_idx = self.text.find(w, idx)
                if next_idx == -1:
                    next_idx = idx
                if w in unique_misspelled and w.lower() not in seen:
                    seen.add(w.lower())
                    self._spell_misspelled.append((w, next_idx))
                idx = next_idx + len(w)
            if not self._spell_misspelled:
                self.speak("No misspelled words found.")
                return
            self._spell_sug_active = False
            self._spell_index = 0
            self.state = STATE_SPELL
            count = len(self._spell_misspelled)
            self.speak(f"{count} misspelled word{'s' if count != 1 else ''} found.")
            self._announce_spell_word()
        except Exception:
            self.speak("Spell check failed.")

    def _announce_spell_word(self):
        if not self._spell_misspelled:
            return
        word, pos = self._spell_misspelled[self._spell_index]
        total = len(self._spell_misspelled)
        self.cursor = pos
        self._spell_sug_active = False
        self._update_display()
        self.speak(f"Misspelled: {word}. Word {self._spell_index + 1} of {total}.")

    def _replace_spell_word(self, replacement):
        word, pos = self._spell_misspelled[self._spell_index]
        self.text = self.text[:pos] + replacement + self.text[pos + len(word):]
        self.cursor = pos + len(replacement)
        self._mark_dirty()
        idx = self._spell_index
        self._spell_misspelled.pop(idx)
        if not self._spell_misspelled:
            self.state = STATE_EDIT
            self.speak("No more misspelled words.")
            self._update_display()
            return
        self._spell_index = min(idx, len(self._spell_misspelled) - 1)
        self._announce_spell_word()

    def _spell_show_suggestions(self):
        word, _ = self._spell_misspelled[self._spell_index]
        try:
            spell = SpellChecker()
            corr = spell.correction(word)
            cands = spell.candidates(word)
            if cands:
                try:
                    sorted_cands = sorted(cands, key=lambda c: -spell.word_usage_frequency(c))[:9]
                except Exception:
                    sorted_cands = sorted(cands)[:9]
                self._spell_suggestions = sorted_cands
                self._spell_sug_active = True
                labels = [f"{i+1}. {s}" for i, s in enumerate(sorted_cands)]
                if corr and corr in sorted_cands:
                    idx = sorted_cands.index(corr)
                    labels[idx] = f"{idx+1}. {corr} (best)"
                self.speak("Suggestions: " + ", ".join(labels))
                self.window.update_text(" | ".join(labels))
            else:
                self.speak("No suggestions available.")
        except Exception:
            self.speak("Failed to get suggestions.")

    def _handle_spell_key(self, vk):
        if self._spell_sug_active:
            if 0x31 <= vk <= 0x39:
                idx = vk - 0x31
                if idx < len(self._spell_suggestions):
                    self._replace_spell_word(self._spell_suggestions[idx])
                return
            if vk == win32con.VK_ESCAPE:
                self._spell_sug_active = False
                self._announce_spell_word()
            return

        if vk == win32con.VK_ESCAPE:
            self.state = STATE_EDIT
            self.speak("Spell check cancelled.")
            self._update_display()
            return
        if vk == win32con.VK_BACK:
            self._spell_index = (self._spell_index - 1) % len(self._spell_misspelled)
            self._announce_spell_word()
            return
        if vk == win32con.VK_F8:
            self._spell_show_suggestions()
            return
        if vk == win32con.VK_F9:
            idx = self._spell_index
            self._spell_misspelled.pop(idx)
            if not self._spell_misspelled:
                self.state = STATE_EDIT
                self.speak("No more misspelled words.")
                self._update_display()
                return
            self._spell_index = min(idx, len(self._spell_misspelled) - 1)
            self._announce_spell_word()
            return
        if vk == win32con.VK_F7:
            self.state = STATE_EDIT
            self.speak("Spell check done.")
            self._update_display()
            return

    def on_key_up(self, vk):
        if self._file_dialog and self._file_dialog.active:
            self._file_dialog.on_key_up(vk)
            return
        if self._save_dialog and self._save_dialog.active:
            self._save_dialog.on_key_up(vk)
            return
        if self.state == STATE_SPELL:
            if self._spell_sug_active:
                return
            if vk == win32con.VK_SPACE:
                if getattr(self.manager, 'space_used_in_chord', False):
                    return
                self._spell_index = (self._spell_index + 1) % len(self._spell_misspelled)
                self._announce_spell_word()
            return

        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            if self.state == STATE_EDIT:
                self.text = self.text[:self.cursor] + ' ' + self.text[self.cursor:]
                self.cursor += 1
                self._mark_dirty()
                self._update_display()
