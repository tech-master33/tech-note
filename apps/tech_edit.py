import os
import json
import win32api
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

SPELL_LANGUAGES = ["en", "es", "fr", "de", "it", "pt"]
SPELL_LANG_NAMES = {"en": "English", "es": "Spanish", "fr": "French", "de": "German", "it": "Italian", "pt": "Portuguese"}

STATE_EDIT = 0
STATE_SPELL = 3
STATE_FIND = 4
STATE_REPLACE = 5
STATE_DICT_MANAGER = 6
STATE_TEMPLATES = 7
STATE_EXIT_CONFIRM = 8

EXIT_CONFIRM_CHOICES = ["Save and Exit", "Exit Without Saving", "Cancel"]

class TechEdit(SoftApp):
    app_title = "Word Processor"

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
        self._exit_after_save = False
        self._confirm_index = 0
        self._autosave_registered = False
        self._find_query = ""
        self._replace_query = ""
        self._find_results = []
        self._find_index = 0
        self._user_dict_path = os.path.join(TECH_SOFT, 'user_dict.json')
        self._user_dict = self._load_user_dict()
        self._spell_config_path = os.path.join(TECH_SOFT, 'spell_config.json')
        self._spell_language = self._load_spell_language()
        self._dict_list = []
        self._dict_index = 0
        self._add_word_buffer = ""
        self._awaiting_add_word = False
        self._spell_language = self._load_spell_language()
        self._templates_dir = os.path.join(TECH_SOFT, 'templates')
        self._templates = []
        self._template_index = 0
        self._ensure_templates()

    def _mark_dirty(self):
        self._dirty = True

    def is_dirty(self):
        return self._dirty

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
        elif self.state == STATE_EXIT_CONFIRM:
            self._announce_confirm()

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
            self._exit_after_save = False
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
            if self._exit_after_save:
                self._exit_after_save = False
                self.exit_app()
        except Exception:
            self._exit_after_save = False
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
        elif self.state == STATE_DICT_MANAGER:
            self._handle_dict_key(vk)
        elif self.state == STATE_TEMPLATES:
            self._handle_template_key(vk)
        elif self.state == STATE_EXIT_CONFIRM:
            self._handle_exit_confirm_key(vk)

    def _is_ctrl_pressed(self):
        return win32api.GetAsyncKeyState(win32con.VK_CONTROL) & 0x8000

    def _insert_formatting(self, marker):
        self.text = self.text[:self.cursor] + marker + marker + self.text[self.cursor:]
        self.cursor += len(marker)

    def _handle_edit_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            if self._dirty:
                self._enter_exit_confirm()
            else:
                self.exit_app()
            return

        if self._is_ctrl_pressed():
            if vk == 0x42:
                self._insert_formatting("**")
                self._mark_dirty()
                self._update_display()
                self.speak("Bold.")
                return
            if vk == 0x49:
                self._insert_formatting("*")
                self._mark_dirty()
                self._update_display()
                self.speak("Italic.")
                return
            if vk == 0x55:
                self._insert_formatting("__")
                self._mark_dirty()
                self._update_display()
                self.speak("Underline.")
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
        elif vk == win32con.VK_F9:
            self._enter_templates()
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
            line_start = self.text.rfind('\n', 0, self.cursor)
            if line_start == -1:
                line_start = 0
            else:
                line_start += 1
            leading = self.text[line_start:self.cursor]
            indent = leading[:len(leading) - len(leading.lstrip())]
            self.text = self.text[:self.cursor] + '\n' + indent + self.text[self.cursor:]
            self.cursor += 1 + len(indent)
            self._mark_dirty()
            self._update_display()
            return

        ch = self._vk_to_char(vk)
        if ch:
            self.text = self.text[:self.cursor] + ch + self.text[self.cursor:]
            self.cursor += 1
            self._mark_dirty()
            self._update_display()

    def _enter_exit_confirm(self):
        self.state = STATE_EXIT_CONFIRM
        self._confirm_index = 0
        self._announce_confirm()

    def _announce_confirm(self):
        choice = EXIT_CONFIRM_CHOICES[self._confirm_index]
        pos = self._confirm_index + 1
        total = len(EXIT_CONFIRM_CHOICES)
        self.speak(f"Unsaved changes. {choice}. {pos} of {total}. Enter to select, Escape to cancel.")
        self.window.update_text(f"Unsaved changes: {choice}")

    def _cancel_exit_confirm(self):
        self._exit_after_save = False
        self.state = STATE_EDIT
        self._update_display()
        self.speak("Canceled.")

    def _handle_exit_confirm_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self._cancel_exit_confirm()
            return
        if vk == win32con.VK_RETURN:
            self._select_exit_confirm_option()
            return
        if vk in (win32con.VK_DOWN, win32con.VK_RIGHT):
            self._confirm_index = (self._confirm_index + 1) % len(EXIT_CONFIRM_CHOICES)
            self._announce_confirm()
            return
        if vk in (win32con.VK_UP, win32con.VK_LEFT):
            self._confirm_index = (self._confirm_index - 1) % len(EXIT_CONFIRM_CHOICES)
            self._announce_confirm()
            return
        if 0x31 <= vk <= 0x33:
            self._confirm_index = vk - 0x31
            self._select_exit_confirm_option()

    def _select_exit_confirm_option(self):
        choice = EXIT_CONFIRM_CHOICES[self._confirm_index]
        if choice == "Save and Exit":
            self._exit_after_save = True
            self.save_file()
            if self._save_dialog:
                return
            if not self._dirty:
                self.exit_app()
            else:
                self._cancel_exit_confirm()
        elif choice == "Exit Without Saving":
            self._exit_after_save = False
            self.exit_app()
        else:
            self._cancel_exit_confirm()

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
        self._find_regex = False
        self.speak("Find. Type search text.")
        self.window.update_text("Find: ")

    def _do_find(self):
        q = self._find_query
        if not q:
            self._find_results = []
            self.speak("No search text.")
            return
        try:
            pattern = q if self._find_regex else re.escape(q)
            self._find_results = [m.start() for m in re.finditer(pattern, self.text)]
        except re.error:
            self._find_results = []
            self.speak("Invalid regex.")
            return
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
        self._find_regex = False
        self.speak("Replace. Type text to find.")
        self.window.update_text("Find: ")

    def _do_replace_find(self):
        q = self._find_query
        if not q:
            self._find_results = []
            self.speak("No search text.")
            return
        try:
            pattern = q if self._find_regex else re.escape(q)
            self._find_results = [m.start() for m in re.finditer(pattern, self.text)]
        except re.error:
            self._find_results = []
            self.speak("Invalid regex.")
            return
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
        if self._find_regex:
            try:
                self.text = re.sub(q, self._replace_query, self.text)
                count = self.text.count(self._replace_query)
            except re.error:
                self.speak("Invalid regex.")
                return
        else:
            count = self.text.count(q)
            self.text = self.text.replace(q, self._replace_query)
        self.cursor = min(self.cursor, len(self.text))
        self._mark_dirty()
        self._update_display()
        self.speak(f"Replaced {count} occurrence{'s' if count != 1 else ''}.")

    def _enter_templates(self):
        self._load_template_list()
        if not self._templates:
            self.speak("No templates available.")
            return
        self._template_index = 0
        self.state = STATE_TEMPLATES
        name = self._templates[0].replace('.json', '').title()
        self.speak(f"Templates. {name}.")
        self.window.update_text(f"Template: {name}")

    def _handle_template_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.state = STATE_EDIT
            self._update_display()
            self.speak("Templates cancelled.")
            return
        if vk == win32con.VK_SPACE or vk == win32con.VK_RIGHT:
            self._template_index = (self._template_index + 1) % len(self._templates)
            name = self._templates[self._template_index].replace('.json', '').title()
            self.speak(name)
            self.window.update_text(f"Template: {name}")
            return
        if vk == win32con.VK_BACK or vk == win32con.VK_LEFT:
            self._template_index = (self._template_index - 1) % len(self._templates)
            name = self._templates[self._template_index].replace('.json', '').title()
            self.speak(name)
            self.window.update_text(f"Template: {name}")
            return
        if vk == win32con.VK_RETURN:
            self._apply_template(self._template_index)

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
        if vk == win32con.VK_F9:
            self._find_regex = not self._find_regex
            mode = "regex" if self._find_regex else "plain text"
            self.speak(f"Find mode: {mode}.")
            self.window.update_text(f"Find ({mode}): {self._find_query}")
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
        if vk == win32con.VK_F9:
            self._find_regex = not self._find_regex
            mode = "regex" if self._find_regex else "plain text"
            self.speak(f"Replace mode: {mode}.")
            step_label = "Find" if self._replace_step == 0 else "Replace with"
            self.window.update_text(f"{step_label} ({mode}): ")
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
                return "Suggestions. Press number 1-9 to select a suggestion. 0 to replace all. Escape to cancel."
            return f"Spell Check. Space for next, Backspace for previous. F8 suggestions, F9 add to dictionary, F10 dictionary, F11 language ({SPELL_LANG_NAMES[self._spell_language]}), F7 exit. Escape to cancel."
        if self.state == STATE_FIND:
            return f"Find. Type text and press Enter. F5 for next match. F9 toggle regex ({'on' if self._find_regex else 'off'}). Escape to exit."
        if self.state == STATE_REPLACE:
            return f"Replace. Enter text to find, then replacement. F9 toggle regex ({'on' if self._find_regex else 'off'}). Escape to cancel."
        if self.state == STATE_DICT_MANAGER:
            if self._awaiting_add_word:
                return "Type a word and press Enter to add. F9 to clear and restart. Escape to cancel."
            return "User Dictionary. Space and Backspace to browse. F8 remove word, F9 add word, F10 clear all, Escape to close."
        if self.state == STATE_TEMPLATES:
            return f"Templates ({self._template_index + 1} of {len(self._templates)}). Space and Backspace to browse. Enter to use. Escape to cancel."
        if self.state == STATE_EXIT_CONFIRM:
            return "Unsaved changes. Space and Backspace to choose. Enter to select. Escape to cancel."
        return "Word Processor. Type to enter text. Home/End for start/end of line. Left/Right to move cursor. Ctrl+B Bold, Ctrl+I Italic, Ctrl+U Underline. F1 Save, F2 Save As, F3 Open. F5 Find, F6 Replace, F7 Spell, F8 Count, F9 Templates. Escape to exit."

    def _load_user_dict(self):
        try:
            if os.path.exists(self._user_dict_path):
                with open(self._user_dict_path, 'r') as f:
                    return set(json.load(f))
        except Exception:
            pass
        return set()

    def _save_user_dict(self):
        try:
            with open(self._user_dict_path, 'w') as f:
                json.dump(sorted(self._user_dict), f)
        except Exception:
            pass

    def _is_in_user_dict(self, word):
        return word.lower() in self._user_dict

    def _add_to_dictionary(self, word):
        self._user_dict.add(word.lower())
        self._save_user_dict()

    def _load_spell_language(self):
        path = os.path.join(TECH_SOFT, 'spell_lang.json')
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    lang = json.load(f)
                if lang in SPELL_LANGUAGES:
                    return lang
        except Exception:
            pass
        return "en"

    def _save_spell_language(self):
        path = os.path.join(TECH_SOFT, 'spell_lang.json')
        try:
            with open(path, 'w') as f:
                json.dump(self._spell_language, f)
        except Exception:
            pass

    def _cycle_spell_language(self):
        idx = SPELL_LANGUAGES.index(self._spell_language)
        self._spell_language = SPELL_LANGUAGES[(idx + 1) % len(SPELL_LANGUAGES)]
        self._save_spell_language()
        self.speak(f"Spell language: {SPELL_LANG_NAMES[self._spell_language]}.")

    def _ensure_templates(self):
        os.makedirs(self._templates_dir, exist_ok=True)
        builtins = {
            "blank.json": "",
            "letter.json": "Dear [Name],\n\n[Body]\n\nSincerely,\n[Your Name]",
            "memo.json": "MEMORANDUM\n\nTo: [Recipient]\nFrom: [Your Name]\nDate: [Date]\nSubject: [Subject]\n\n[Body]",
            "report.json": "Report: [Title]\n\nIntroduction\n\n[Body]\n\nConclusion",
            "todo.json": "To Do\n\n1. \n2. \n3.",
        }
        for name, content in builtins.items():
            path = os.path.join(self._templates_dir, name)
            if not os.path.exists(path):
                try:
                    with open(path, 'w') as f:
                        json.dump({"text": content}, f)
                except Exception:
                    pass

    def _load_template_list(self):
        self._templates = []
        try:
            for fname in sorted(os.listdir(self._templates_dir)):
                if fname.endswith('.json'):
                    self._templates.append(fname)
        except Exception:
            pass
        return self._templates

    def _apply_template(self, index):
        if index < 0 or index >= len(self._templates):
            return
        path = os.path.join(self._templates_dir, self._templates[index])
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            self.text = data.get("text", "")
            self.cursor = 0
            self.filename = None
            self._dirty = False
            self.state = STATE_EDIT
            name = self._templates[index].replace('.json', '').title()
            self.speak(f"{name} template loaded.")
            self._update_display()
        except Exception:
            self.speak("Failed to load template.")

    def _do_spell_check(self):
        if not HAS_SPELLCHECK:
            self.speak("Spell check requires pyspellchecker.")
            return
        if not self.text.strip():
            self.speak("No text to check.")
            return
        self.speak(f"Checking spelling. Language: {SPELL_LANG_NAMES[self._spell_language]}.")
        try:
            spell = SpellChecker(language=self._spell_language)
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
                if w in unique_misspelled and w.lower() not in seen and not self._is_in_user_dict(w):
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

    def _replace_all_spell_word(self, replacement):
        word, _ = self._spell_misspelled[self._spell_index]
        count = self.text.count(word)
        self.text = self.text.replace(word, replacement)
        self._mark_dirty()
        self.state = STATE_EDIT
        self.cursor = min(self.cursor, len(self.text))
        self.speak(f"Replaced {count} occurrence{'s' if count != 1 else ''} with {replacement}.")
        self._update_display()

    def _spell_show_suggestions(self):
        word, _ = self._spell_misspelled[self._spell_index]
        try:
            spell = SpellChecker(language=self._spell_language)
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
                self.speak("0. Replace all. " + ", ".join(labels))
                self.window.update_text("0. Replace all | " + " | ".join(labels))
            else:
                self.speak("No suggestions available.")
        except Exception:
            self.speak("Failed to get suggestions.")

    def _handle_spell_key(self, vk):
        if self._spell_sug_active:
            if vk == 0x30:
                if self._spell_suggestions:
                    self._replace_all_spell_word(self._spell_suggestions[0])
                return
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
            word, _ = self._spell_misspelled[self._spell_index]
            self._add_to_dictionary(word)
            self.speak(f"{word} added to dictionary.")
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
        if vk == win32con.VK_F10:
            self._enter_dict_manager()
            return
        if vk == win32con.VK_F11:
            self._cycle_spell_language()
            return

    def _enter_dict_manager(self):
        self.state = STATE_DICT_MANAGER
        self._dict_list = sorted(self._user_dict)
        self._dict_index = 0
        if self._dict_list:
            self._announce_dict_word()
        else:
            self.speak("Dictionary is empty. Press F9 to add a word.")
            self.window.update_text("User Dictionary - empty")

    def _announce_dict_word(self):
        if not self._dict_list:
            return
        word = self._dict_list[self._dict_index]
        total = len(self._dict_list)
        self.window.update_text(f"Dictionary: {word} ({self._dict_index + 1} of {total})")
        self.speak(f"{word}. Word {self._dict_index + 1} of {total}.")

    def _handle_dict_key(self, vk):
        if vk == win32con.VK_BACK and not self._awaiting_add_word:
            if self._dict_list:
                self._dict_index = (self._dict_index - 1) % len(self._dict_list)
                self._announce_dict_word()
            return
        if self._awaiting_add_word:
            if vk == win32con.VK_F9:
                self._add_word_buffer = ""
                self.window.update_text("Add word: ")
                self.speak("Type a word and press Enter.")
                return
            if vk == win32con.VK_ESCAPE:
                self._awaiting_add_word = False
                if self._dict_list:
                    self._announce_dict_word()
                else:
                    self.speak("Dictionary is empty.")
                    self.window.update_text("User Dictionary - empty")
                return
            if vk == win32con.VK_RETURN:
                word = self._add_word_buffer.strip()
                if word:
                    self._user_dict.add(word.lower())
                    self._save_user_dict()
                    self._dict_list = sorted(self._user_dict)
                    self._dict_index = self._dict_list.index(word.lower())
                    self.speak(f"{word} added to dictionary.")
                    self._awaiting_add_word = False
                    self._announce_dict_word()
                else:
                    self.speak("No word entered.")
                return
            if vk == win32con.VK_BACK:
                if self._add_word_buffer:
                    self._add_word_buffer = self._add_word_buffer[:-1]
                    self.window.update_text(f"Add word: {self._add_word_buffer}")
                return
            ch = self._vk_to_char(vk)
            if ch and ch.isprintable():
                self._add_word_buffer += ch
                self.window.update_text(f"Add word: {self._add_word_buffer}")
            return

        if vk == win32con.VK_ESCAPE:
            self.state = STATE_EDIT
            self.speak("Dictionary closed.")
            self._update_display()
            return
        if vk == win32con.VK_F8:
            if not self._dict_list:
                return
            word = self._dict_list[self._dict_index]
            self._user_dict.discard(word)
            self._save_user_dict()
            self._dict_list.pop(self._dict_index)
            if not self._dict_list:
                self.speak(f"{word} removed. Dictionary is empty.")
                self.window.update_text("User Dictionary - empty")
                return
            self._dict_index = min(self._dict_index, len(self._dict_list) - 1)
            self._announce_dict_word()
            return
        if vk == win32con.VK_F9:
            self._enter_add_to_dict()
            return
        if vk == win32con.VK_F10:
            if not self._dict_list:
                return
            self._user_dict.clear()
            self._save_user_dict()
            self._dict_list = []
            self.speak("Dictionary cleared.")
            self.window.update_text("User Dictionary - empty")
            return

    def _enter_add_to_dict(self):
        self.state = STATE_DICT_MANAGER
        self._add_word_buffer = ""
        self._awaiting_add_word = True
        self.speak("Type a word and press Enter to add to dictionary.")
        self.window.update_text("Add word: ")

    def on_key_up(self, vk):
        if self._file_dialog and self._file_dialog.active:
            self._file_dialog.on_key_up(vk)
            return
        if self._save_dialog and self._save_dialog.active:
            self._save_dialog.on_key_up(vk)
            return
        if self.state == STATE_EXIT_CONFIRM:
            if vk == win32con.VK_SPACE:
                if getattr(self.manager, 'space_used_in_chord', False):
                    return
                self._confirm_index = (self._confirm_index + 1) % len(EXIT_CONFIRM_CHOICES)
                self._announce_confirm()
            elif vk == win32con.VK_BACK:
                self._confirm_index = (self._confirm_index - 1) % len(EXIT_CONFIRM_CHOICES)
                self._announce_confirm()
            return
        if self.state == STATE_DICT_MANAGER:
            if self._awaiting_add_word:
                return
            if vk == win32con.VK_SPACE:
                if getattr(self.manager, 'space_used_in_chord', False):
                    return
                if self._dict_list:
                    self._dict_index = (self._dict_index + 1) % len(self._dict_list)
                    self._announce_dict_word()
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
