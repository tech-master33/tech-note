def get_available_synths():
    return [("SAPI5", "sapi_synth")]


def create_synth(module_name):
    from synths.sapi_synth import SapiSynthBase
    return SapiSynthBase()
