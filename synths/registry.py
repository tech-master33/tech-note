import os
import subprocess


def get_available_synths():
    base = [("SAPI5", "sapi_synth")]
    if _find_32bit_python() is not None:
        base.append(("SAPI5 (32-bit bridge)", "bridge:sapi32"))
    pm = _get_plugin_manager()
    for name in pm.get_synth_plugins():
        base.append((f"Plugin: {name}", f"plugin:{name}"))
    for name in pm.get_bridge_synth_plugins():
        base.append((f"Plugin: {name}", f"plugin:{name}"))
    return base


def create_synth(module_name):
    if module_name == 'sapi_synth':
        from synths.sapi_synth import SapiSynthBase
        return SapiSynthBase()
    if module_name == 'bridge:sapi32':
        # A 32-bit TTS engine hosted in a helper process, driven by the
        # 64-bit app over a local socket (see core/tts_bridge.py).
        from core.tts_bridge import BridgeTTS
        return BridgeTTS()
    if module_name.startswith('plugin:'):
        name = module_name[7:]
        pm = _get_plugin_manager()
        # bits:32 synth plugins run in the 32-bit bridge helper; every
        # DLL they load happens there. Everything else loads in-process.
        if name in pm.get_bridge_synth_plugins():
            from core.plugin_bridge import BridgePluginSynth
            return BridgePluginSynth(name)
        plugins = pm.get_synth_plugins()
        if name in plugins:
            return plugins[name]
    raise ValueError(f"Unknown synth module: {module_name}")


def get_synth_bits(module_name):
    """Optional architecture hint for a synth: '32', '64', or '' (unknown /
    not required). Plugins may declare it in their manifest as `bits`."""
    if module_name == 'bridge:sapi32':
        return '32'
    if module_name == 'sapi_synth':
        return '64'
    if module_name.startswith('plugin:'):
        name = module_name[7:]
        pm = _get_plugin_manager()
        if name in pm.get_bridge_synth_plugins():
            return '32'
        info = pm.get_plugin_info(name)
        if info:
            return info.get('bits', '')
    return ''


def _find_32bit_python():
    """Locate a 32-bit Python interpreter for the TTS bridge, or None."""
    env = os.environ.get("TECHNOTE_BRIDGE_PYTHON")
    if env and os.path.exists(env):
        return env
    try:
        out = subprocess.run(["py", "-0p"], capture_output=True, text=True,
                             timeout=10).stdout
        for line in out.splitlines():
            if "-32" in line.lower() and "python.exe" in line.lower():
                path = line.split()[-1].strip().strip('"')
                if os.path.exists(path):
                    return path
    except Exception:
        pass
    try:
        programs = os.environ.get("LOCALAPPDATA", "")
        root = os.path.join(programs, "Programs", "Python")
        if os.path.isdir(root):
            for entry in sorted(os.listdir(root), reverse=True):
                if "-32" in entry.lower():
                    exe = os.path.join(root, entry, "python.exe")
                    if os.path.exists(exe):
                        return exe
    except Exception:
        pass
    return None


def _get_plugin_manager():
    from core.plugin_manager import get_plugin_manager as _pm
    pm = _pm()
    pm.scan()
    return pm
