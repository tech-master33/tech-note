import threading
import time
import queue
import inspect
from apps.dora.dora_config import load_settings, save_settings

_sr = None
_skills = None

def _get_sr():
    global _sr
    if _sr is None:
        import speech_recognition as sr_mod
        _sr = sr_mod
    return _sr

def _get_skills():
    global _skills
    if _skills is None:
        from apps.dora.skills import information, system, timer as timer_skill, conversation
        _skills = {'information': information, 'system': system, 'timer': timer_skill, 'conversation': conversation}
    return _skills

class DoraAssistant:
    def __init__(self, synth_speak):
        self.speak_func = synth_speak
        self.settings = load_settings()
        self.username = self.settings.get('username', 'User')
        self.ai_mode = self.settings.get('ai_enabled', False)
        self.is_running = True
        self.listening = False
        self._command_map = self._build_commands()
        self.input_queue = queue.Queue()

    def _build_commands(self):
        sk = _get_skills()
        return {
            'what time is it': sk['information'].tell_time,
            'time': sk['information'].tell_time,
            'what is the date': sk['information'].tell_date,
            'date': sk['information'].tell_date,
            'shut down': sk['system'].shutdown_computer,
            'turn off': sk['system'].shutdown_computer,
            'restart': sk['system'].restart_computer,
            'reboot': sk['system'].restart_computer,
            'cancel shutdown': sk['system'].cancel_shutdown,
            'battery': sk['system'].get_battery_status,
            'battery status': sk['system'].get_battery_status,
            'open': sk['system'].open_application,
            'start': sk['system'].open_application,
            'launch': sk['system'].open_application,
            'set timer': sk['timer'].start_timer,
            'timer': sk['timer'].start_timer,
            'stop timer': sk['timer'].stop_timer,
            'stop alarm': sk['timer'].stop_timer,
        }

    def speak(self, text):
        self.speak_func(text)

    def listen(self, timeout=5, source=None):
        try:
            sr = _get_sr()
            r = sr.Recognizer()
            if source is not None:
                audio = r.listen(source, timeout=timeout)
            else:
                with sr.Microphone() as mic:
                    r.adjust_for_ambient_noise(mic, duration=0.3)
                    audio = r.listen(mic, timeout=timeout)
            command = r.recognize_google(audio)
            return command.lower()
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            return ""
        except Exception as e:
            print(f"Speech recognition error: {e}")
            return ""

    def process_command(self, command):
        if not command:
            return
        processed = command.replace(" ", "")
        sorted_keys = sorted(self._command_map.keys(), key=len, reverse=True)
        for keyword in sorted_keys:
            func = self._command_map[keyword]
            if func is None:
                continue
            if keyword.replace(" ", "") in processed:
                sig = inspect.signature(func)
                expects_command = 'command' in sig.parameters
                if expects_command:
                    func(self, command)
                else:
                    func(self)
                return
        if self.ai_mode:
            sk = _get_skills()
            sk['conversation'].chat_with_ai(self, command)
        else:
            self.speak("I don't know that command.")

    def run_voice_loop(self):
        sr = _get_sr()
        self.listening = True
        wake_word = self.settings.get('wake_word', 'computer').lower()
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
        self.speak("Voice mode activated. Say wake word to begin.")
        while self.is_running and self.listening:
            try:
                with sr.Microphone() as source:
                    audio = r.listen(source, phrase_time_limit=3, timeout=1)
                query = r.recognize_google(audio).lower().strip()
                if wake_word in query:
                    self.speak("Yes?")
                    with sr.Microphone() as source:
                        command = self.listen(source=source)
                    self.process_command(command)
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except Exception as e:
                print(f"Voice loop error: {e}")
                time.sleep(0.5)

    def stop_voice_loop(self):
        self.listening = False
