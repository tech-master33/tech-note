def get_available_synths():
    return [("SAPI5", "sapi_synth")]


def create_synth(module_name):
    if module_name == 'sapi_synth':
        from synths.sapi_synth import SapiSynthBase
        return SapiSynthBase()
    raise ValueError(f"Unknown synth module: {module_name}")
