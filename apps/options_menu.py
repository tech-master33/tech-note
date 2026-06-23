import os
import json
import win32con
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.config import SETTINGS_PATH, ACCOUNT_PATH
from synths.registry import get_available_synths
import core.error_handler

class OptionsApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.adjust_mode = None
        self._text_input_field = None
        self._text_input_buf = ""
        self.pav_submode = None
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
            "log_level": "WARN",
            "speech_history_size": 50
        }
        self._load_voice_settings()
        self._build_main_menu()

    def _build_main_menu(self):
        root = MenuNode("Options")

        tts = root.add_child(MenuNode("TTS Menu"))
        tts.add_child(MenuNode("TTS Engine", lambda: self._enter_adjust("tts_engine")))
        tts.add_child(MenuNode("Speech Rate", lambda: self._enter_adjust("speech_rate")))
        tts.add_child(MenuNode("Volume", lambda: self._enter_adjust("volume")))
        tts.add_child(MenuNode("Voice Selection", lambda: self._enter_adjust("voice")))
        tts.add_child(MenuNode("Punctuation Level", lambda: self._enter_adjust("punctuation_level")))
        tts.add_child(MenuNode("Pitch", lambda: self._enter_adjust("pitch")))
        tts.add_child(MenuNode("Capital Pitch Change", lambda: self._enter_adjust("capital_pitch_change")))
        tts.add_child(MenuNode("Language Auto-Switch", lambda: self._enter_adjust("language_auto_switch")))
        tts.add_child(MenuNode("Voice Profiles", self._enter_voice_profiles))
        tts.add_child(MenuNode("Per-App Voices", self._enter_per_app_voices))
        tts.add_child(MenuNode("Pronunciation Dictionary", self._enter_pronunciation_dict))
        tts.add_child(MenuNode("Speech History Size", lambda: self._enter_adjust("speech_history_size")))

        kb = root.add_child(MenuNode("Keyboard Menu"))
        kb.add_child(MenuNode("Character Echo", lambda: self._enter_adjust("char_echo")))
        kb.add_child(MenuNode("Word Echo", lambda: self._enter_adjust("word_echo")))
        kb.add_child(MenuNode("Position Announcement", lambda: self._enter_adjust("announce_position")))
        kb.add_child(MenuNode("State Keys", lambda: self._enter_adjust("state_keys")))
        kb.add_child(MenuNode("Key Bindings", self._enter_key_bindings))

        audio = root.add_child(MenuNode("Audio Menu"))
        audio.add_child(MenuNode("Volume Ducking", lambda: self._enter_adjust("volume_ducking")))
        audio.add_child(MenuNode("Sound Scheme", lambda: self._enter_adjust("sound_scheme")))

        system = root.add_child(MenuNode("System Menu"))
        system.add_child(MenuNode("Log Level", lambda: self._enter_adjust("log_level")))

        self.menu = MenuSystem(root, self.speak)

    def on_focus(self):
        item = self.menu.get_current_item()
        title = item.title if item else "Options"
        self.speak("Options. " + title)
        self.window.update_text("Options: " + title)

    def on_key(self, vk):
        if self.adjust_mode:
            if self.adjust_mode == "key_bind":
                self._handle_key_bind(vk)
                return
            if self.adjust_mode == "text_input":
                self._handle_text_input(vk)
                return
            self._handle_adjust(vk)
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
        if self.adjust_mode:
            return f"Adjusting {self.adjust_mode.replace('_', ' ')}. Use Plus and Minus to change value, Enter to save, Escape to cancel."
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

    def _enter_adjust(self, key):
        self.adjust_mode = key

        if key == "tts_engine":
            self.synth_list = get_available_synths()
            current_module = "sapi_synth"
            try:
                with open(ACCOUNT_PATH, 'r') as f:
                    account = json.load(f)
                current_module = account.get("synth_module", "sapi_synth")
            except Exception as e: core.error_handler.log(e, "Loading account synth module")
            self.synth_index = 0
            for i, (name, mod) in enumerate(self.synth_list):
                if mod == current_module:
                    self.synth_index = i
                    break
            name = self.synth_list[self.synth_index][0]
            self.speak(f"TTS Engine. Current: {name}.")
        elif key == "speech_rate":
            self.speak(f"Rate. Current: {self.settings['rate']}.")
        elif key == "volume":
            self.speak(f"Volume. Current: {self.settings['volume']}.")
        elif key == "voice":
            names = self.manager.synth.get_voice_names()
            idx = self.settings.get("voice_index", 0)
            self.speak(f"Voice. Current: {names[idx] if names else 'Default'}.")
        elif key == "punctuation_level":
            self.speak(f"Punctuation Level. Current: {self.settings['punctuation_level']}.")
        elif key == "char_echo":
            self.speak(f"Character Echo. Current: {self.settings['char_echo']}.")
        elif key == "word_echo":
            self.speak(f"Word Echo. Current: {self.settings['word_echo']}.")
        elif key == "announce_position":
            self.speak(f"Position Announcement. Current: {self.settings['announce_position']}.")
        elif key == "pitch":
            self.speak(f"Pitch. Current: {self.settings['pitch']}.")
        elif key == "capital_pitch_change":
            self.speak(f"Capital Pitch Change. Current: {self.settings['capital_pitch_change']}.")
        elif key == "state_keys":
            self.speak(f"State Keys. Current: {self.settings['state_keys']}.")
        elif key == "volume_ducking":
            self.speak(f"Volume Ducking. Current: {self.settings['volume_ducking']}.")
        elif key == "language_auto_switch":
            self.speak(f"Language Auto-Switch. Current: {self.settings['language_auto_switch']}.")
        elif key == "sound_scheme":
            self.speak(f"Sound Scheme. Current: {self.settings['sound_scheme']}.")
        elif key == "log_level":
            core.error_handler.load_level_from_settings()
            self.settings["log_level"] = core.error_handler.get_level_name()
            self.speak(f"Log Level. Current: {self.settings['log_level']}.")
        elif key == "speech_history_size":
            self.speak(f"Speech History Size. Current: {self.settings.get('speech_history_size', 50)}.")

        self.window.update_text(key.replace('_', ' ').title() + ": " + str(self._get_current_display()))

    def _get_current_display(self):
        key = self.adjust_mode
        if key == "tts_engine":
            return self.synth_list[self.synth_index][0] if self.synth_list else "None"
        if key.startswith("pav_"):
            app_name = key[4:]
            pav = self.settings.get("per_app_voice", {})
            override = pav.get(app_name, {})
            if self.pav_submode == "voice":
                names = self.manager.synth.get_voice_names()
                idx = override.get("voice_index", 0)
                return names[idx] if idx < len(names) else str(idx)
            return str(override.get(self.pav_submode, ""))
        return str(self.settings.get(key, ""))

    def _handle_adjust(self, vk):
        if vk == win32con.VK_BACK or vk == win32con.VK_ESCAPE:
            self.adjust_mode = None
            self.menu.announce_current()
            return
        elif vk == 0xBB:
            self._adjust_value(1)
        elif vk == 0xBD:
            self._adjust_value(-1)
        elif vk == win32con.VK_RETURN:
            if self.adjust_mode == "tts_engine":
                self._save_synth_selection()
                return
            self.adjust_mode = None
            self.speak("Set.")

    def _adjust_value(self, direction):
        key = self.adjust_mode
        if not key: return

        if key == "tts_engine":
            if self.synth_list:
                self.synth_index = (self.synth_index + direction) % len(self.synth_list)
                self.speak(self.synth_list[self.synth_index][0])
        elif key == "speech_rate":
            self.settings["rate"] = max(-10, min(10, self.settings["rate"] + direction))
            self.manager.synth.set_rate(self.settings["rate"])
            self.speak(str(self.settings["rate"]))
        elif key == "volume":
            self.settings["volume"] = max(0, min(100, self.settings["volume"] + direction * 10))
            self.manager.synth.set_volume(self.settings["volume"])
            self.speak(str(self.settings["volume"]))
        elif key == "voice":
            names = self.manager.synth.get_voice_names()
            idx = (self.settings.get("voice_index", 0) + direction) % len(names)
            self.settings["voice_index"] = idx
            self.manager.synth.set_voice_by_index(idx)
            self.speak(names[idx])
        elif key == "punctuation_level":
            opts = ["None", "Some", "Most", "All"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % len(opts)]
            self.manager.synth.set_punctuation_level(self.settings[key])
            self.speak(self.settings[key])
        elif key == "char_echo":
            opts = ["Off", "On"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % 2]
            self.speak(f"Character Echo {self.settings[key]}")
        elif key == "word_echo":
            opts = ["Off", "On"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % 2]
            self.speak(f"Word Echo {self.settings[key]}")
        elif key == "announce_position":
            opts = ["Off", "On"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % 2]
            self.speak(f"Position Announcement {self.settings[key]}")
            import core.menu
            core.menu.ANNOUNCE_POSITION = self.settings[key] == "On"
        elif key == "pitch":
            self.settings["pitch"] = max(0, min(100, self.settings["pitch"] + direction * 10))
            self.manager.synth.set_pitch(self.settings["pitch"])
            self.speak(str(self.settings["pitch"]))
        elif key == "capital_pitch_change":
            opts = ["Off", "Say Cap", "Raise Pitch"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % len(opts)]
            self.manager.synth.set_capital_pitch_change(self.settings[key])
            self.speak(self.settings[key])
        elif key == "state_keys":
            opts = ["Off", "On"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % 2]
            self.speak(f"State Keys {self.settings[key]}")
        elif key == "volume_ducking":
            opts = ["Off", "On"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % 2]
            self.manager.synth.set_volume_ducking(self.settings[key] == "On")
            self.speak(f"Volume Ducking {self.settings[key]}")
        elif key == "sound_scheme":
            opts = ["Default", "Classic", "Minimal"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % len(opts)]
            import core.menu
            core.menu.SOUND_SCHEME = self.settings[key]
            self.speak(self.settings[key])
        elif key == "language_auto_switch":
            opts = ["Off", "On"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % 2]
            self.manager.synth.set_auto_language(self.settings[key] == "On")
            self.speak(f"Language Auto-Switch {self.settings[key]}")
        elif key == "log_level":
            opts = ["SILENT", "ERROR", "WARN", "INFO", "DEBUG", "ALL"]
            curr = opts.index(self.settings[key]) if self.settings[key] in opts else 2
            self.settings[key] = opts[(curr + direction) % len(opts)]
            name_map = {"SILENT": 0, "ERROR": 1, "WARN": 2, "INFO": 3, "DEBUG": 4, "ALL": 5}
            core.error_handler.set_level(name_map[self.settings[key]])
            core.error_handler.log(None, f"Log level set to {self.settings[key]}", level=core.error_handler.LEVEL_INFO)
            self.speak(f"Log Level {self.settings[key]}")
        elif key == "speech_history_size":
            val = max(10, min(200, self.settings.get("speech_history_size", 50) + direction * 10))
            self.settings["speech_history_size"] = val
            self.manager.synth.set_history_max(val)
            self.speak(str(val))
        elif key.startswith("pav_"):
            app_name = key[4:]
            pav = self.settings.get("per_app_voice", {})
            if app_name not in pav:
                pav[app_name] = {"voice_index": self.settings.get("voice_index", 0), "rate": self.settings.get("rate", 0), "pitch": self.settings.get("pitch", 50)}
            override = pav[app_name]
            if self.pav_submode == "voice":
                names = self.manager.synth.get_voice_names()
                idx = (override.get("voice_index", 0) + direction) % len(names)
                override["voice_index"] = idx
                self.manager.synth.set_voice_by_index(idx)
                self.speak(names[idx])
            elif self.pav_submode == "rate":
                override["rate"] = max(-10, min(10, override.get("rate", 0) + direction))
                self.manager.synth.set_rate(override["rate"])
                self.speak(str(override["rate"]))
            elif self.pav_submode == "pitch":
                override["pitch"] = max(0, min(100, override.get("pitch", 50) + direction * 10))
                self.manager.synth.set_pitch(override["pitch"])
                self.speak(str(override["pitch"]))
            pav[app_name] = override
            self.settings["per_app_voice"] = pav

        self.window.update_text(key.replace('_', ' ').title() + ": " + str(self._get_current_display()))
        self._save_settings()

    def _save_synth_selection(self):
        name, module = self.synth_list[self.synth_index]
        try:
            with open(ACCOUNT_PATH, 'r') as f:
                account = json.load(f)
            account["synth_module"] = module
            with open(ACCOUNT_PATH, 'w') as f:
                json.dump(account, f)
            self.speak(f"Synth set to {name}. Restart to apply.")
        except Exception:
            self.speak("Failed to save synth.")
        self.adjust_mode = None
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
        root = MenuNode(f"{app_name} Voice")
        root.add_child(MenuNode("Adjust Voice", lambda: self._enter_pav_adjust(app_name, "voice")))
        root.add_child(MenuNode("Adjust Rate", lambda: self._enter_pav_adjust(app_name, "rate")))
        root.add_child(MenuNode("Adjust Pitch", lambda: self._enter_pav_adjust(app_name, "pitch")))
        root.add_child(MenuNode("Remove Override", lambda: self._remove_pav(app_name)))
        root.add_child(MenuNode("Back", self._enter_per_app_voices))
        self._switch_to_submenu(root, f"{app_name} Voice")

    def _enter_pav_adjust(self, app_name, submode):
        self.adjust_mode = f"pav_{app_name}"
        self.pav_submode = submode
        pav = self.settings.get("per_app_voice", {})
        override = pav.get(app_name, {})
        if submode == "voice":
            names = self.manager.synth.get_voice_names()
            idx = override.get("voice_index", 0)
            self.manager.synth.set_voice_by_index(idx)
            self.speak(f"Voice. Current: {names[idx] if names else 'Default'}.")
        elif submode == "rate":
            r = override.get("rate", 0)
            self.manager.synth.set_rate(r)
            self.speak(f"Rate. Current: {r}.")
        elif submode == "pitch":
            p = override.get("pitch", 50)
            self.manager.synth.set_pitch(p)
            self.speak(f"Pitch. Current: {p}.")
        self.window.update_text(f"{app_name} {submode}: {self._get_current_display()}")

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
            self._enter_voice_profiles() if self._text_input_field in ("save_profile",) else self._enter_per_app_voices()
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

    def _back_to_tts_menu(self):
        self._build_main_menu()
        self.menu.current_index = 0
        self.menu.announce_current()

    def _switch_to_submenu(self, root, title):
        self.adjust_mode = None
        self.menu = MenuSystem(root, self.speak)
        self.window.update_text(title + ": " + self.menu.get_current_item().title)

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
        0xBB: "Equals", 0xBD: "Minus",
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
