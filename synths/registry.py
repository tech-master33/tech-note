def get_available_synths():
    synths = [("SAPI5", "sapi_synth")]

    try:
        from synths.eloquence_synth import Synth
        inst = Synth()
        if inst.get_voice_names():
            synths.append(("Eloquence", "eloquence_synth"))
    except Exception:
        pass

    try:
        from synths.keynote_synth import Synth
        inst = Synth()
        if inst.get_voice_names():
            synths.append(("Keynote", "keynote_synth"))
    except Exception:
        pass

    try:
        from synths.nvda import Synth
        inst = Synth()
        if inst.test():
            synths.append(("NVDA", "nvda"))
    except Exception:
        pass

    return synths

def create_synth(module_name):
    if module_name == "sapi_synth":
        from synths.sapi_synth import SapiSynthBase
        return SapiSynthBase()
    elif module_name == "eloquence_synth":
        from synths.eloquence_synth import Synth
        return Synth()
    elif module_name == "keynote_synth":
        from synths.keynote_synth import Synth
        return Synth()
    elif module_name == "nvda":
        from synths.nvda import Synth
        return Synth()
    return None
