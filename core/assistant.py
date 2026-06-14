import datetime
import os
import subprocess

_sr = None

def _get_sr():
    global _sr
    if _sr is None:
        import speech_recognition as sr_mod
        _sr = sr_mod
    return _sr


class VoiceAssistant:
    def __init__(self, speak_func, on_shutdown=None, on_restart=None):
        self.speak = speak_func
        self.on_shutdown = on_shutdown
        self.on_restart = on_restart
        self.listening = False

    def listen(self, timeout=5):
        try:
            sr = _get_sr()
            r = sr.Recognizer()
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.3)
                audio = r.listen(source, timeout=timeout)
            text = r.recognize_google(audio)
            return text.lower()
        except Exception:
            return ""

    def handle_command(self, command):
        if not command:
            self.speak("No command heard.")
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
        elif "cancel" in c:
            self.speak("Nothing to cancel.")
        elif "open" in command or "launch" in command or "start" in command:
            self._open_app(command)
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

    def _open_app(self, command):
        apps = {
            "chrome": "chrome.exe", "firefox": "firefox.exe", "notepad": "notepad.exe",
            "calculator": "calc.exe", "edge": "msedge.exe", "vlc": "vlc.exe",
        }
        for name, exe in apps.items():
            if name in command:
                subprocess.Popen(exe, creationflags=subprocess.CREATE_NO_WINDOW)
                self.speak(f"Opening {name}.")
                return
        self.speak(f"Could not find {command}.")

    def run(self):
        self.speak("Listening.")
        cmd = self.listen(timeout=5)
        self.handle_command(cmd)
