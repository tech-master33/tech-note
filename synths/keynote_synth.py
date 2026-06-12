from synths.sapi_synth import SapiSynthBase

class Synth(SapiSynthBase):
    def __init__(self):
        # Strict filter for Keynote Gold
        super().__init__(allowed_fragments=["Keynote"])
