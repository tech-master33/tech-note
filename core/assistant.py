import datetime
import speech_recognition as _sr_mod

_sr = _sr_mod


class VoiceAssistant:
    def __init__(self, speak_func, on_shutdown=None, on_restart=None):
        self.speak = speak_func
        self.on_shutdown = on_shutdown
        self.on_restart = on_restart
        self.listening = False

    def listen(self, timeout=10):
        try:
            r = _sr.Recognizer()
            with _sr.Microphone() as source:
                audio = r.listen(source, timeout=timeout, phrase_time_limit=10)
            text = r.recognize_google(audio)
            return text.lower()
        except Exception:
            return ""

    def handle_command(self, command):
        if not command:
            self.speak("No command heard.")
            return
        
        if command.startswith("say "):
            self.speak(command[4:])
            return

        c = command.replace(" ", "")
        if "time" in c:
            now = datetime.datetime.now()
            self.speak(f"The time is {now.strftime('%I:%M %p').lstrip('0')}.")
        elif "date" in c:
            self.speak(f"Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')}.")
        elif "battery" in c:
            self._battery()
        elif "shut" in c or "turn off" in command:
            self.speak("Shutting down Tech-Note.")
            if self.on_shutdown:
                self.on_shutdown()
        elif "restart" in c or "reboot" in c:
            self.speak("Restarting Tech-Note.")
            if self.on_restart:
                self.on_restart()
        else:
            self.speak("I don't know that command.")

    def _battery(self):
        try:
            import psutil
            bat = psutil.sensors_battery()
            if bat is None:
                self.speak("No battery found.")
                return
            pct = int(bat.percent)
            status = "charging" if bat.power_plugged else "on battery"
            if pct == 100 and bat.power_plugged:
                status = "fully charged"
            self.speak(f"Battery at {pct} percent, {status}.")
        except Exception:
            self.speak("Could not check battery.")

    def run(self):
        self.speak("Listening.")
        cmd = self.listen(timeout=10)
        self.handle_command(cmd)
