class Synth:
    def __init__(self):
        self.engine = None
        self._voice_names = []
        self.is_valid = False
        self._rate = 0
        self._volume = 100
        self._voice_index = 0
        self._voices = []
        try:
            import comtypes.client
            self.engine = comtypes.client.CreateObject("Speech.Voice")
            self.is_valid = True
            self._enum_voices()
        except Exception:
            pass

    def _enum_voices(self):
        try:
            tokens = self.engine.GetVoices()
            self._voices = []
            self._voice_names = []
            for i in range(tokens.Count):
                v = tokens.Item(i)
                self._voices.append(v)
                self._voice_names.append(v.GetDescription())
        except Exception:
            self._voice_names = ["Default"]

    def speak(self, text, interrupt=False):
        if not self.is_valid:
            return
        if interrupt:
            self.stop()
        try:
            self.engine.Rate = self._rate
            self.engine.Volume = self._volume
            self.engine.Speak(text)
        except Exception:
            pass

    def stop(self):
        if self.is_valid:
            try:
                self.engine.Speak("", 3)
            except Exception:
                pass

    def get_rate(self):
        return self._rate

    def set_rate(self, value):
        self._rate = max(-10, min(10, int(value)))
        if self.is_valid:
            try:
                self.engine.Rate = self._rate
            except Exception:
                pass

    def get_volume(self):
        return self._volume

    def set_volume(self, value):
        self._volume = max(0, min(100, int(value)))
        if self.is_valid:
            try:
                self.engine.Volume = self._volume
            except Exception:
                pass

    def get_voice_names(self):
        return self._voice_names

    def set_voice(self, voice_name):
        for i, name in enumerate(self._voice_names):
            if voice_name.lower() in name.lower():
                self.set_voice_by_index(i)
                return True
        return False

    def set_voice_by_index(self, index):
        if 0 <= index < len(self._voices):
            self._voice_index = index
            try:
                self.engine.Voice = self._voices[index]
            except Exception:
                pass

    def get_voice_index(self):
        return self._voice_index

    def get_current_voice_name(self):
        if 0 <= self._voice_index < len(self._voice_names):
            return self._voice_names[self._voice_index]
        return ""

    def set_punctuation_level(self, level):
        pass

    def get_pitch(self):
        return 50

    def set_pitch(self, value):
        pass

    def get_capital_pitch_change(self):
        return "Off"

    def set_capital_pitch_change(self, value):
        pass

    def get_volume_ducking(self):
        return False

    def set_volume_ducking(self, enabled):
        pass

    def reset_temp_params(self):
        pass

    def set_temp_params(self, rate=None, pitch=None):
        pass
