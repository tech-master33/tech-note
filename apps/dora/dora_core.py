import threading
import time
import queue
import inspect
import speech_recognition as sr
from apps.dora.dora_config import load_settings, save_settings
from apps.dora.skills import information, system, timer as timer_skill, conversation

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
        return {
            'what time is it': information.tell_time,
            'time': information.tell_time,
            'what is the date': information.tell_date,
            'date': information.tell_date,
            'shut down': system.shutdown_computer,
            'turn off': system.shutdown_computer,
            'restart': system.restart_computer,
            'reboot': system.restart_computer,
            'cancel shutdown': system.cancel_shutdown,
            'battery': system.get_battery_status,
            'battery status': system.get_battery_status,
            'open': system.open_application,
            'start': system.open_application,
            'launch': system.open_application,
            'set timer': timer_skill.start_timer,
            'timer': timer_skill.start_timer,
            'stop timer': timer_skill.stop_timer,
            'stop alarm': timer_skill.stop_timer,
        }

    def speak(self, text):
        self.speak_func(text)

    def listen(self, timeout=5):
        try:
            r = sr.Recognizer()
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.3)
                audio = r.listen(source, timeout=timeout)
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
            conversation.chat_with_ai(self, command)
        else:
            self.speak("I don't know that command.")

    def run_voice_loop(self):
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
                    command = self.listen()
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
