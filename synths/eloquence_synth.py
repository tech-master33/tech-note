from synths.sapi_synth import SapiSynthBase

class Synth(SapiSynthBase):
    def __init__(self):
        # Strict filter for ViaVoice/Eloquence
        super().__init__(allowed_fragments=["ViaVoice", "Eloquence"])
