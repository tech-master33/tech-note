def get_available_synths():
    base = [("SAPI5", "sapi_synth")]
    pm = _get_plugin_manager()
    for name in pm.get_synth_plugins():
        base.append((f"Plugin: {name}", f"plugin:{name}"))
    return base


def create_synth(module_name):
    if module_name == 'sapi_synth':
        from synths.sapi_synth import SapiSynthBase
        return SapiSynthBase()
    if module_name.startswith('plugin:'):
        name = module_name[7:]
        pm = _get_plugin_manager()
        plugins = pm.get_synth_plugins()
        if name in plugins:
            return plugins[name]
    raise ValueError(f"Unknown synth module: {module_name}")


def _get_plugin_manager():
    from core.plugin_manager import get_plugin_manager as _pm
    pm = _pm()
    pm.scan()
    return pm
