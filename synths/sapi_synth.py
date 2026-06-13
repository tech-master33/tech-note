import comtypes.client
import re
import time
from core.audio_ducking import AudioDucker

class SapiSynthBase:
    def __init__(self, voice_name=None, allowed_fragments=None):
        self.engine = comtypes.client.CreateObject("SAPI.SpVoice")
        self.is_valid = True
        self.allowed_fragments = allowed_fragments
        self.punctuation_level = "Some"
        self.speak_punctuation = False
        self._pitch = 50
        self._capital_pitch_change = "Off"
        self._ducker = AudioDucker()
        
        if allowed_fragments:
            self._set_voice_by_fragments(allowed_fragments)
        elif voice_name:
            self.set_voice(voice_name)

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
                self.engine.Voice = voice
                return True
        return False

    def get_rate(self):
        try:
            return self.engine.Rate
        except:
            return 0

    def set_rate(self, value):
        try:
            self.engine.Rate = max(-10, min(10, int(value)))
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
                self.engine.Voice = voices[index]
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

    def set_volume_ducking(self, enabled):
        self._ducker.set_enabled(enabled)

    def speak(self, text, interrupt=True):
        if not self.engine:
            return
        
        text = self._filter_punctuation(text, self.punctuation_level)
        text, use_xml = self._apply_capital_pitch(text)
        self._ducker.duck()
        try:
            flags = 1
            if interrupt:
                flags |= 2
            if use_xml:
                flags |= 8
            self.engine.Speak(text, flags)
            self._ducker.schedule_unduck(text, self.engine.Rate if self.engine else 0)
        except Exception as e:
            print(f"Speech error: {e}")
            self._ducker.unduck()

    def stop(self):
        if self.engine:
            self.engine.Speak("", 1 | 2)

    def reset_temp_params(self):
        pass

    def set_temp_params(self, rate=None, pitch=None):
        pass
