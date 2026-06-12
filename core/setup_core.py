import json
import os
import win32con
from core.app_base import SoftApp
from core.config import ACCOUNT_PATH
from synths.registry import get_available_synths, create_synth

class TechNoteSetup(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.finish_callback = None
        self.available_synths = get_available_synths()
        self.synth_index = 0
        self.synth_module = "sapi_synth"
        self.voices = []
        self.voice_index = 0
        self.current_step = 0
        self.username = ""
        self.password = ""
        self.pin = ""
        self.active = True

    def _load_voices_for_synth(self):
        inst = create_synth(self.synth_module)
        if inst:
            self.voices = inst.get_voice_names()
            self.voice_index = 0

    def run_setup(self):
        self.window.update_text("TechNote Setup")
        self.speak("Welcome to TechNote. Press Enter to begin.")

    def on_key(self, vk):
        if self.current_step == 0:
            if vk == win32con.VK_RETURN:
                self.current_step += 1
                self.speak("Enter username.")

        elif self.current_step == 1:
            if vk == win32con.VK_RETURN:
                if self.username:
                    self.current_step += 1
                    self.speak("Enter password.")
                    self.window.update_text("Password: ")
            elif vk == win32con.VK_BACK:
                self.username = self.username[:-1]
                self.window.update_text(self.username)
            elif (0x41 <= vk <= 0x5A) or (0x30 <= vk <= 0x39):
                self.username += chr(vk).lower()
                self.window.update_text(self.username)
                self.speak(chr(vk))

        elif self.current_step == 2:
            if vk == win32con.VK_RETURN:
                if self.password:
                    self.current_step += 1
                    self.speak("Enter 4 digit PIN.")
            elif vk == win32con.VK_BACK:
                self.password = self.password[:-1]
                self.window.update_text("*" * len(self.password))
            elif (0x41 <= vk <= 0x5A) or (0x30 <= vk <= 0x39):
                self.password += chr(vk).lower()
                self.window.update_text("*" * len(self.password))

        elif self.current_step == 3:
            if 0x30 <= vk <= 0x39:
                self.pin += chr(vk)
                self.window.update_text("*" * len(self.pin))
                self.speak("Digit added")
                if len(self.pin) == 4:
                    self.current_step += 1
                    self.speak("TTS engine. Use arrows to select.")
                    self.window.update_text(self.available_synths[self.synth_index][0])
            elif vk == win32con.VK_BACK:
                self.pin = self.pin[:-1]
                self.window.update_text("*" * len(self.pin))

        elif self.current_step == 4:
            if vk == win32con.VK_DOWN or vk == win32con.VK_SPACE:
                self.synth_index = (self.synth_index + 1) % len(self.available_synths)
                self.window.update_text(self.available_synths[self.synth_index][0])
                self.speak(self.available_synths[self.synth_index][0])
            elif vk == win32con.VK_UP or vk == win32con.VK_BACK:
                self.synth_index = (self.synth_index - 1) % len(self.available_synths)
                self.window.update_text(self.available_synths[self.synth_index][0])
                self.speak(self.available_synths[self.synth_index][0])
            elif vk == win32con.VK_RETURN:
                self.synth_module = self.available_synths[self.synth_index][1]
                self._load_voices_for_synth()
                self.current_step += 1
                if self.voices:
                    self.speak("Voice selection. Use arrows.")
                    self.window.update_text(self.voices[self.voice_index])
                else:
                    self.speak("No voices available. Press Enter to continue.")

        elif self.current_step == 5:
            if not self.voices:
                self.speak("No voices available. Press Enter to continue.")
                if vk == win32con.VK_RETURN:
                    self.save_account()
                    self.current_step += 1
                    self.speak("Setup complete. Press Enter.")
                return
            if vk == win32con.VK_DOWN or vk == win32con.VK_SPACE:
                self.voice_index = (self.voice_index + 1) % len(self.voices)
                self.window.update_text(self.voices[self.voice_index])
                self.speak(self.voices[self.voice_index])
            elif vk == win32con.VK_UP or vk == win32con.VK_BACK:
                self.voice_index = (self.voice_index - 1) % len(self.voices)
                self.window.update_text(self.voices[self.voice_index])
                self.speak(self.voices[self.voice_index])
            elif vk == win32con.VK_RETURN:
                self.save_account()
                self.current_step += 1
                self.speak("Setup complete. Press Enter.")

        elif self.current_step == 6:
            if vk == win32con.VK_RETURN:
                self.active = False
                if self.finish_callback:
                    self.finish_callback()

    def save_account(self):
        config = {
            "username": self.username,
            "password": self.password,
            "pin": self.pin,
            "synth_module": self.synth_module,
            "default_synth": self.voices[self.voice_index] if self.voices else "Default"
        }
        with open(ACCOUNT_PATH, 'w') as f:
            json.dump(config, f)
        inst = create_synth(self.synth_module)
        if inst and hasattr(inst, 'set_voice') and self.voices:
            inst.set_voice(self.voices[self.voice_index])
        self.speak("Account saved.")
