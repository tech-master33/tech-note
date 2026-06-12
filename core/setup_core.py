import json
import os
import win32con
import win32api
import comtypes.client
from core.app_base import SoftApp

class TechNoteSetup(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.finish_callback = None
        self.steps = [
            "Welcome to TechNote. Press Enter to begin.",
            "Enter your username, then press Enter.",
            "Enter a 4-digit PIN, then press Enter.",
            "Select your voice. Use arrows, Enter to confirm.",
            "Setup complete. Press Enter to start."
        ]
        self.current_step = 0
        self.username = ""
        self.pin = ""
        # Access voices through the manager's engine
        if hasattr(self.manager, 'engine'):
            self.voices = [v.GetDescription() for v in self.manager.engine.GetVoices()]
        else:
            self.voices = []
        self.voice_index = 0
        self.active = True

    def run_setup(self):
        self.window.update_text("TechNote Setup")
        self.speak(self.steps[0])

    def on_key(self, vk):
        if self.current_step == 0:
            if vk == win32con.VK_RETURN:
                self.current_step += 1
                self.speak("Enter username.")
        
        elif self.current_step == 1:
            if vk == win32con.VK_RETURN:
                if self.username:
                    self.current_step += 1
                    self.speak("Enter 4 digit PIN.")
            elif vk == win32con.VK_BACK:
                self.username = self.username[:-1]
                self.window.update_text(self.username)
            elif (0x41 <= vk <= 0x5A) or (0x30 <= vk <= 0x39):
                self.username += chr(vk).lower()
                self.window.update_text(self.username)
                self.speak(chr(vk))

        elif self.current_step == 2:
            if 0x30 <= vk <= 0x39: # Digits
                self.pin += chr(vk)
                self.window.update_text("*" * len(self.pin))
                self.speak("Digit added")
                if len(self.pin) == 4:
                    self.current_step += 1
                    self.speak("Voice selection. Use arrows.")
                    self.window.update_text(self.voices[self.voice_index])
            elif vk == win32con.VK_BACK:
                self.pin = self.pin[:-1]
                self.window.update_text("*" * len(self.pin))

        elif self.current_step == 3:
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
        
        elif self.current_step == 4:
            if vk == win32con.VK_RETURN:
                self.active = False
                if self.finish_callback:
                    self.finish_callback()

    def save_account(self):
        tech_soft = os.path.join(os.environ['USERPROFILE'], '.tech-soft')
        account_path = os.path.join(tech_soft, 'account.json')
        config = {
            "username": self.username,
            "pin": self.pin,
            "default_synth": self.voices[self.voice_index]
        }
        with open(account_path, 'w') as f:
            json.dump(config, f)
        # Apply voice
        if hasattr(self.manager, 'engine') and self.voices:
            for voice in self.manager.engine.GetVoices():
                if voice.GetDescription() == self.voices[self.voice_index]:
                    self.manager.engine.Voice = voice
                    break
        self.speak("Account saved.")
