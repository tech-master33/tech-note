import os
import json
import win32con
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.config import SETTINGS_PATH, ACCOUNT_PATH
from synths.registry import get_available_synths
import core.error_handler
import core.pronunciation_dict

class OptionsApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.adjust_mode = None
        self._text_input_field = None
        self._text_input_buf = ""
        self.pav_submode = None
        self._current_parent_back = None
        self._numeric_key = None
        self._numeric_min = None
        self._numeric_max = None
        self.settings_file = SETTINGS_PATH
        self.settings = {
            "rate": 0, "volume": 100, "voice_index": 0,
            "punctuation_level": "Some",
            "pitch": 50,
            "capital_pitch_change": "Off",
            "char_echo": "Off",
            "word_echo": "Off",
            "announce_position": "On",
            "state_keys": "Off",
            "volume_ducking": "Off",
            "sound_scheme": "Default",
            "language_auto_switch": "Off",
            "voice_profiles": {},
            "per_app_voice": {},
            "speech_history_size": 50,
            "braille_display": "Off",
            "braille_grade": 2
        }
        self._load_voice_settings()
        self._build_main_menu()

    def _build_main_menu(self):
        root = MenuNode("Options")

        tts = root.add_child(MenuNode("TTS Menu"))
        tts.add_child(MenuNode("TTS Engine", self._enter_tts_engine_menu))
        tts.add_child(MenuNode("Speech Rate", self._enter_rate_menu))
        tts.add_child(MenuNode("Volume", self._enter_volume_menu))
        tts.add_child(MenuNode("Voice Selection", self._enter_voice_menu))
        tts.add_child(MenuNode("Punctuation Level", self._enter_punctuation_menu))
        tts.add_child(MenuNode("Pitch", self._enter_pitch_menu))
        tts.add_child(MenuNode("Capital Pitch Change", self._enter_capital_pitch_menu))
        tts.add_child(MenuNode("Language Auto-Switch", self._enter_language_switch_menu))
        tts.add_child(MenuNode("Voice Profiles", self._enter_voice_profiles))
        tts.add_child(MenuNode("Per-App Voices", self._enter_per_app_voices))
        tts.add_child(MenuNode("Pronunciation Dictionary", self._enter_pronunciation_dict))
        tts.add_child(MenuNode("Speech History Size", self._enter_history_size_menu))

        kb = root.add_child(MenuNode("Keyboard Menu"))
        kb.add_child(MenuNode("Character Echo", self._enter_char_echo_menu))
        kb.add_child(MenuNode("Word Echo", self._enter_word_echo_menu))
        kb.add_child(MenuNode("Position Announcement", self._enter_announce_position_menu))
        kb.add_child(MenuNode("State Keys", self._enter_state_keys_menu))
        kb.add_child(MenuNode("Key Bindings", self._enter_key_bindings))

        audio = root.add_child(MenuNode("Audio Menu"))
        audio.add_child(MenuNode("Volume Ducking", self._enter_volume_ducking_menu))
        audio.add_child(MenuNode("Sound Scheme", self._enter_sound_scheme_menu))

        braille = root.add_child(MenuNode("Braille Menu"))
        braille.add_child(MenuNode("Braille Display", self._enter_braille_display_menu))
        braille.add_child(MenuNode("Braille Grade", self._enter_braille_grade_menu))

        self.menu = MenuSystem(root, self.speak)

    def on_focus(self):
        item = self.menu.get_current_item()
        title = item.title if item else "Options"
        self.speak("Options. " + title)
        self.window.update_text("Options: " + title)

    def on_key(self, vk):
        if self.adjust_mode == "key_bind":
            self._handle_key_bind(vk)
            return
        if self.adjust_mode == "text_input":
            self._handle_text_input(vk)
            return
        if self.adjust_mode == "numeric_input":
            self._handle_numeric_input(vk)
            return
        if self.adjust_mode == "pav_numeric":
            self._handle_pav_numeric(vk)
            return

        if vk == win32con.VK_ESCAPE:
            if self.menu.current_node.parent:
                self.menu.back()
            else:
                self.exit_app()
            return

        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            char = chr(vk)
            self.menu.first_letter_nav(char)

        item = self.menu.get_current_item()
        if item:
            self.window.update_text(item.title)

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            if self.adjust_mode:
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text(item.title)

    def get_help_text(self):
        if self.adjust_mode == "key_bind":
            return "Key binding. Press the key you want to assign. Escape to cancel."
        if self.adjust_mode == "numeric_input":
            return f"Enter a value between {self._numeric_min} and {self._numeric_max}. Type the number and press Enter. Escape to cancel."
        return "Options. Navigate with Space and Backspace. Enter to select. Escape to go back or exit."

    def _load_voice_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    loaded = json.load(f)
                self.settings.update(loaded)
                if "rate" in loaded:
                    self.manager.synth.set_rate(self.settings["rate"])
                if "volume" in loaded:
                    self.manager.synth.set_volume(self.settings["volume"])
                if "voice_index" in loaded:
                    names = self.manager.synth.get_voice_names()
                    v_idx = self.settings["voice_index"]
                    if 0 <= v_idx < len(names):
                        self.manager.synth.set_voice_by_index(v_idx)
                if "punctuation_level" in loaded:
                    self.manager.synth.set_punctuation_level(self.settings["punctuation_level"])
                if "pitch" in loaded:
                    self.manager.synth.set_pitch(self.settings["pitch"])
                if "capital_pitch_change" in loaded:
                    self.manager.synth.set_capital_pitch_change(self.settings["capital_pitch_change"])
                if "volume_ducking" in loaded:
                    self.manager.synth.set_volume_ducking(self.settings["volume_ducking"] == "On")
                import core.menu
                if "sound_scheme" in loaded:
                    core.menu.SOUND_SCHEME = self.settings["sound_scheme"]
                if hasattr(self.manager.synth, 'set_auto_language') and "language_auto_switch" in loaded:
                    self.manager.synth.set_auto_language(self.settings["language_auto_switch"] == "On")
            except Exception:
                pass

    def _save_settings(self):
        try:
            self.settings["voice_index"] = self.manager.synth.get_voice_index()
            self.settings["rate"] = self.manager.synth.get_rate()
            self.settings["volume"] = self.manager.synth.get_volume()
            full_settings = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    full_settings = json.load(f)
            full_settings.update(self.settings)
            with open(self.settings_file, 'w') as f:
                json.dump(full_settings, f)
            self.manager.synth.save_defaults()
        except Exception:
            pass

    # --- Shared helpers ---

    def _switch_to_submenu(self, root, title):
        self.adjust_mode = None
        self.menu = MenuSystem(root, self.speak)
        self.window.update_text(title + ": " + self.menu.get_current_item().title)

    def _build_list_menu(self, title, setting_key, options, side_effect=None):
        root = MenuNode(title)
        current = self.settings.get(setting_key)
        for opt in options:
            label = opt
            if opt == current:
                label = f"{label} (current)"
            root.add_child(MenuNode(label, lambda v=opt: self._set_and_back(setting_key, v, side_effect)))
        root.add_child(MenuNode("Back", self._current_parent_back or self._back_to_main_menu))
        self._switch_to_submenu(root, title)

    def _build_numeric_menu(self, title, setting_key, default, min_val, max_val, side_effect=None):
        root = MenuNode(title)
        root.add_child(MenuNode("Edit Value...", lambda: self._start_numeric_input(setting_key, min_val, max_val, side_effect)))
        root.add_child(MenuNode(f"Reset to Default ({default})", lambda: self._reset_numeric(setting_key, default, side_effect)))
        root.add_child(MenuNode("Back", self._current_parent_back or self._back_to_main_menu))
        self._switch_to_submenu(root, title)

    def _start_numeric_input(self, setting_key, min_val, max_val, side_effect=None):
        self.adjust_mode = "numeric_input"
        self._numeric_key = setting_key
        self._numeric_min = min_val
        self._numeric_max = max_val
        self._numeric_side_effect = side_effect
        self._text_input_buf = ""
        self.speak(f"Enter value between {min_val} and {max_val}.")
        self.window.update_text(f"{setting_key.replace('_', ' ').title()}: ")

    def _handle_numeric_input(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.adjust_mode = None
            if self._current_parent_back:
                self._current_parent_back()
            return
        if vk == win32con.VK_RETURN:
            val = self._text_input_buf.strip()
            try:
                num = int(val)
                if self._numeric_min <= num <= self._numeric_max:
                    self._set_and_back(self._numeric_key, num, side_effect=getattr(self, '_numeric_side_effect', None))
                else:
                    self.speak(f"Value must be between {self._numeric_min} and {self._numeric_max}.")
            except ValueError:
                self.speak("Invalid number.")
            return
        if vk == win32con.VK_BACK:
            if self._text_input_buf:
                self._text_input_buf = self._text_input_buf[:-1]
                self.window.update_text(self._text_input_buf if self._text_input_buf else " ")
            return
        ch = self._vk_to_char(vk)
        if ch and (ch.isdigit() or (ch == '-' and not self._text_input_buf)):
            self._text_input_buf += ch
            self.window.update_text(self._text_input_buf)

    def _reset_numeric(self, setting_key, default, side_effect=None):
        self._set_and_back(setting_key, default, side_effect=side_effect)

    def _set_and_back(self, setting_key, value, side_effect=None):
        self.settings[setting_key] = value
        self._save_settings()
        if side_effect:
            side_effect(setting_key, value)
        self.speak(f"{setting_key.replace('_', ' ').title()} set to {value}.")
        self.window.update_text(str(value))
        if self._current_parent_back:
            self._current_parent_back()

    # --- TTS Engine ---

    def _enter_tts_engine_menu(self):
        self._current_parent_back = self._back_to_tts_menu
        try:
            from core.plugin_manager import PluginManager
            pm = PluginManager()
            pm.scan()
        except Exception:
            pm = None
        synth_list = get_available_synths()
        current_module = "sapi_synth"
        try:
            with open(ACCOUNT_PATH, 'r') as f:
                account = json.load(f)
            current_module = account.get("synth_module", "sapi_synth")
        except Exception as e:
            core.error_handler.log(e, "Loading account synth module")
        root = MenuNode("TTS Engine")
        for name, module in synth_list:
            label = name
            if module == current_module:
                label = f"{name} (current)"
            root.add_child(MenuNode(label, lambda m=module, n=name: self._select_tts_engine(n, m)))
        root.add_child(MenuNode("Back", self._current_parent_back))
        self._switch_to_submenu(root, "TTS Engine")

    def _select_tts_engine(self, name, module):
        try:
            with open(ACCOUNT_PATH, 'r') as f:
                account = json.load(f)
            account["synth_module"] = module
            with open(ACCOUNT_PATH, 'w') as f:
                json.dump(account, f)
            self.speak(f"Synth set to {name}. Restart to apply.")
        except Exception:
            self.speak("Failed to save synth.")
        if self._current_parent_back:
            self._current_parent_back()

    # --- TTS Settings ---

    def _enter_rate_menu(self):
        self._current_parent_back = self._back_to_tts_menu
        self._build_numeric_menu("Speech Rate", "rate", 0, -10, 10, side_effect=self._rate_side_effect)

    def _rate_side_effect(self, key, value):
        self.manager.synth.set_rate(value)

    def _enter_volume_menu(self):
        self._current_parent_back = self._back_to_tts_menu
        self._build_numeric_menu("Volume", "volume", 100, 0, 100, side_effect=self._volume_side_effect)

    def _volume_side_effect(self, key, value):
        self.manager.synth.set_volume(value)

    def _enter_voice_menu(self):
        self._current_parent_back = self._back_to_tts_menu
        names = self.manager.synth.get_voice_names()
        if not names:
            self.speak("No voices available.")
            return
        root = MenuNode("Voice Selection")
        current_idx = self.settings.get("voice_index", 0)
        for i, name in enumerate(names):
            label = name
            if i == current_idx:
                label = f"{name} (current)"
            root.add_child(MenuNode(label, lambda idx=i, n=name: self._select_voice(idx, n)))
        root.add_child(MenuNode("Back", self._current_parent_back))
        self._switch_to_submenu(root, "Voice Selection")

    def _select_voice(self, idx, name):
        self.settings["voice_index"] = idx
        self.manager.synth.set_voice_by_index(idx)
        self._save_settings()
        self.speak(f"Voice set to {name}.")
        if self._current_parent_back:
            self._current_parent_back()

    def _enter_punctuation_menu(self):
        self._current_parent_back = self._back_to_tts_menu
        self._build_list_menu("Punctuation Level", "punctuation_level",
                             ["None", "Some", "Most", "All"],
                             side_effect=self._punctuation_side_effect)

    def _punctuation_side_effect(self, key, value):
        self.manager.synth.set_punctuation_level(value)

    def _enter_pitch_menu(self):
        self._current_parent_back = self._back_to_tts_menu
        self._build_numeric_menu("Pitch", "pitch", 50, 0, 100, side_effect=self._pitch_side_effect)

    def _pitch_side_effect(self, key, value):
        self.manager.synth.set_pitch(value)

    def _enter_capital_pitch_menu(self):
        self._current_parent_back = self._back_to_tts_menu
        self._build_list_menu("Capital Pitch Change", "capital_pitch_change",
                             ["Off", "Say Cap", "Raise Pitch"],
                             side_effect=self._capital_pitch_side_effect)

    def _capital_pitch_side_effect(self, key, value):
        self.manager.synth.set_capital_pitch_change(value)

    def _enter_language_switch_menu(self):
        self._current_parent_back = self._back_to_tts_menu
        self._build_list_menu("Language Auto-Switch", "language_auto_switch",
                             ["Off", "On"],
                             side_effect=self._language_switch_side_effect)

    def _language_switch_side_effect(self, key, value):
        if hasattr(self.manager.synth, 'set_auto_language'):
            self.manager.synth.set_auto_language(value == "On")

    def _enter_history_size_menu(self):
        self._current_parent_back = self._back_to_tts_menu
        self._build_numeric_menu("Speech History Size", "speech_history_size", 50, 10, 200, side_effect=self._history_size_side_effect)

    def _history_size_side_effect(self, key, value):
        if hasattr(self.manager.synth, 'set_history_max'):
            self.manager.synth.set_history_max(value)

    # --- Keyboard Settings ---

    def _enter_char_echo_menu(self):
        self._current_parent_back = self._back_to_kb_menu
        self._build_list_menu("Character Echo", "char_echo", ["Off", "On"])

    def _enter_word_echo_menu(self):
        self._current_parent_back = self._back_to_kb_menu
        self._build_list_menu("Word Echo", "word_echo", ["Off", "On"])

    def _enter_announce_position_menu(self):
        self._current_parent_back = self._back_to_kb_menu
        self._build_list_menu("Position Announcement", "announce_position",
                             ["Off", "On"],
                             side_effect=self._announce_position_side_effect)

    def _announce_position_side_effect(self, key, value):
        import core.menu
        core.menu.ANNOUNCE_POSITION = value == "On"

    def _enter_state_keys_menu(self):
        self._current_parent_back = self._back_to_kb_menu
        self._build_list_menu("State Keys", "state_keys", ["Off", "On"])

    # --- Audio Settings ---

    def _enter_volume_ducking_menu(self):
        self._current_parent_back = self._back_to_audio_menu
        self._build_list_menu("Volume Ducking", "volume_ducking",
                             ["Off", "On"],
                             side_effect=self._volume_ducking_side_effect)

    def _volume_ducking_side_effect(self, key, value):
        self.manager.synth.set_volume_ducking(value == "On")

    def _enter_sound_scheme_menu(self):
        self._current_parent_back = self._back_to_audio_menu
        self._build_list_menu("Sound Scheme", "sound_scheme",
                             ["Default", "Classic", "Minimal"],
                             side_effect=self._sound_scheme_side_effect)

    def _sound_scheme_side_effect(self, key, value):
        import core.menu
        core.menu.SOUND_SCHEME = value

    # --- Braille Settings ---

    def _enter_braille_display_menu(self):
        self._current_parent_back = self._back_to_braille_menu
        from braille.manager import BrailleManager
        plugin_names = list(BrailleManager.get_plugin_displays().keys())
        options = ["Off", "Humanware", "Monarch"] + plugin_names
        self._build_list_menu("Braille Display", "braille_display", options)

    def _enter_braille_grade_menu(self):
        self._current_parent_back = self._back_to_braille_menu
        self._build_list_menu("Braille Grade", "braille_grade", ["1", "2"])

    # --- Navigation helpers ---

    def _back_to_tts_menu(self):
        self._build_main_menu()
        current = self.menu.root.children[0] if self.menu.root.children else None
        if current:
            self.menu.current_node = current
            self.menu.current_index = 0
        self.menu.announce_current()

    def _back_to_kb_menu(self):
        self._build_main_menu()
        current = self.menu.root.children[1] if len(self.menu.root.children) > 1 else None
        if current:
            self.menu.current_node = current
            self.menu.current_index = 0
        self.menu.announce_current()

    def _back_to_audio_menu(self):
        self._build_main_menu()
        current = self.menu.root.children[2] if len(self.menu.root.children) > 2 else None
        if current:
            self.menu.current_node = current
            self.menu.current_index = 0
        self.menu.announce_current()

    def _back_to_braille_menu(self):
        self._build_main_menu()
        current = self.menu.root.children[3] if len(self.menu.root.children) > 3 else None
        if current:
            self.menu.current_node = current
            self.menu.current_index = 0
        self.menu.announce_current()

    # --- Voice Profiles ---
    def _enter_voice_profiles(self):
        root = MenuNode("Voice Profiles")
        profiles = self.settings.get("voice_profiles", {})
        for name in sorted(profiles.keys()):
            root.add_child(MenuNode(name, lambda n=name: self._apply_profile(n)))
        root.add_child(MenuNode("Save Current As...", self._start_save_profile))
        if profiles:
            root.add_child(MenuNode("Delete Profile", self._enter_delete_profile))
        root.add_child(MenuNode("Back", self._back_to_tts_menu))
        self._switch_to_submenu(root, "Voice Profiles")

    def _apply_profile(self, name):
        profiles = self.settings.get("voice_profiles", {})
        if name in profiles:
            p = profiles[name]
            self.manager.synth.apply_profile(
                voice_index=p.get("voice_index"),
                rate=p.get("rate"),
                pitch=p.get("pitch")
            )
            self.settings.update(p)
            self._save_settings()
            self.speak(f"{name} profile applied.")

    def _start_save_profile(self):
        self.adjust_mode = "text_input"
        self._text_input_field = "save_profile"
        self._text_input_buf = ""
        self.speak("Enter profile name.")
        self.window.update_text("Profile name: ")

    def _do_save_profile(self, name):
        profiles = self.settings.get("voice_profiles", {})
        profiles[name] = {
            "voice_index": self.manager.synth.get_voice_index(),
            "rate": self.manager.synth.get_rate(),
            "pitch": self.manager.synth.get_pitch()
        }
        self.settings["voice_profiles"] = profiles
        self._save_settings()
        self.speak(f"Profile {name} saved.")

    def _enter_delete_profile(self):
        root = MenuNode("Delete Profile")
        profiles = self.settings.get("voice_profiles", {})
        for name in sorted(profiles.keys()):
            root.add_child(MenuNode(name, lambda n=name: self._do_delete_profile(n)))
        root.add_child(MenuNode("Back", self._enter_voice_profiles))
        self._switch_to_submenu(root, "Delete Profile")

    def _do_delete_profile(self, name):
        profiles = self.settings.get("voice_profiles", {})
        if name in profiles:
            del profiles[name]
            self.settings["voice_profiles"] = profiles
            self._save_settings()
            self.speak(f"Profile {name} deleted.")
        self._enter_voice_profiles()

    # --- Pronunciation Dictionary ---
    def _enter_pronunciation_dict(self):
        root = MenuNode("Pronunciation Dictionary")
        entries = core.pronunciation_dict.get_all()
        for word, spoken in sorted(entries.items()):
            root.add_child(MenuNode(f"{word} -> {spoken}", lambda w=word: self._remove_pronunciation_word(w)))
        root.add_child(MenuNode("Add Word", self._start_add_pronunciation))
        root.add_child(MenuNode("Back", self._back_to_tts_menu))
        self._switch_to_submenu(root, "Pronunciation Dictionary")

    def _start_add_pronunciation(self):
        self.adjust_mode = "text_input"
        self._text_input_field = "pronunciation_word"
        self._text_input_buf = ""
        self._pronunciation_stage = "word"
        self._pronunciation_word = ""
        self._pronunciation_spoken = ""
        self.speak("Enter the word to customize.")
        self.window.update_text("Word: ")

    def _remove_pronunciation_word(self, word):
        core.pronunciation_dict.remove(word)
        self.speak(f"Removed {word}.")
        self._enter_pronunciation_dict()

    def _handle_pronunciation_input(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.adjust_mode = None
            self._enter_pronunciation_dict()
            return
        if vk == win32con.VK_RETURN:
            val = self._text_input_buf.strip()
            if not val:
                self.speak("Cannot be empty.")
                return
            if self._pronunciation_stage == "word":
                self._pronunciation_word = val
                self._pronunciation_stage = "spoken"
                self._text_input_buf = ""
                self.speak("Enter how it should be spoken.")
                self.window.update_text("Spoken as: ")
            else:
                self._pronunciation_spoken = val
                core.pronunciation_dict.add(self._pronunciation_word, self._pronunciation_spoken)
                self.speak(f"Added {self._pronunciation_word}.")
                self.adjust_mode = None
                self._enter_pronunciation_dict()
            return
        if vk == win32con.VK_BACK:
            if self._text_input_buf:
                self._text_input_buf = self._text_input_buf[:-1]
                self.window.update_text(self._text_input_buf)
            return
        ch = self._vk_to_char(vk)
        if ch:
            self._text_input_buf += ch
            self.window.update_text(self._text_input_buf)

    # --- Per-App Voices ---
    def _enter_per_app_voices(self):
        root = MenuNode("Per-App Voices")
        pav = self.settings.get("per_app_voice", {})
        for app_name in sorted(pav.keys()):
            override = pav[app_name]
            v = override.get("voice_index", 0)
            r = override.get("rate", 0)
            p = override.get("pitch", 50)
            names = self.manager.synth.get_voice_names()
            vn = names[v] if v < len(names) else str(v)
            root.add_child(MenuNode(f"{app_name}: {vn}, rate {r}, pitch {p}", lambda a=app_name: self._edit_per_app_voice(a)))
        root.add_child(MenuNode("Add App", self._start_add_per_app))
        if pav:
            root.add_child(MenuNode("Clear All", self._clear_per_app_voices))
        root.add_child(MenuNode("Back", self._back_to_tts_menu))
        self._switch_to_submenu(root, "Per-App Voices")

    def _start_add_per_app(self):
        self.adjust_mode = "text_input"
        self._text_input_field = "add_pav"
        self._text_input_buf = ""
        self.speak("Enter app class name (e.g. NotesApp, ChatApp).")
        self.window.update_text("App name: ")

    def _do_add_per_app(self, app_name):
        pav = self.settings.get("per_app_voice", {})
        if app_name not in pav:
            pav[app_name] = {
                "voice_index": self.manager.synth.get_voice_index(),
                "rate": self.manager.synth.get_rate(),
                "pitch": self.manager.synth.get_pitch()
            }
            self.settings["per_app_voice"] = pav
            self._save_settings()
            self.speak(f"Added {app_name}.")
        self._edit_per_app_voice(app_name)

    def _edit_per_app_voice(self, app_name):
        self._current_pav_app = app_name
        root = MenuNode(f"{app_name} Voice")
        root.add_child(MenuNode("Adjust Voice", self._enter_pav_voice_menu))
        root.add_child(MenuNode("Adjust Rate", self._enter_pav_rate_menu))
        root.add_child(MenuNode("Adjust Pitch", self._enter_pav_pitch_menu))
        root.add_child(MenuNode("Remove Override", lambda: self._remove_pav(app_name)))
        root.add_child(MenuNode("Back", self._enter_per_app_voices))
        self._switch_to_submenu(root, f"{app_name} Voice")

    def _enter_pav_voice_menu(self):
        app_name = self._current_pav_app
        self._current_parent_back = lambda: self._edit_per_app_voice(app_name)
        names = self.manager.synth.get_voice_names()
        if not names:
            self.speak("No voices available.")
            return
        pav = self.settings.get("per_app_voice", {})
        override = pav.get(app_name, {})
        current_idx = override.get("voice_index", 0)
        root = MenuNode(f"{app_name} Voice")
        for i, name in enumerate(names):
            label = name
            if i == current_idx:
                label = f"{name} (current)"
            root.add_child(MenuNode(label, lambda idx=i: self._select_pav_voice(app_name, idx)))
        root.add_child(MenuNode("Back", self._current_parent_back))
        self._switch_to_submenu(root, f"{app_name} Voice")

    def _select_pav_voice(self, app_name, idx):
        pav = self.settings.get("per_app_voice", {})
        if app_name not in pav:
            pav[app_name] = {"voice_index": idx, "rate": 0, "pitch": 50}
        else:
            pav[app_name]["voice_index"] = idx
        self.settings["per_app_voice"] = pav
        self._save_settings()
        names = self.manager.synth.get_voice_names()
        self.speak(f"Voice set to {names[idx] if idx < len(names) else idx}.")
        self._enter_pav_voice_menu()

    def _enter_pav_rate_menu(self):
        app_name = self._current_pav_app
        self._current_parent_back = lambda: self._edit_per_app_voice(app_name)
        pav = self.settings.get("per_app_voice", {})
        override = pav.get(app_name, {})
        current = override.get("rate", 0)
        root = MenuNode(f"{app_name} Rate")
        root.add_child(MenuNode("Edit Value...", lambda: self._start_pav_numeric(app_name, "rate", -10, 10)))
        root.add_child(MenuNode(f"Reset to Default (0)", lambda: self._set_pav_and_back(app_name, "rate", 0)))
        root.add_child(MenuNode("Back", self._current_parent_back))
        self._switch_to_submenu(root, f"{app_name} Rate")

    def _enter_pav_pitch_menu(self):
        app_name = self._current_pav_app
        self._current_parent_back = lambda: self._edit_per_app_voice(app_name)
        pav = self.settings.get("per_app_voice", {})
        override = pav.get(app_name, {})
        current = override.get("pitch", 50)
        root = MenuNode(f"{app_name} Pitch")
        root.add_child(MenuNode("Edit Value...", lambda: self._start_pav_numeric(app_name, "pitch", 0, 100)))
        root.add_child(MenuNode(f"Reset to Default (50)", lambda: self._set_pav_and_back(app_name, "pitch", 50)))
        root.add_child(MenuNode("Back", self._current_parent_back))
        self._switch_to_submenu(root, f"{app_name} Pitch")

    def _start_pav_numeric(self, app_name, key, min_val, max_val):
        self.adjust_mode = "pav_numeric"
        self._pav_numeric_app = app_name
        self._pav_numeric_key = key
        self._pav_numeric_min = min_val
        self._pav_numeric_max = max_val
        self._text_input_buf = ""
        self.speak(f"Enter value between {min_val} and {max_val}.")
        self.window.update_text(f"{app_name} {key}: ")

    def _handle_pav_numeric(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.adjust_mode = None
            if self._current_parent_back:
                self._current_parent_back()
            return
        if vk == win32con.VK_RETURN:
            val = self._text_input_buf.strip()
            try:
                num = int(val)
                if self._pav_numeric_min <= num <= self._pav_numeric_max:
                    self._set_pav_and_back(self._pav_numeric_app, self._pav_numeric_key, num)
                else:
                    self.speak(f"Value must be between {self._pav_numeric_min} and {self._pav_numeric_max}.")
            except ValueError:
                self.speak("Invalid number.")
            return
        if vk == win32con.VK_BACK:
            if self._text_input_buf:
                self._text_input_buf = self._text_input_buf[:-1]
                self.window.update_text(self._text_input_buf if self._text_input_buf else " ")
            return
        ch = self._vk_to_char(vk)
        if ch and (ch.isdigit() or (ch == '-' and not self._text_input_buf)):
            self._text_input_buf += ch
            self.window.update_text(self._text_input_buf)

    def _set_pav_and_back(self, app_name, key, value):
        pav = self.settings.get("per_app_voice", {})
        if app_name not in pav:
            pav[app_name] = {"voice_index": 0, "rate": 0, "pitch": 50}
        pav[app_name][key] = value
        self.settings["per_app_voice"] = pav
        self._save_settings()
        if key == "rate":
            self.manager.synth.set_rate(value)
        elif key == "pitch":
            self.manager.synth.set_pitch(value)
        self.speak(f"{app_name} {key} set to {value}.")
        if self._current_parent_back:
            self._current_parent_back()

    def _remove_pav(self, app_name):
        pav = self.settings.get("per_app_voice", {})
        if app_name in pav:
            del pav[app_name]
            self.settings["per_app_voice"] = pav
            self._save_settings()
            self.speak(f"Override for {app_name} removed.")
            self.manager.synth.reset_temp_params()
        self._enter_per_app_voices()

    def _clear_per_app_voices(self):
        self.settings["per_app_voice"] = {}
        self._save_settings()
        self.manager.synth.reset_temp_params()
        self.speak("All per-app voice overrides cleared.")

    # --- Text Input ---
    def _handle_text_input(self, vk):
        if self._text_input_field == "pronunciation_word":
            self._handle_pronunciation_input(vk)
            return
        if vk == win32con.VK_ESCAPE:
            self.adjust_mode = None
            if self._text_input_field in ("save_profile",):
                self._enter_voice_profiles()
            else:
                self._enter_per_app_voices()
            return
        if vk == win32con.VK_RETURN:
            val = self._text_input_buf.strip()
            if not val:
                self.speak("Cannot be empty.")
                return
            if self._text_input_field == "save_profile":
                self._do_save_profile(val)
            elif self._text_input_field == "add_pav":
                self._do_add_per_app(val)
            self.adjust_mode = None
            return
        if vk == win32con.VK_BACK:
            if self._text_input_buf:
                self._text_input_buf = self._text_input_buf[:-1]
                self.window.update_text(f"{self._text_input_field}: {self._text_input_buf}")
            return
        ch = self._vk_to_char(vk)
        if ch:
            self._text_input_buf += ch
            self.window.update_text(f"{self._text_input_field}: {self._text_input_buf}")
            self.speak(ch)

    def _back_to_main_menu(self):
        self._build_main_menu()
        self.menu.announce_current()

    def _back_to_tts_menu(self):
        self._build_main_menu()
        current = self.menu.root.children[0] if self.menu.root.children else None
        if current:
            self.menu.current_node = current
            self.menu.current_index = 0
        self.menu.announce_current()

    # --- Key Bindings ---
    BIND_NAMES = {
        "next_item": "Next Item (Space)",
        "prev_item": "Previous Item (Backspace)",
        "select": "Select (Enter)",
        "back": "Back (Escape)",
        "help": "Help (F1)",
        "status": "Status (F5)",
        "power_menu": "Power Menu",
    }
    VK_NAMES = {
        8: "Backspace", 13: "Enter", 27: "Escape", 32: "Space",
        112: "F1", 116: "F5",
    }

    def _get_power_key_vk(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    s = json.load(f)
                if s.get("keyboard_layout") == "UK":
                    return 0xDF
        except Exception:
            pass
        return 0xC0

    def _get_default_bindings(self):
        pk = self._get_power_key_vk()
        return {
            "next_item": [32],
            "prev_item": [8],
            "select": [13],
            "back": [27],
            "help": [112],
            "status": [116],
            "power_menu": [pk],
        }

    def _enter_key_bindings(self):
        self.adjust_mode = None
        self._build_bindings_menu()

    def _build_bindings_menu(self):
        self.adjust_mode = None
        root = MenuNode("Key Bindings")
        bindings = self._load_bindings()
        defaults = self._get_default_bindings()
        power_vk = self._get_power_key_vk()
        vk_name_map = dict(self.VK_NAMES)
        vk_name_map[0xC0] = "Backtick (US)" if power_vk == 0xC0 else "Backtick (UK)"
        vk_name_map[0xDF] = "Backtick (UK)" if power_vk == 0xDF else "Backtick (US)"
        for action in sorted(self.BIND_NAMES.keys()):
            keys = bindings.get(action, defaults[action])
            label = self.BIND_NAMES[action]
            names = []
            for k in keys:
                names.append(vk_name_map.get(k, f"VK_{k}"))
            display = f"{label} [{' '.join(names)}]"
            root.add_child(MenuNode(display, lambda a=action: self._start_rebind(a)))
        root.add_child(MenuNode("Reset to Defaults", self._reset_bindings))
        root.add_child(MenuNode("Back", self._back_from_bindings))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _load_bindings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    s = json.load(f)
                return s.get("key_bindings", {})
        except Exception:
            pass
        return {}

    def _save_bindings(self, bindings):
        try:
            full_settings = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    full_settings = json.load(f)
            full_settings["key_bindings"] = bindings
            with open(self.settings_file, 'w') as f:
                json.dump(full_settings, f)
        except Exception:
            pass

    def _start_rebind(self, action):
        self.adjust_mode = "key_bind"
        self._rebind_action = action
        self.speak(f"Press the key you want for {self.BIND_NAMES[action]}. Escape to cancel.")
        self.window.update_text(f"Rebind: {self.BIND_NAMES[action]}")

    def _handle_key_bind(self, vk):
        if vk == win32con.VK_ESCAPE:
            self._build_bindings_menu()
            return
        bindings = self._load_bindings()
        bindings[self._rebind_action] = [vk]
        self._save_bindings(bindings)
        name = self.VK_NAMES.get(vk, f"VK_{vk}")
        self.speak(f"{self.BIND_NAMES[self._rebind_action]} set to {name}.")
        self._build_bindings_menu()

    def _reset_bindings(self):
        self._save_bindings({})
        self.speak("Key bindings reset to defaults.")
        self._build_bindings_menu()

    def _back_from_bindings(self):
        self.adjust_mode = None
        self._build_main_menu()
        self.menu.announce_current()
