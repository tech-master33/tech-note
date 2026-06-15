import os
import json
import win32con
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.config import SETTINGS_PATH, ACCOUNT_PATH
from synths.registry import get_available_synths

class OptionsApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.adjust_mode = None
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
            "sound_scheme": "Default"
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

        kb = root.add_child(MenuNode("Keyboard Menu"))
        kb.add_child(MenuNode("Character Echo", lambda: self._enter_adjust("char_echo")))
        kb.add_child(MenuNode("Word Echo", lambda: self._enter_adjust("word_echo")))
        kb.add_child(MenuNode("Position Announcement", lambda: self._enter_adjust("announce_position")))
        kb.add_child(MenuNode("State Keys", lambda: self._enter_adjust("state_keys")))
        kb.add_child(MenuNode("Key Bindings", self._enter_key_bindings))

        audio = root.add_child(MenuNode("Audio Menu"))
        audio.add_child(MenuNode("Volume Ducking", lambda: self._enter_adjust("volume_ducking")))
        audio.add_child(MenuNode("Sound Scheme", lambda: self._enter_adjust("sound_scheme")))

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
                self.manager.set_rate(self.settings.get("rate", 0))
                self.manager.set_volume(self.settings.get("volume", 100))
                names = self.manager.get_voice_names()
                v_idx = self.settings.get("voice_index", 0)
                if 0 <= v_idx < len(names):
                    self.manager.set_voice_by_index(v_idx)
                pl = self.settings.get("punctuation_level", "Some")
                self.manager.set_punctuation_level(pl)
                self.manager.set_pitch(self.settings.get("pitch", 50))
                self.manager.set_capital_pitch_change(self.settings.get("capital_pitch_change", "Off"))
                self.manager.set_volume_ducking(self.settings.get("volume_ducking", "Off") == "On")
                import core.menu
                core.menu.SOUND_SCHEME = self.settings.get("sound_scheme", "Default")
            except Exception:
                pass

    def _save_settings(self):
        try:
            full_settings = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    full_settings = json.load(f)
            full_settings.update(self.settings)
            with open(self.settings_file, 'w') as f:
                json.dump(full_settings, f)
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
            except Exception: pass
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
            names = self.manager.get_voice_names()
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
        elif key == "sound_scheme":
            self.speak(f"Sound Scheme. Current: {self.settings['sound_scheme']}.")

        self.window.update_text(key.replace('_', ' ').title() + ": " + str(self._get_current_display()))

    def _get_current_display(self):
        key = self.adjust_mode
        if key == "tts_engine":
            return self.synth_list[self.synth_index][0] if self.synth_list else "None"
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
            self.manager.set_rate(self.settings["rate"])
            self.speak(str(self.settings["rate"]))
        elif key == "volume":
            self.settings["volume"] = max(0, min(100, self.settings["volume"] + direction * 10))
            self.manager.set_volume(self.settings["volume"])
            self.speak(str(self.settings["volume"]))
        elif key == "voice":
            names = self.manager.get_voice_names()
            idx = (self.settings.get("voice_index", 0) + direction) % len(names)
            self.settings["voice_index"] = idx
            self.manager.set_voice_by_index(idx)
            self.speak(names[idx])
        elif key == "punctuation_level":
            opts = ["None", "Some", "Most", "All"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % len(opts)]
            self.manager.set_punctuation_level(self.settings[key])
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
            self.manager.set_pitch(self.settings["pitch"])
            self.speak(str(self.settings["pitch"]))
        elif key == "capital_pitch_change":
            opts = ["Off", "Say Cap", "Raise Pitch"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % len(opts)]
            self.manager.set_capital_pitch_change(self.settings[key])
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
            self.manager.set_volume_ducking(self.settings[key] == "On")
            self.speak(f"Volume Ducking {self.settings[key]}")
        elif key == "sound_scheme":
            opts = ["Default", "Classic", "Minimal"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % len(opts)]
            import core.menu
            core.menu.SOUND_SCHEME = self.settings[key]
            self.speak(self.settings[key])

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
