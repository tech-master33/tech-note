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

    def _run(arg):
        if not arg:
            return "Usage: run <app_name>. Available: " + ", ".join(_get_app_list())
        target = arg.strip().lower()
        try:
            from core.menu import build_braillenote_menu
            from main import _run_app_by_name
            if _run_app_by_name(target):
                return f"Running {target}."
            else:
                return f"App '{target}' not found."
        except Exception:
            return f"Could not run {target}."

    def _switch(arg):
        if not arg:
            return "Usage: switch <app_name>. Use 'apps' to list."
        try:
            from main import _switch_to_app
            if _switch_to_app(arg.strip()):
                return f"Switched to {arg}."
            else:
                return f"App '{arg}' not found."
        except Exception:
            return f"Could not switch to {arg}."

    def _get_app_list():
        try:
            from core.menu import build_braillenote_menu
            menu = build_braillenote_menu(None, None, lambda x: None, None, None)
            return [child.title for child in (menu.children or []) if child.title]
        except Exception:
            return []

    def _services(arg):
        from core.systmanserv import get_manager
        m = get_manager()
        parts = arg.split()
        if not parts:
            statuses = m.status()
            if not statuses:
                return "No services registered."
            return "Services: " + ", ".join(
                f"{s['name']} {s['state']}" for s in statuses
            )
        action = parts[0].lower()
        name = parts[1].strip() if len(parts) > 1 else ""
        if action == "log":
            if not name:
                return "Usage: services log <name>"
            entries = m.get_log(name)  # live history + on-disk journal
            if not entries:
                return f"No run history for {name}."
            lines = []
            for e in reversed(entries):
                ts = time.strftime("%H:%M:%S", time.localtime(e["time"]))
                status = "ok" if e["ok"] else "error"
                dur = f"{e['duration']:.1f}s"
                desc = f" ({e['desc']})" if e.get("desc") else ""
                err = f" - {e['error']}" if e.get("error") else ""
                lines.append(f"{ts} {status} {dur}{desc}{err}")
            return f"Log for {name}: " + "; ".join(lines)
        if m.get(action) is not None and not name:
            # `services <name>` -> full status and statistics for one service
            info = {s["name"]: s for s in m.status()}.get(action)
            if info:
                bits = [f"{action} {info['state']}"]
                bits.append("enabled" if info["enabled"] else "disabled")
                bits.append(f"{info['runs']} runs")
                if info["successes"] or info["failures"]:
                    bits.append(f"{info['successes']} ok, {info['failures']} failed")
                if info.get("avg_duration") is not None:
                    bits.append(f"avg {info['avg_duration']}s")
                if info["pending"] is not None:
                    bits.append(f"{info['pending']} pending")
                if info["restart"] != "no":
                    bits.append(f"restart {info['restart']} ({info['max_restarts']} max)")
                if info["consecutive_failures"]:
                    bits.append(f"{info['consecutive_failures']} failures in a row")
                if info.get("last_error"):
                    bits.append(f"last error: {info['last_error']}")
                return "Service: " + ", ".join(bits)
        if not name:
            return "Usage: services <log|start|stop|restart|enable|disable> <name>"
        if action == "start":
            if m.start(name):
                return f"{name} started."
            svc = m.get(name)
            if not svc:
                return f"Service '{name}' not found."
            if not svc.enabled:
                return f"{name} is disabled. Enable it first: services enable {name}"
            return f"{name} is already running."
        if action == "stop":
            if m.stop(name):
                return f"{name} stopped."
            return f"Service '{name}' not found."
        if action == "restart":
            if m.restart(name):
                return f"{name} restarted."
            svc = m.get(name)
            if not svc:
                return f"Service '{name}' not found."
            if not svc.enabled:
                return f"{name} is disabled. Enable it first: services enable {name}"
            return f"Could not restart {name}."
        if action == "enable":
            if m.enable(name):
                return f"{name} enabled."
            return f"Service '{name}' not found."
        if action == "disable":
            if m.disable(name):
                return f"{name} disabled."
            return f"Service '{name}' not found."
        return "Usage: services <log|start|stop|restart|enable|disable> <name>"

    def _audio(arg):
        from core.systmanau import get_audio_manager
        am = get_audio_manager()
        parts = arg.split()
        if not parts or parts[0].lower() == "status":
            st = am.status()
            head = (f"Now playing {st['desc'] or st['source']} on {st['channel']}"
                    if st["channel"] else "No audio playing")
            paused = f", paused: {', '.join(st['paused'])}" if st["paused"] else ""
            pending = f", pending: {', '.join(st['pending'])}" if st["pending"] else ""
            muted = "muted" if st["muted"] else f"volume {st['volume']}"
            ducking = "ducking on" if st["ducking"] else "ducking off"
            pause = ("pause while playing on" if st["pause_while_playing"]
                     else "pause while playing off")
            return f"{head}{paused}{pending}. {muted}, EQ {st['eq']}, {ducking}, {pause}."
        action = parts[0].lower()
        if action == "stop":
            if len(parts) > 1:
                am.stop_channel(parts[1])
                return f"Stopped {parts[1]}."
            am.stop_all()
            return "Stopped all audio."
        if action in ("vol", "volume"):
            if len(parts) > 1:
                try:
                    am.set_volume(int(parts[1]))
                    return f"Volume set to {parts[1]}."
                except ValueError:
                    return f"Invalid volume: {parts[1]}"
            return f"Volume is {am.get_volume()}."
        if action == "mute":
            am.set_muted(True)
            return "Muted."
        if action == "unmute":
            am.set_muted(False)
            return "Unmuted."
        if action == "duck":
            am.duck()
            return "Ducked."
        if action == "unduck":
            am.unduck()
            return "Unducked."
        if action == "eq":
            if len(parts) > 1:
                am.set_eq(parts[1])
                return f"EQ set to {parts[1]}."
            return f"EQ is {am.get_eq()}."
        if action == "pause":
            if len(parts) > 1:
                on = parts[1].lower() in ("on", "1", "true", "yes")
                am.set_pause_while_playing(on)
                return f"Pause while playing {'on' if on else 'off'}."
            return ("Pause while playing is on." if am.status()["pause_while_playing"]
                    else "Pause while playing is off.")
        return "Usage: audio <status|stop [channel]|vol [value]|mute|unmute|duck|unduck|eq [preset]|pause [on|off]>"

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
        ("run", "Launch an app: run <app_name>", _run),
        ("switch", "Switch to a running app: switch <app_name>", _switch),
        ("services", "Manage background services: services [log|start|stop|restart|enable|disable <name>]", _services),
        ("audio", "Control audio: audio [status|stop|vol|mute|unmute|duck|unduck|eq]", _audio),
        ("reboot", "Restart Tech-Note", _reboot),
        ("shutdown", "Exit Tech-Note", _shutdown),
    ]
    for name, help_text, handler in builtins:
        registry.register(name, help_text, handler)