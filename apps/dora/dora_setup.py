import time
from apps.dora.dora_config import load_settings, save_settings

class DoraSetup:
    def __init__(self, assistant, speak_func):
        self.assistant = assistant
        self.speak = speak_func
        self.username = "User"

    def run(self):
        self.speak("Hello! I'm Dora, your personal assistant. Let's get to know each other.")
        time.sleep(0.5)
        self.speak("What is your name?")
        response = self.assistant.listen(timeout=8)
        if response:
            name = response.strip().title()
            self.speak(f"Nice to meet you, {name}!")
            self.username = name
        else:
            self.speak("I'll call you User for now.")
        time.sleep(0.3)
        self.speak("Would you like me to enable AI chat? This lets me answer questions using artificial intelligence. Say yes or no.")
        ai_enabled = False
        response = self.assistant.listen(timeout=6)
        if response and 'yes' in response.lower():
            ai_enabled = True
            self.speak("AI chat enabled. You can change this anytime.")
        else:
            self.speak("No problem. You can enable it later.")
        settings = load_settings()
        settings['username'] = self.username
        settings['ai_enabled'] = ai_enabled
        save_settings(settings)
        self.speak("Setup is complete. Press F2 to open Dora, or double press F2 to activate voice mode.")
