import time


class CommandRegistry:
    def __init__(self):
        self._commands = {}

    def register(self, name, help_text, handler):
        self._commands[name.lower()] = (handler, help_text)

    def unregister(self, name):
        self._commands.pop(name.lower(), None)

    def get_command(self, name):
        return self._commands.get(name.lower())

    def list_commands(self):
        return sorted((name, help) for name, (handler, help) in self._commands.items())

    def execute(self, line):
        if not line or not line.strip():
            return ""
        parts = line.strip().split(maxsplit=1)
        cmd_name = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        entry = self._commands.get(cmd_name)
        if not entry:
            return f"Unknown command: {cmd_name}. Type 'help' for available commands."
        handler, help_text = entry
        try:
            result = handler(arg)
            return result if result else ""
        except Exception as e:
            return f"Error executing {cmd_name}: {e}"


_registry = None


def get_command_registry():
    global _registry
    if _registry is None:
        _registry = CommandRegistry()
        _register_builtins(_registry)
    return _registry


def _register_builtins(registry):
    def _help(arg):
        lines = registry.list_commands()
        parts = [f"{name}: {help}" for name, help in lines]
        return "Available commands: " + ", ".join(parts)

    def _version(arg):
        from core.version import VERSION
        return f"Tech-Note version {VERSION}"

    def _echo(arg):
        return arg

    def _time(arg):
        return time.strftime("%I:%M %p")

    def _date(arg):
        return time.strftime("%A, %B %d, %Y")

    def _datetime(arg):
        return time.strftime("%A, %B %d, %Y at %I:%M %p")

    def _apps(arg):
        from core.menu import build_braillenote_menu
        try:
            menu = build_braillenote_menu(None, None, lambda x: None, None, None)
            names = []
            for child in menu.children or []:
                if child.title:
                    names.append(child.title)
            return "Installed apps: " + ", ".join(sorted(names))
        except Exception:
            return "Could not list apps."

    def _plugins(arg):
        from core.plugin_manager import get_plugin_manager
        pm = get_plugin_manager()
        pm.scan()
        infos = pm.get_all_plugin_info()
        if not infos:
            return "No plugins installed."
        parts = [f"{p['name']} ({p['plugin_type']} v{p['version']})" for p in infos]
        return "Plugins: " + ", ".join(parts)

    def _settings(arg):
        from core.config import SETTINGS_PATH
        import json
        import os
        if not os.path.exists(SETTINGS_PATH):
            return "No settings file found."
        with open(SETTINGS_PATH) as f:
            s = json.load(f)
        if arg:
            key = arg.strip().lower()
            for k, v in s.items():
                if k.lower() == key:
                    return f"{k} = {v}"
            return f"Setting '{arg}' not found."
        keys = ", ".join(sorted(s.keys()))
        return f"Settings: {keys}"

    def _voice(arg):
        from core.plugin_manager import get_plugin_manager
        pm = get_plugin_manager()
        pm.scan()
        if not arg:
            return "Voice command requires a voice name."
        for name, plugin in pm.get_synth_plugins().items():
            voices = plugin.get_voice_names() if hasattr(plugin, 'get_voice_names') else []
            for v in voices:
                if arg.lower() in v.lower():
                    plugin.set_voice(v)
                    return f"Voice set to {v}"
        return f"Voice '{arg}' not found."

    def _rate(arg):
        from core.plugin_manager import get_plugin_manager
        pm = get_plugin_manager()
        pm.scan()
        if not arg:
            val = 0
            for name, plugin in pm.get_synth_plugins().items():
                val = plugin.get_rate() if hasattr(plugin, 'get_rate') else 0
                return f"Rate is {val}" if val == 0 else f"Rate: {val}"
        try:
            val = int(arg)
            for name, plugin in pm.get_synth_plugins().items():
                if hasattr(plugin, 'set_rate'):
                    plugin.set_rate(val)
            return f"Rate set to {val}"
        except ValueError:
            return f"Invalid rate: {arg}"

    def _volume(arg):
        from core.plugin_manager import get_plugin_manager
        pm = get_plugin_manager()
        pm.scan()
        if not arg:
            for name, plugin in pm.get_synth_plugins().items():
                return f"Volume: {plugin.get_volume()}"
            return "Volume: 100"
        try:
            val = max(0, min(100, int(arg)))
            for name, plugin in pm.get_synth_plugins().items():
                if hasattr(plugin, 'set_volume'):
                    plugin.set_volume(val)
            return f"Volume set to {val}"
        except ValueError:
            return f"Invalid volume: {arg}"

    def _reboot(arg):
        import os
        os._exit(42)

    def _shutdown(arg):
        import os
        os._exit(0)

    builtins = [
        ("help", "Show this help message", _help),
        ("version", "Show Tech-Note version", _version),
        ("echo", "Repeat the given text", _echo),
        ("time", "Show current time", _time),
        ("date", "Show current date", _date),
        ("datetime", "Show current date and time", _datetime),
        ("apps", "List installed applications", _apps),
        ("plugins", "List installed plugins", _plugins),
        ("settings", "Show or query a setting: settings [key]", _settings),
        ("voice", "Set voice: voice <name>", _voice),
        ("rate", "Get or set speech rate: rate [value]", _rate),
        ("volume", "Get or set volume: volume [value]", _volume),
        ("reboot", "Restart Tech-Note", _reboot),
        ("shutdown", "Exit Tech-Note", _shutdown),
    ]
    for name, help_text, handler in builtins:
        registry.register(name, help_text, handler)