import comtypes.client
import time

class SapiSynthBase:
    def __init__(self, voice_name=None, allowed_fragments=None):
        self.engine = comtypes.client.CreateObject("SAPI.SpVoice")
        self.is_valid = True
        self.allowed_fragments = allowed_fragments
        
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

    def speak(self, text, interrupt=True):
        if not self.engine:
            return
        
        try:
            flags = 1
            if interrupt:
                flags |= 2
            self.engine.Speak(text, flags)
        except Exception as e:
            print(f"Speech error: {e}")

    def stop(self):
        if self.engine:
            self.engine.Speak("", 1 | 2)

    def reset_temp_params(self):
        pass

    def set_temp_params(self, rate=None, pitch=None):
        pass
