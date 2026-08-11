"""
systmanau — Tech-Note's audio manager.

A systemd-inspired coordinator for everything the app plays: ONE shared
AudioPlayer, priority channels (speech > notify > ui > media > voice),
preemption with resume for long-lived sessions, a pending queue so
deliberate actions (tune a station, play a track) wait for transient
sounds instead of being dropped, playback sessions surfaced as
systmanserv services, ducking automation, and status/control queries
for the `audio` terminal command.

The orchestration is pure Python (threading/time/os only) — the
sounddevice/winmm backends it delegates to are third-party or pre-existing.
"""

import os
import threading
import time

from core.audio_player import AudioPlayer
from core.audio_ducking import AudioDucker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")

# Channel priority: a new request on a channel with priority >= the active
# channel's preempts it; a request on a strictly lower channel is dropped
# (or queued with wait=True). speech is the top of the ladder; voice is the
# bottom, so chat voice messages never cut off music.
CHANNELS = ("speech", "notify", "ui", "media", "voice")
PRIORITY = {"speech": 4, "notify": 3, "ui": 2, "media": 1, "voice": 0}

# NotificationCenter references sound files (message.wav, email.wav...) that
# may not ship yet; resolve_notify_sound() falls back to real sounds/ files.
NOTIFY_FALLBACKS = ("clicked.ogg", "clicked.wav", "Focus.wav")


def resolve_notify_sound(name):
    """Resolve a notification-sound filename to an existing path, falling
    back through sounds/ and sounds/default/, then to any real sound."""
    for candidate in (name,) + NOTIFY_FALLBACKS:
        for d in (SOUNDS_DIR, os.path.join(SOUNDS_DIR, "default")):
            p = os.path.join(d, candidate)
            if os.path.exists(p):
                return p
    return None


class _Session:
    """One playback request. resumable sessions (media/radio/voice) are
    pushed onto the interrupted stack when preempted by a higher channel
    and resumed when the preemptor finishes."""

    __slots__ = ("channel", "kind", "source", "desc", "resumable", "started",
                 "overlay")

    def __init__(self, channel, kind, source, desc, resumable):
        self.channel = channel
        self.kind = kind      # "file" | "url"
        self.source = source
        self.desc = desc
        self.resumable = resumable
        self.started = False  # True once a URL stream has been launched
        self.overlay = False  # True when played over continuing media


class AudioManager:
    def __init__(self, player=None, service_manager=None, ducker=None):
        self._player = player or AudioPlayer()
        self._service_manager = service_manager  # systmanserv manager (optional)
        self._ducker = ducker or AudioDucker()
        self._lock = threading.Lock()
        self._active = None        # currently playing _Session or None
        self._interrupted = []     # stack of resumable sessions awaiting resume
        self._pending = []         # queued sessions waiting on a busy channel
        self._muted = False
        self._last_volume = 1.0
        # Preempt-with-resume: when ON, a higher-priority sound pauses the
        # radio/media and resumes it after. When OFF (the default), the
        # sound simply plays over the continuing media — the stream is never
        # paused or stopped, so "pause while playing" is literally off.
        self._pause_while_playing = False

    # ------------------------------------------------------------------ play

    def play(self, channel, source, kind="file", desc="", resumable=False,
             wait=False):
        """Request playback on a priority channel.

        Returns True if the request was started or queued; False if it was
        dropped because a higher-priority channel is playing (and wait=False).
        """
        if channel not in PRIORITY:
            raise ValueError(f"Unknown audio channel: {channel}")
        session = _Session(channel, kind, source, desc, resumable)
        with self._lock:
            active = self._active
            if active is not None:
                if PRIORITY[channel] < PRIORITY[active.channel]:
                    if wait:
                        self._pending.append(session)
                        return True
                    return False  # dropped: something more important is playing
                # Preempt the active session. With pause_while_playing on, a
                # strictly-higher preemption stacks resumable sessions (a
                # click pauses the radio, which resumes after) — streams are
                # paused in place (ffmpeg keeps running, output silenced) so
                # resume is instant. With it off, a transient just plays
                # over the continuing media (overlay), and same-channel
                # replacement always hard-stops.
                if (active.resumable and not self._pause_while_playing
                        and PRIORITY[active.channel] < PRIORITY[channel]
                        and not session.resumable):
                    session.overlay = True
                    self._start_worker(session)
                    return True
                if (active.resumable and self._pause_while_playing
                        and PRIORITY[active.channel] < PRIORITY[channel]):
                    self._interrupted.append(active)
                    self._player.pause()
                else:
                    self._player.stop()
            self._active = session
        self._start_worker(session)
        return True

    def play_blocking(self, channel, path):
        """Play a sound synchronously (boot/shutdown tones) on the given
        channel, still honoring priority preemption rules."""
        if not os.path.exists(path):
            return False
        session = _Session(channel, "file", path, path, False)
        with self._lock:
            active = self._active
            if active is not None:
                if PRIORITY[channel] < PRIORITY[active.channel]:
                    return False
                if (active.resumable and not self._pause_while_playing
                        and PRIORITY[active.channel] < PRIORITY[channel]):
                    # Mix mode: play the blocking sound over the continuing
                    # media without pausing or stopping the stream.
                    self._player.play_file_blocking(path)
                    return True
                if (active.resumable and self._pause_while_playing
                        and PRIORITY[active.channel] < PRIORITY[channel]):
                    self._interrupted.append(active)
                    self._player.pause()
                else:
                    self._player.stop()
            self._active = session
        try:
            self._player.play_file_blocking(path)
        finally:
            self._session_done(session)
        return True

    # ------------------------------------------------------------- stopping

    def stop_channel(self, channel):
        """Stop playback on a channel and drop any paused/queued sessions of it."""
        with self._lock:
            if self._active is not None and self._active.channel == channel:
                self._player.stop()
                self._active = None
                self._promote_pending_locked() or self._resume_locked()
            removed = [s for s in self._interrupted if s.channel == channel]
            self._interrupted = [s for s in self._interrupted if s.channel != channel]
            self._pending = [s for s in self._pending if s.channel != channel]
            # A paused stream whose session is dropped would otherwise keep
            # running silently — kill it so it isn't orphaned.
            if removed and any(s.kind in ("url", "track") for s in removed):
                self._player.stop()
        self._stop_service(channel)

    def stop_all(self):
        """Stop every channel and clear all paused/queued sessions."""
        with self._lock:
            self._player.stop()
            self._active = None
            self._interrupted = []
            self._pending = []
        for channel in CHANNELS:
            self._stop_service(channel)

    def fade_out(self, duration_ms=1000):
        self._player.fade_out(duration_ms)

    # ------------------------------------------------------------- workers

    def _start_worker(self, session):
        t = threading.Thread(
            target=self._run_session, args=(session,), daemon=True,
            name=f"systmanau-{session.channel}",
        )
        t.start()

    def _run_session(self, session):
        try:
            if session.resumable:
                self._sync_service(session)
            if session.kind == "url":
                self._run_stream_session(
                    session, lambda: self._player.play_url(session.source))
            elif session.kind == "track":
                # Local tracks use the streaming engine too, so they pause
                # and resume mid-track instead of restarting.
                self._run_stream_session(
                    session, lambda: self._player.play_stream_file(session.source))
            else:
                self._run_file(session)
        except Exception:
            with self._lock:
                if self._active is session:
                    self._active = None
                    self._promote_pending_locked() or self._resume_locked()
        finally:
            if not session.overlay:
                self._maybe_stop_service(session.channel)

    def _run_file(self, session):
        self._player.play_file_blocking(session.source)
        self._session_done(session)

    def _run_stream_session(self, session, launch):
        if session.started:
            # A paused stream being resumed: un-silence it in place.
            self._player.resume()
        else:
            if not launch():
                self._session_done(session)
                return
            session.started = True
        self._run_stream_loop(session)

    def _run_stream_loop(self, session):
        while True:
            with self._lock:
                if self._active is not session:
                    return  # preempted or stopped; the new owner handles state
            if not self._player.is_url_playing():
                break  # stream/track ended (or was stopped)
            time.sleep(0.2)
        self._session_done(session)

    def _session_done(self, session):
        """Called by a worker when its session ended (not preempted)."""
        with self._lock:
            if self._active is not session:
                return
            self._active = None
            if not self._promote_pending_locked():
                self._resume_locked()
        self._maybe_stop_service(session.channel)

    def _promote_pending_locked(self):
        """Start the highest-priority queued session, if any. Replacing a
        channel's paused sessions (the user's newest request wins). Returns
        True if a session was promoted. Caller must hold self._lock."""
        if self._active is not None or not self._pending:
            return False
        self._pending.sort(key=lambda s: -PRIORITY[s.channel])
        session = self._pending.pop(0)
        removed = [s for s in self._interrupted if s.channel == session.channel]
        self._interrupted = [s for s in self._interrupted if s.channel != session.channel]
        if removed and any(s.kind in ("url", "track") for s in removed):
            # The promoted request supersedes a paused stream — kill it.
            self._player.stop()
        self._active = session
        self._start_worker(session)
        return True

    def _resume_locked(self):
        """Resume the most recently paused resumable session, if any.
        Caller must hold self._lock."""
        if self._active is not None or not self._interrupted:
            return False
        session = self._interrupted.pop()
        self._active = session
        self._start_worker(session)
        return True

    # --------------------------------------------------------------- status

    def status(self):
        with self._lock:
            active = self._active
            return {
                "channel": active.channel if active else None,
                "source": active.source if active else None,
                "desc": active.desc if active else None,
                "kind": active.kind if active else None,
                "paused": [s.channel for s in self._interrupted],
                "pending": [s.channel for s in self._pending],
                "volume": self.get_volume(),
                "eq": self._player.get_eq_preset(),
                "muted": self._muted,
                "ducking": self._ducker.get_enabled(),
                "pause_while_playing": self._pause_while_playing,
            }

    # ------------------------------------------------------------- controls

    def get_volume(self):
        return round(self._player.get_volume() * 100)

    def set_volume(self, pct):
        pct = max(0, min(100, int(pct)))
        self._player.set_volume(pct / 100.0)
        if not self._muted:
            self._last_volume = pct / 100.0

    def set_muted(self, muted):
        self._muted = bool(muted)
        self._player.set_volume(0.0 if muted else self._last_volume)

    def set_pause_while_playing(self, enabled):
        """Toggle preempt-with-resume. When off, a higher-priority sound
        hard-stops radio/media instead of pausing it for later resume."""
        self._pause_while_playing = bool(enabled)

    def get_eq(self):
        return self._player.get_eq_preset()

    def set_eq(self, name):
        self._player.set_eq_preset(name)

    def duck(self):
        self._ducker.duck()

    def unduck(self):
        self._ducker.unduck()

    def set_ducking(self, enabled):
        self._ducker.set_enabled(bool(enabled))

    def get_ducker(self):
        """The one app-wide ducker — the synth shares it so ducking state
        has a single source of truth."""
        return self._ducker

    # ------------------------------------------------------------ services

    def set_service_manager(self, m):
        """Attach the systmanserv manager so long-lived playback sessions
        (radio/media/voice) surface as named services."""
        self._service_manager = m

    def _sync_service(self, session):
        m = self._service_manager
        if m is None or not session.resumable:
            return
        name = session.channel
        if m.get(name) is None:
            m.register(
                name,
                description=f"Audio: {session.desc}",
                run=None,
                stop=lambda n=name: self.stop_channel(n),
                enabled=True,
                persist=False,
            )
        svc = m.get(name)
        if svc is not None:
            svc.description = f"Audio: {session.desc}"
            if not svc.enabled:
                m.enable(name)
            m.start(name)

    def _stop_service(self, channel):
        m = self._service_manager
        if m is None:
            return
        m.stop(channel)

    def _maybe_stop_service(self, channel):
        with self._lock:
            active_channel = self._active.channel if self._active else None
            stacked = any(s.channel == channel for s in self._interrupted)
            queued = any(s.channel == channel for s in self._pending)
        if active_channel != channel and not stacked and not queued:
            self._stop_service(channel)


_manager = None
_manager_lock = threading.Lock()


def get_audio_manager():
    """Module-level singleton — the app's one audio coordinator."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = AudioManager()
    return _manager
