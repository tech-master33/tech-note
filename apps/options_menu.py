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
            "time_format": "12h", "startup_sound": "On",
            "bg_color": "Black", "font_size": "Medium"
        }
        self._load_all_settings()
        self._build_main_menu()

    def _build_main_menu(self):
        root = MenuNode("Options")
        root.add_child(MenuNode("Voice Settings", self._enter_voice_menu))
        root.add_child(MenuNode("System Settings", self._enter_system_menu))
        root.add_child(MenuNode("Display Settings", self._enter_display_menu))
        self.menu = MenuSystem(root, self.speak)

    def _enter_voice_menu(self):
        root = MenuNode("Voice Settings")
        root.add_child(MenuNode("TTS Engine", lambda: self._enter_adjust("tts_engine")))
        root.add_child(MenuNode("Speech Rate", lambda: self._enter_adjust("speech_rate")))
        root.add_child(MenuNode("Volume", lambda: self._enter_adjust("volume")))
        root.add_child(MenuNode("Voice Selection", lambda: self._enter_adjust("voice")))
        root.add_child(MenuNode("Back", self._build_main_menu))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _enter_system_menu(self):
        root = MenuNode("System Settings")
        root.add_child(MenuNode("Time Format", lambda: self._enter_adjust("time_format")))
        root.add_child(MenuNode("Startup Sound", lambda: self._enter_adjust("startup_sound")))
        root.add_child(MenuNode("Back", self._build_main_menu))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _enter_display_menu(self):
        root = MenuNode("Display Settings")
        root.add_child(MenuNode("Background Color", lambda: self._enter_adjust("bg_color")))
        root.add_child(MenuNode("Font Size", lambda: self._enter_adjust("font_size")))
        root.add_child(MenuNode("Back", self._build_main_menu))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def on_focus(self):
        item = self.menu.get_current_item()
        title = item.title if item else "Options"
        self.speak("Options. " + title)
        self.window.update_text("Options: " + title)

    def on_key(self, vk):
        if self.adjust_mode:
            self._handle_adjust(vk)
            return

        if vk == win32con.VK_ESCAPE:
            if self.menu.current_node.parent:
                self.menu.back()
            else:
                self.exit_app()
            return

        if vk in (win32con.VK_BACK, win32con.VK_UP):
            self.menu.previous()
        elif vk in (win32con.VK_DOWN, win32con.VK_SPACE):
            self.menu.next()
        elif vk == win32con.VK_RETURN:
            self.menu.select()

        item = self.menu.get_current_item()
        if item:
            self.window.update_text(item.title)

    def get_help_text(self):
        if self.adjust_mode:
            return f"Adjusting {self.adjust_mode.replace('_', ' ')}. Use Plus and Minus to change value, Enter to save, Escape to cancel."
        return "Options Menu. Use arrows to navigate sub-menus. Enter to select. Press Escape to go back."

    def _load_all_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    loaded = json.load(f)
                self.settings.update(loaded)

                # Apply voice settings immediately
                self.manager.set_rate(self.settings.get("rate", 0))
                self.manager.set_volume(self.settings.get("volume", 100))
                names = self.manager.get_voice_names()
                v_idx = self.settings.get("voice_index", 0)
                if 0 <= v_idx < len(names):
                    self.manager.set_voice_by_index(v_idx)

                # Apply display settings immediately
                self._apply_display_settings()
            except Exception:
                pass

    def _save_all_settings(self):
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f)
        except Exception:
            pass

    def _apply_display_settings(self):
        colors = {"Black": (0,0,0), "Blue": (0,0,128), "Gray": (64,64,64)}
        bg = colors.get(self.settings.get("bg_color", "Black"), (0,0,0))
        fs = self.settings.get("font_size", "Medium")
        self.window.set_display_settings(bg_color=bg, font_size=fs)

    def _enter_adjust(self, key):
        self.adjust_mode = key
        val = self.settings.get(key)

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
        elif key == "time_format":
            self.speak(f"Time Format. Current: {val}.")
        elif key == "startup_sound":
            self.speak(f"Startup Sound. Current: {val}.")
        elif key == "bg_color":
            self.speak(f"Background Color. Current: {val}.")
        elif key == "font_size":
            self.speak(f"Font Size. Current: {val}.")

        self.window.update_text(key.replace('_', ' ').title() + ": " + str(self._get_current_display()))

    def _get_current_display(self):
        key = self.adjust_mode
        if key == "tts_engine":
            return self.synth_list[self.synth_index][0] if self.synth_list else "None"
        return str(self.settings.get(key, ""))

    def _handle_adjust(self, vk):
        if vk == win32con.VK_BACK or vk == win32con.VK_ESCAPE:
            self.adjust_mode = None
            item = self.menu.get_current_item()
            title = item.title if item else "Options"
            self.speak(title)
            self.window.update_text(title)
            return
        elif vk == 0xBB: # Plus
            self._adjust_value(1)
        elif vk == 0xBD: # Minus
            self._adjust_value(-1)
        elif vk == win32con.VK_RETURN:
            if self.adjust_mode == "tts_engine":
                self._save_synth_selection()
                return
            self.speak("Set.")
            self.adjust_mode = None
            item = self.menu.get_current_item()
            title = item.title if item else "Options"
            self.window.update_text(title)

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
        elif key == "time_format":
            opts = ["12h", "24h"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % 2]
            self.speak(self.settings[key])
        elif key == "startup_sound":
            opts = ["On", "Off"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % 2]
            self.speak(self.settings[key])
        elif key == "bg_color":
            opts = ["Black", "Blue", "Gray"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % 3]
            self.speak(self.settings[key])
            self._apply_display_settings()
        elif key == "font_size":
            opts = ["Small", "Medium", "Large"]
            curr = opts.index(self.settings[key])
            self.settings[key] = opts[(curr + direction) % 3]
            self.speak(self.settings[key])
            self._apply_display_settings()

        self.window.update_text(key.replace('_', ' ').title() + ": " + str(self._get_current_display()))
        self._save_all_settings()

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
        item = self.menu.get_current_item()
        title = item.title if item else "Options"
        self.speak(title)
        self.window.update_text(title)