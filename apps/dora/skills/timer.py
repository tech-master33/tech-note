import threading
import time
import numpy as np
import sounddevice as sd

_state = {'timer_running': False, 'alarm_active': False}

def is_alarm_active():
    return _state['alarm_active']

def _generate_tone(freq=880, duration=0.5, samplerate=22050):
    t = np.linspace(0, duration, int(samplerate * duration), False)
    tone = np.sin(freq * t * 2 * np.pi) * 0.3
    silence = np.zeros(int(samplerate * 0.1))
    return np.concatenate([tone, silence])

def _play_alarm_loop(stop_event):
    tone = _generate_tone()
    while not stop_event.is_set():
        sd.play(tone, samplerate=22050, blocking=False)
        time.sleep(0.6)

def start_timer(assistant, command):
    words = command.split()
    minutes = 0
    for w in words:
        if w.isdigit():
            minutes = int(w)
            break
    if minutes <= 0:
        assistant.speak("Please specify the number of minutes.")
        return
    if _state['timer_running']:
        assistant.speak("A timer is already running.")
        return
    assistant.speak(f"Timer set for {minutes} minutes.")
    _state['timer_running'] = True
    t = threading.Thread(target=_timer_logic, args=(assistant, minutes), daemon=True)
    t.start()

def _timer_logic(assistant, minutes):
    time.sleep(minutes * 60)
    if _state['timer_running']:
        _state['alarm_active'] = True
        assistant.speak("Time is up!")
        stop_event = threading.Event()
        alarm_thread = threading.Thread(target=_play_alarm_loop, args=(stop_event,), daemon=True)
        alarm_thread.start()
        while _state['alarm_active']:
            time.sleep(0.1)
        stop_event.set()
        sd.stop()
        _state['timer_running'] = False

def stop_timer(assistant, command=None):
    if _state['alarm_active']:
        _state['alarm_active'] = False
        sd.stop()
        assistant.speak("Alarm stopped.")
        _state['timer_running'] = False
        return True
    elif _state['timer_running']:
        _state['timer_running'] = False
        assistant.speak("Timer cancelled.")
        return True
    return False
