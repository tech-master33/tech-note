"""
syst — Tech-Note's unified system layer.

The daemon system grew up into a family: systmanserv runs background
services, systmanau owns the audio device, and this module is the umbrella
that ties them together under one name — `syst`. It presents a single
facade (services + audio + one status view) so apps, the terminal, and
plugins have one entry point instead of reaching into each subsystem.

The orchestration is pure Python (threading/time/os only); the
sounddevice/winmm backends it delegates to are third-party or pre-existing.
"""

import threading

_service_manager = None
_audio_manager = None
_manager_lock = threading.Lock()


def services():
    """The systmanserv service manager singleton."""
    global _service_manager
    if _service_manager is None:
        with _manager_lock:
            if _service_manager is None:
                from core.systmanserv import get_manager
                _service_manager = get_manager()
    return _service_manager


def audio():
    """The systmanau audio manager singleton."""
    global _audio_manager
    if _audio_manager is None:
        with _manager_lock:
            if _audio_manager is None:
                from core.systmanau import get_audio_manager
                _audio_manager = get_audio_manager()
    return _audio_manager


class Syst:
    """One facade over the syst subsystems: services and audio."""

    def get_services(self):
        return services()

    def get_audio(self):
        return audio()

    # ------------------------------------------------------------------ state

    def status(self):
        """Unified status: what's running, what's playing, and the audio
        policy — everything the old daemon listing showed plus audio."""
        sm = services()
        am = audio()
        try:
            running = [n for n in sm.names() if sm.get(n).state in ("running", "restarting")]
        except Exception:
            running = []
        ast = am.status()
        return {
            "services": running,
            "service_count": len(running),
            "now_playing": ast.get("channel"),
            "playing_desc": ast.get("desc"),
            "paused": ast.get("paused", []),
            "pending": ast.get("pending", []),
            "volume": ast.get("volume"),
            "muted": ast.get("muted"),
            "pause_while_playing": ast.get("pause_while_playing"),
            "ducking": ast.get("ducking"),
            "eq": ast.get("eq"),
        }

    # -------------------------------------------------------------- lifecycle

    def start(self):
        """Start all registered services (autosave, session-save, ...)."""
        services().start_all()

    def shutdown(self):
        """Stop every service and every audio channel."""
        services().shutdown_all()
        audio().stop_all()

    # ----------------------------------------------------------- passthroughs

    def run_service(self, name):
        return services().start(name)

    def stop_service(self, name):
        return services().stop(name)

    def restart_service(self, name):
        return services().restart(name)

    def run_once(self, name, run, description=""):
        return services().run_once(name, run, description)

    def submit(self, queue_name, run, description=""):
        return services().submit(queue_name, run, description)

    def audio_play(self, channel, source, kind="file", desc="", resumable=False,
                   wait=False):
        return audio().play(channel, source, kind=kind, desc=desc,
                            resumable=resumable, wait=wait)

    def audio_stop(self, channel=None):
        if channel:
            audio().stop_channel(channel)
        else:
            audio().stop_all()


_syst = None
_syst_lock = threading.Lock()


def get_syst():
    """Module-level singleton — the app's one `syst` entry point."""
    global _syst
    if _syst is None:
        with _syst_lock:
            if _syst is None:
                _syst = Syst()
    return _syst
