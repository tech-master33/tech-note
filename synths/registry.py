def get_available_synths():
    synths = [("SAPI5", "sapi_synth")]

    try:
        from synths.sapi4_synth import Synth
        inst = Synth()
        if inst.is_valid:
            synths.append(("SAPI4", "sapi4_synth"))
    except Exception:
        pass

    return synths

def create_synth(module_name):
    if module_name == "sapi_synth":
        from synths.sapi_synth import SapiSynthBase
        return SapiSynthBase()
    elif module_name == "sapi4_synth":
        from synths.sapi4_synth import Synth
        return Synth()
    else:
        from synths.sapi_synth import SapiSynthBase
        return SapiSynthBase()
