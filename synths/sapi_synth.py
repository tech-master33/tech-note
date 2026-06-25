import comtypes.client
import re
import time
from core.audio_ducking import AudioDucker
import core.pronunciation_dict

class SapiSynthBase:
    def __init__(self, voice_name=None, allowed_fragments=None):
        self.engine = None
        self.is_valid = False
        try:
            self.engine = comtypes.client.CreateObject("SAPI.SpVoice")
            self.is_valid = True
        except Exception:
            self.is_valid = False
            return
        self.allowed_fragments = allowed_fragments
        self.punctuation_level = "Some"
        self.speak_punctuation = False
        self._pitch = 50
        self._capital_pitch_change = "Off"
        self._ducker = AudioDucker()
        self._default_voice_index = None
        self._default_rate = None
        self._default_pitch = None

        if allowed_fragments:
            self._set_voice_by_fragments(allowed_fragments)
        elif voice_name:
            self.set_voice(voice_name)

        self.save_defaults()
        core.pronunciation_dict.load()
        self._speech_history = []
        self._history_max = 50

    def save_defaults(self):
        try:
            self._default_voice_index = self.get_voice_index()
            self._default_rate = self.engine.Rate
            self._default_pitch = self._pitch
        except:
            pass

    def apply_profile(self, voice_index=None, rate=None, pitch=None):
        if voice_index is not None:
            self.set_voice_by_index(voice_index)
        if rate is not None:
            self.set_rate(rate)
        if pitch is not None:
            self.set_pitch(pitch)

    def _set_voice_by_fragments(self, fragments):
        for voice in self.engine.GetVoices():
            desc = voice.GetDescription()
            for frag in fragments:
                if frag.lower() in desc.lower():
                    self.engine.Voice = voice
                    return True
        return False

    def set_voice(self, voice_name):
        for voice in self.engine.GetVoices():
            if voice_name.lower() in voice.GetDescription().lower():
                saved_rate = self.engine.Rate
                saved_volume = self.engine.Volume
                self.engine.Voice = voice
                self.engine.Rate = saved_rate
                self.engine.Volume = saved_volume
                return True
        return False

    def get_rate(self):
        try:
            return self.engine.Rate
        except:
            return 0

    def set_rate(self, value):
        try:
            self.engine.Rate = max(-10, min(30, int(value)))
        except:
            pass

    def get_volume(self):
        try:
            return self.engine.Volume
        except:
            return 100

    def set_volume(self, value):
        try:
            self.engine.Volume = max(0, min(100, int(value)))
        except:
            pass

    def get_voice_names(self):
        try:
            return [v.GetDescription() for v in self.engine.GetVoices()]
        except:
            return []

    def get_current_voice_name(self):
        try:
            return self.engine.Voice.GetDescription()
        except:
            return ""

    def set_voice_by_index(self, index):
        try:
            voices = self.engine.GetVoices()
            if 0 <= index < len(voices):
                saved_rate = self.engine.Rate
                saved_volume = self.engine.Volume
                self.engine.Voice = voices[index]
                self.engine.Rate = saved_rate
                self.engine.Volume = saved_volume
                return True
        except:
            pass
        return False

    def get_voice_index(self):
        try:
            current = self.engine.Voice.GetDescription()
            for i, v in enumerate(self.engine.GetVoices()):
                if v.GetDescription() == current:
                    return i
        except:
            pass
        return 0

    def set_punctuation_level(self, level):
        self.punctuation_level = level

    def get_pitch(self):
        return self._pitch

    def set_pitch(self, value):
        self._pitch = max(0, min(100, int(value)))

    def get_capital_pitch_change(self):
        return self._capital_pitch_change

    def set_capital_pitch_change(self, value):
        if value in ("Off", "Say Cap", "Raise Pitch"):
            self._capital_pitch_change = value

    @staticmethod
    def _filter_punctuation(text, level):
        if level == "All":
            return text
        if level == "None":
            return re.sub(r'[^\w\s]', '', text)
        if level == "Some":
            return re.sub(r'[^\w\s.,!?;:\-\'"]', '', text)
        if level == "Most":
            return re.sub(r'[^\w\s.,!?;:\-\'\"()\[\]{}@#$%^&*+=<>/\\|~]', '', text)
        return text

    def _apply_capital_pitch(self, text):
        if self._capital_pitch_change == "Off":
            return text, False
        if self._capital_pitch_change == "Say Cap":
            return re.sub(r'([A-Z])', r'cap \1', text), False
        if self._capital_pitch_change == "Raise Pitch":
            text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            text = re.sub(r'([A-Z]+)', r'<prosody pitch="+40%">\1</prosody>', text)
            text = '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis">' + text + '</speak>'
            return text, True
        return text, False

    def get_volume_ducking(self):
        return self._ducker.get_enabled()

    def set_volume_ducking(self, enabled):
        self._ducker.set_enabled(enabled)

    def get_speech_history(self):
        return list(self._speech_history)

    def get_history_max(self):
        return self._history_max

    def set_history_max(self, value):
        self._history_max = max(10, min(200, int(value)))

    def repeat_last(self):
        if self._speech_history:
            self._speak_direct(self._speech_history[-1])

    def _engine_stop(self):
        if self.engine:
            self.engine.Speak("", 2)

    def speak(self, text, interrupt=True):
        if not self.engine:
            return

        text = self._filter_punctuation(text, self.punctuation_level)

        if interrupt:
            self._engine_stop()
        self._speak_direct(text)

    def _speak_direct(self, text):
        if not self.engine:
            return

        text, use_xml = self._apply_capital_pitch(text)

        if not use_xml and self._pitch != 50:
            safe = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            text = f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"><pitch absmiddle="{self._pitch}">{safe}</pitch></speak>'
            use_xml = True

        self._ducker.duck()
        try:
            flags = 1
            if use_xml:
                flags |= 8
            self.engine.Speak(text, flags)
            self._ducker.schedule_unduck(text, self.engine.Rate if self.engine else 0)
            self._speech_history.append(text)
            if len(self._speech_history) > self._history_max:
                self._speech_history.pop(0)
        except Exception as e:
            print(f"Speech error: {e}")
            self._ducker.unduck()

    def stop(self):
        self._engine_stop()

    def wait_until_done(self, timeout_ms=5000):
        if self.engine:
            self.engine.WaitUntilDone(timeout_ms)

    def reset_temp_params(self):
        if self._default_voice_index is not None:
            self.set_voice_by_index(self._default_voice_index)
        if self._default_rate is not None:
            self.set_rate(self._default_rate)
        if self._default_pitch is not None:
            self._pitch = self._default_pitch

    def set_temp_params(self, rate=None, pitch=None, voice_index=None):
        if voice_index is not None:
            self.set_voice_by_index(voice_index)
        if rate is not None:
            self.set_rate(rate)
        if pitch is not None:
            self._pitch = max(0, min(100, int(pitch)))
