"""
systmanserv — Tech-Note's in-process service manager.

A systemd-inspired service manager that owns the lifecycle of the app's
background tasks (its "daemons"): registration, start/stop/restart,
enable/disable for boot, interval and one-shot scheduling, status reporting,
and clean shutdown. Pure Python (threading/time/json/os only) — no
OS-specific APIs, so it runs identically on any platform.

For now systmanserv is used only for services.
"""

import json
import os
import threading
import time
from collections import deque
from core.config import TECH_SOFT

SERVICES_FILE = os.path.join(TECH_SOFT, "services.json")
JOURNAL_FILE = os.path.join(TECH_SOFT, "services_journal.jsonl")

JOURNAL_MAX_PER_SERVICE = 200  # in-memory journal cap per service
JOURNAL_COMPACT_AT = 1000      # total journal lines that trigger compaction
JOURNAL_KEEP = 500             # lines kept when compacting

STATE_STOPPED = "stopped"
STATE_RUNNING = "running"
STATE_DONE = "done"
STATE_ERRORED = "errored"
STATE_RESTARTING = "restarting"

DEFAULT_TICK = 1.0

QUEUE_TICK = 1.0  # min gap between queued jobs (scheduler granularity)

HISTORY_MAX = 30  # run-history entries kept per service (journalctl-style)


class Service:
    """A named background task. Runs on an interval (timer-style) or once
    (oneshot), with optional stop cleanup. Every run happens in its own
    worker thread, so long-running work never blocks the scheduler and
    interval runs never overlap."""

    def __init__(self, name, description="", run=None, stop=None, interval=None,
                 oneshot=False, enabled=True, persist=True, restart="no",
                 restart_sec=1.0, max_restarts=3):
        self.name = name
        self.description = description
        self.run = run            # callable, invoked on each run / once for oneshot
        self.stop = stop          # optional callable, invoked on stop/shutdown
        self.interval = interval  # seconds; None means no auto-repeat
        self.oneshot = oneshot    # run once, then state -> done
        self.enabled = enabled    # boot policy: started by start_all()
        self.persist = persist    # whether enable/disable policy is saved
        # systemd-style restart policy
        self.restart = restart          # "no" | "on-failure" | "always"
        self.restart_sec = restart_sec  # delay before an automatic restart
        self.max_restarts = max_restarts  # cap on consecutive-failure restarts
        self.consecutive_failures = 0
        self._restart_at = None
        self.state = STATE_STOPPED
        self.last_run = 0.0
        self.runs = 0
        self.last_error = None
        self.successes = 0
        self.failures = 0
        self.total_time = 0.0
        self.history = deque(maxlen=HISTORY_MAX)  # {time, ok, duration, error, desc}
        self._worker = None
        self._lock = threading.Lock()


class ServiceManager:
    def __init__(self):
        self._services = {}
        self._queues = {}  # queue_name -> deque of (run, description) jobs
        self._queue_errors = {}  # queue_name -> number of failed jobs
        self._queue_last_error = {}  # queue_name -> most recent job error
        self._lock = threading.Lock()
        self._scheduler = None
        self._stop_event = threading.Event()
        self._policy = self._load_policy()
        self._journal = self._load_journal()  # name -> deque of run records

    # ---------------------------------------------------------------- registry

    def register(self, name, description="", run=None, stop=None, interval=None,
                 oneshot=False, enabled=True, persist=True, restart="no",
                 restart_sec=1.0, max_restarts=3):
        """Register (or replace) a service. The persisted enable/disable
        policy wins over the default `enabled` value. `restart` mirrors
        systemd Restart=: "no" (default), "on-failure", or "always"; a
        failed run is retried after `restart_sec` up to `max_restarts`
        consecutive failures, then the service is marked errored."""
        svc = Service(
            name, description, run, stop, interval, oneshot,
            enabled=self._policy.get(name, enabled),
            persist=persist, restart=restart, restart_sec=restart_sec,
            max_restarts=max_restarts,
        )
        # Seed the live history from the on-disk journal so `services log`
        # shows pre-restart runs.
        if name in self._journal and self._journal[name]:
            svc.history.extend(list(self._journal[name])[-HISTORY_MAX:])
        with self._lock:
            self._services[name] = svc
        return svc

    def get(self, name):
        return self._services.get(name)

    def names(self):
        return sorted(self._services.keys())

    def run_once(self, name, run, description=""):
        """Register (replacing any previous instance) and start a short-lived
        oneshot service in its own worker thread — fire-and-forget for
        per-action background work. A second call while the first is still
        running starts a fresh service; the old one finishes detached, so
        concurrent actions never collide."""
        self.register(name, description=description, run=run, oneshot=True,
                      enabled=True, persist=False)
        return self.start(name)

    def submit(self, queue_name, run, description=""):
        """Append a job to a named task queue. Jobs in a queue run one at a
        time, in FIFO order, on the queue's own interval service — a slow job
        never collides with the next one, and concurrent submits simply line
        up instead of replacing each other. The queue goes idle when empty
        and is re-armed by the next submit. Returns the number of jobs now
        pending (including the one in flight)."""
        q = self._queues.setdefault(queue_name, deque())
        q.append((run, description))
        if self.get(queue_name) is None:
            self.register(
                queue_name,
                description=f"Job queue: {queue_name}",
                run=self._make_drain(queue_name),
                interval=QUEUE_TICK,
                persist=False,
            )
        self.start(queue_name)
        return len(q)

    def queue_size(self, queue_name):
        """Number of jobs pending in a queue (0 if unknown)."""
        return len(self._queues.get(queue_name, ()))

    def _make_drain(self, queue_name):
        """Build the interval-service run callback that pops and executes one
        queued job per tick. A failing job is recorded but never kills the
        queue; when the queue empties the service stops (goes idle)."""
        def drain():
            q = self._queues.get(queue_name)
            if not q:
                return
            run, desc = q.popleft()
            svc = self._services.get(queue_name)
            start = time.time()
            try:
                run()
            except Exception as e:
                # Record on the queue (svc.last_error gets cleared by
                # _worker_run) and in the run history with the job's desc.
                err = f"{type(e).__name__}: {e}"
                self._queue_errors[queue_name] = self._queue_errors.get(queue_name, 0) + 1
                self._queue_last_error[queue_name] = err
                if svc is not None:
                    self._record_run(svc, False, time.time() - start, error=err, desc=desc)
            else:
                if svc is not None:
                    self._record_run(svc, True, time.time() - start, desc=desc)
            if not q:
                self.stop(queue_name)
        return drain

    # ------------------------------------------------------------------ policy

    def enable(self, name):
        svc = self._services.get(name)
        if not svc:
            return False
        svc.enabled = True
        self._save_policy()
        return True

    def disable(self, name):
        svc = self._services.get(name)
        if not svc:
            return False
        svc.enabled = False
        self._save_policy()
        return True

    def _load_policy(self):
        try:
            if os.path.exists(SERVICES_FILE):
                with open(SERVICES_FILE, "r") as f:
                    data = json.load(f)
                return dict(data.get("enabled", {}))
        except Exception:
            pass
        return {}

    def _save_policy(self):
        try:
            data = {"enabled": {
                name: svc.enabled
                for name, svc in self._services.items()
                if svc.persist
            }}
            with open(SERVICES_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    # --------------------------------------------------------------- lifecycle

    def start_all(self):
        """Start every enabled service (boot). Returns names started."""
        started = []
        for svc in list(self._services.values()):
            if svc.enabled:
                self._start_service(svc)
                started.append(svc.name)
        self._ensure_scheduler()
        return started

    def start(self, name):
        """Start a single service. Disabled services must be enabled first."""
        svc = self._services.get(name)
        if not svc:
            return False
        if not svc.enabled:
            return False
        self._start_service(svc)
        return True

    def _start_service(self, svc):
        with svc._lock:
            if svc.state == STATE_RUNNING:
                return
            svc.state = STATE_RUNNING
            svc.last_error = None
            svc.consecutive_failures = 0
            svc._restart_at = None
        if svc.oneshot:
            self._spawn_worker(svc)
        # Always ensure the scheduler: oneshot services may need scheduled
        # restarts (Restart=on-failure), which the scheduler fires.
        self._ensure_scheduler()

    def stop(self, name):
        svc = self._services.get(name)
        if not svc:
            return False
        with svc._lock:
            already = svc.state == STATE_STOPPED
            svc.state = STATE_STOPPED
        if not already and svc.stop:
            try:
                svc.stop()
            except Exception:
                pass
        return True

    def restart(self, name):
        svc = self._services.get(name)
        if not svc:
            return False
        self.stop(name)
        return self.start(name)

    def shutdown_all(self):
        """Stop every running service and halt the scheduler. Called during
        app shutdown so background tasks get their stop() cleanup."""
        self._stop_event.set()
        for svc in list(self._services.values()):
            with svc._lock:
                running = svc.state == STATE_RUNNING
                svc.state = STATE_STOPPED
            if running and svc.stop:
                try:
                    svc.stop()
                except Exception:
                    pass

    # -------------------------------------------------------------- scheduling

    def _ensure_scheduler(self):
        with self._lock:
            alive = self._scheduler is not None and self._scheduler.is_alive()
            if alive and not self._stop_event.is_set():
                return
            # Either no scheduler yet, or the old one is winding down after
            # shutdown_all — start a fresh one with a clean stop event.
            self._stop_event = threading.Event()
            self._scheduler = threading.Thread(
                target=self._scheduler_loop, daemon=True, name="systmanserv"
            )
            self._scheduler.start()

    def _scheduler_loop(self):
        while not self._stop_event.wait(DEFAULT_TICK):
            for svc in list(self._services.values()):
                spawn = False
                with svc._lock:
                    if svc.state == STATE_RESTARTING:
                        if time.time() < svc._restart_at:
                            continue
                        # RestartSec elapsed: fire the run immediately
                        svc.state = STATE_RUNNING
                        svc._restart_at = None
                        spawn = True
                    elif svc.state == STATE_RUNNING and not svc.oneshot and svc.interval is not None:
                        due = time.time() - svc.last_run >= svc.interval
                        busy = svc._worker is not None and svc._worker.is_alive()
                        if due and not busy:
                            spawn = True
                if spawn:
                    self._spawn_worker(svc)

    def _spawn_worker(self, svc):
        worker = threading.Thread(
            target=self._worker_run, args=(svc,), daemon=True,
            name=f"systmanserv-{svc.name}",
        )
        with svc._lock:
            svc._worker = worker
        worker.start()

    def _worker_run(self, svc):
        start = time.time()
        try:
            if svc.run:
                svc.run()
            with svc._lock:
                svc.runs += 1
                svc.last_run = time.time()
                svc.last_error = None
                svc.consecutive_failures = 0
                if svc.oneshot:
                    svc.state = STATE_DONE
                svc._worker = None
            if svc.name not in self._queues:
                # Queue services log each job inside drain (with its desc)
                self._record_run(svc, True, time.time() - start)
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            with svc._lock:
                svc.runs += 1
                svc.last_error = err
                svc.consecutive_failures += 1
                if self._should_restart(svc):
                    svc.state = STATE_RESTARTING
                    svc._restart_at = time.time() + svc.restart_sec
                else:
                    svc.state = STATE_ERRORED
                svc._worker = None
            if svc.name not in self._queues:
                self._record_run(svc, False, time.time() - start, error=err)

    def _should_restart(self, svc):
        """systemd Restart=on-failure: retry a failed run (after restart_sec)
        while the consecutive-failure streak is within max_restarts."""
        if svc.restart not in ("on-failure", "always"):
            return False
        if svc.max_restarts is not None and svc.consecutive_failures > svc.max_restarts:
            return False
        return True

    def _record_run(self, svc, ok, duration, error=None, desc=None):
        """Append a run-history entry (live + journal) and update totals."""
        with svc._lock:
            if ok:
                svc.successes += 1
            else:
                svc.failures += 1
            svc.total_time += duration
            record = {
                "time": time.time(),
                "ok": ok,
                "duration": round(duration, 3),
                "error": error,
                "desc": desc,
            }
            svc.history.append(record)
        self._append_journal(svc.name, dict(record, service=svc.name))

    # ---------------------------------------------------------------- journal

    def get_log(self, name, limit=HISTORY_MAX):
        """Recent run history for a service, newest last. Prefers the on-disk
        journal (a superset, covering sessions before this one and services
        not registered yet); falls back to the live service's history."""
        if name in self._journal and self._journal[name]:
            return list(self._journal[name])[-limit:]
        svc = self._services.get(name)
        if svc is not None:
            return list(svc.history)[-limit:]
        return []

    def _load_journal(self):
        """Read the journal file into per-service deques, skipping corrupt
        lines so a partial write never breaks the log."""
        journal = {}
        lines = 0
        try:
            if os.path.exists(JOURNAL_FILE):
                with open(JOURNAL_FILE, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = json.loads(line)
                        except Exception:
                            continue
                        name = rec.get("service")
                        if not name:
                            continue
                        journal.setdefault(
                            name, deque(maxlen=JOURNAL_MAX_PER_SERVICE)
                        ).append(rec)
                        lines += 1
        except Exception:
            pass
        self._journal_lines = lines
        return journal

    def _append_journal(self, name, record):
        with self._lock:
            self._journal.setdefault(
                name, deque(maxlen=JOURNAL_MAX_PER_SERVICE)
            ).append(record)
            self._journal_lines += 1
            try:
                with open(JOURNAL_FILE, "a") as f:
                    f.write(json.dumps(record) + "\n")
                    f.flush()
            except Exception:
                pass
            if self._journal_lines >= JOURNAL_COMPACT_AT:
                self._compact_journal()

    def _compact_journal(self):
        """Trim the journal file to its most recent lines."""
        try:
            lines = []
            if os.path.exists(JOURNAL_FILE):
                with open(JOURNAL_FILE, "r") as f:
                    lines = f.readlines()
            lines = lines[-JOURNAL_KEEP:]
            with open(JOURNAL_FILE, "w") as f:
                f.writelines(lines)
            self._journal_lines = len(lines)
        except Exception:
            pass

    # ------------------------------------------------------------------ status

    def status(self):
        return [
            {
                "name": svc.name,
                "description": svc.description,
                "state": svc.state,
                "enabled": svc.enabled,
                "oneshot": svc.oneshot,
                "interval": svc.interval,
                "runs": svc.runs,
                "last_run": svc.last_run,
                "last_error": svc.last_error or self._queue_last_error.get(svc.name),
                "pending": len(self._queues.get(svc.name, ())) if svc.name in self._queues else None,
                "errors": self._queue_errors.get(svc.name, 0) if svc.name in self._queues else None,
                "successes": svc.successes,
                "failures": svc.failures,
                "total_time": round(svc.total_time, 3),
                "avg_duration": round(svc.total_time / svc.runs, 3) if svc.runs else None,
                "restart": svc.restart,
                "restart_sec": svc.restart_sec,
                "max_restarts": svc.max_restarts,
                "consecutive_failures": svc.consecutive_failures,
            }
            for svc in self._services.values()
        ]


_manager = None
_manager_lock = threading.Lock()


def get_manager():
    """Module-level singleton (like systemd's PID-1 for in-process services)."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = ServiceManager()
    return _manager


def run_once(name, run, description=""):
    """Module-level shorthand for fire-and-forget oneshot tasks."""
    return get_manager().run_once(name, run, description=description)


def submit(name, run, description=""):
    """Module-level shorthand for queueing a job (see ServiceManager.submit)."""
    return get_manager().submit(name, run, description=description)
