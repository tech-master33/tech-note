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
        self._load_voice_settings()
        root = MenuNode("Options")
        root.add_child(MenuNode("TTS Engine", lambda: self._enter_adjust("tts_engine")))
        root.add_child(MenuNode("Speech Rate", lambda: self._enter_adjust("speech_rate")))
        root.add_child(MenuNode("Volume", lambda: self._enter_adjust("volume")))
        root.add_child(MenuNode("Voice", lambda: self._enter_adjust("voice")))
        self.menu = MenuSystem(root, self.speak)

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
            self.exit_app()
        elif vk in (win32con.VK_BACK, win32con.VK_UP):
            self.menu.previous()
        elif vk in (win32con.VK_DOWN, win32con.VK_SPACE):
            self.menu.next()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Options: " + item.title)

    def _load_voice_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                rate = settings.get("rate")
                volume = settings.get("volume")
                voice_index = settings.get("voice_index")
                if rate is not None:
                    self.manager.set_rate(rate)
                if volume is not None:
                    self.manager.set_volume(volume)
                if voice_index is not None:
                    names = self.manager.get_voice_names()
                    if 0 <= voice_index < len(names):
                        self.manager.set_voice_by_index(voice_index)
            except Exception:
                pass

    def _save_voice_settings(self):
        try:
            settings = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
            settings["rate"] = self.manager.get_rate()
            settings["volume"] = self.manager.get_volume()
            settings["voice_index"] = self.manager.get_voice_index()
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f)
        except Exception:
            pass

    def _enter_adjust(self, key):
        if key == "tts_engine":
            self.synth_list = get_available_synths()
            current_module = "sapi_synth"
            try:
                with open(ACCOUNT_PATH, 'r') as f:
                    account = json.load(f)
                current_module = account.get("synth_module", "sapi_synth")
            except Exception:
                pass
            self.synth_index = 0
            for i, (name, mod) in enumerate(self.synth_list):
                if mod == current_module:
                    self.synth_index = i
                    break
            name = self.synth_list[self.synth_index][0]
            self.speak(f"TTS Engine. Current: {name}. Use plus and minus to change.")
        elif key == "speech_rate":
            val = self.manager.get_rate()
            self.speak(f"Rate. Current: {val}. Use plus and minus to adjust.")
        elif key == "volume":
            val = self.manager.get_volume()
            self.speak(f"Volume. Current: {val}. Use plus and minus to adjust.")
        elif key == "voice":
            names = self.manager.get_voice_names()
            idx = self.manager.get_voice_index()
            self.speak(f"Voice. Current: {names[idx]}. Use plus and minus to change.")
        self.adjust_mode = key
        self.window.update_text(key.replace('_', ' ').title() + ": " + str(self._get_current_display()))

    def _get_current_display(self):
        key = self.adjust_mode
        if key == "tts_engine":
            if self.synth_list:
                return self.synth_list[self.synth_index][0]
            return "None"
        elif key == "speech_rate":
            return self.manager.get_rate()
        elif key == "volume":
            return self.manager.get_volume()
        elif key == "voice":
            names = self.manager.get_voice_names()
            idx = self.manager.get_voice_index()
            return names[idx]
        return ""

    def _handle_adjust(self, vk):
        if vk == win32con.VK_BACK or vk == win32con.VK_ESCAPE:
            self.adjust_mode = None
            item = self.menu.get_current_item()
            title = item.title if item else "Options"
            self.speak(title)
            self.window.update_text("Options: " + title)
            return
        elif vk == 0xBB:
            self._adjust_value(1)
        elif vk == 0xBD:
            self._adjust_value(-1)
        elif vk == win32con.VK_RETURN:
            if self.adjust_mode == "tts_engine":
                self._save_synth_selection()
                return
            self.speak("Set.")
            self.adjust_mode = None
            item = self.menu.get_current_item()
            title = item.title if item else "Options"
            self.window.update_text("Options: " + title)

    def _adjust_value(self, direction):
        key = self.adjust_mode
        if not key:
            return
        if key == "tts_engine":
            if self.synth_list:
                self.synth_index = (self.synth_index + direction) % len(self.synth_list)
                self.speak(self.synth_list[self.synth_index][0])
        elif key == "speech_rate":
            val = self.manager.get_rate() + direction
            self.manager.set_rate(val)
            self.speak(str(self.manager.get_rate()))
        elif key == "volume":
            val = self.manager.get_volume() + direction * 10
            self.manager.set_volume(val)
            self.speak(str(self.manager.get_volume()))
        elif key == "voice":
            names = self.manager.get_voice_names()
            idx = self.manager.get_voice_index()
            idx = (idx + direction) % len(names)
            self.manager.set_voice_by_index(idx)
            self.speak(names[idx])
        self.window.update_text(key.replace('_', ' ').title() + ": " + str(self._get_current_display()))
        self._save_voice_settings()

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
        self.window.update_text("Options: " + title)