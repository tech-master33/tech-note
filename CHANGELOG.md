# Changelog

All notable changes to Tech-Note are documented here.

> **Status terms:** **released** means the source is on GitHub (pushed to `main`); **released to archive** means it is also tagged as a GitHub release. Every shipped version is released; only the ones behind the current version are released to archive — while the app is on **v9**, the archive tops out at **v8**, and when the version bumps to v10, v9 gets tagged and released to archive as the new latest, and so on.

## v9.2.1 (released)

### Bug fixes
- **Unlock no longer fails with `NameError: TECH_SOFT is not defined`.** `_load_main_menu_layout()` and `_save_main_menu_layout()` in `core/menu.py` referenced `TECH_SOFT` without importing it. On unlock, `load_main_menu()` → `build_braillenote_menu()` → `_load_main_menu_layout()` raised, which aborted `_unlock()` **before `exit_app()` ran** — so the PIN was accepted, the unlock sound played, and the lock screen stayed active. The import is fixed, and `_unlock()` now wraps `success_callback()` in try/except so a callback failure can never leave the screen locked (it logs, announces the failure, and still deactivates).
- **Main menu no longer lists every app twice.** When no custom layout was saved, `build_braillenote_menu`'s fallback branch never populated `listed_ids`, so the "add unlisted defaults" pass re-added all 14 built-ins a second time.

## v9.2.0 (released)

### Bug fixes
- **FM Radio / Media Player: orphaned streams no longer play over other apps.** Both apps now implement `on_destroy()` to call `stop_channel("media")` when the app is interrupted by power menu, auto-lock, or another app launch. Previously the audio stream kept playing in the background with no way to stop it.
- **Options / Settings apps: stale input modes no longer persist across app switches.** `OptionsApp.on_pause()` clears `adjust_mode`; `SettingsApp.on_pause()` clears `adjust_mode`, `pin_mode`, `confirm_mode`, `text_input`, and `_find_setting_mode`. Previously, being mid-edit when the power menu or auto-lock interrupted would leave the app in an invisible input mode on resume.
- **Chat client: WebSocket now auto-reconnects on disconnect.** The `on_close` handler triggers exponential backoff reconnection (1s → 2s → 4s → ... → 30s cap, reset on successful open). Previously a network blip silently killed the chat with no recovery.
- **Bridge orphan cleanup on startup.** `boot_64.py` now kills any lingering `TechNoteBridge32.exe` processes from previous crashes on startup. Windows doesn't clean up child processes, so zombies held SAPI/COM resources and sockets.
- **Bare `except:` clauses replaced with `except Exception:`** in boot_64.py to prevent catching `KeyboardInterrupt` and `SystemExit`.
- **`_edit_menu_add_app` closure fix.** Removed stale `idx` default argument that evaluated at lambda definition time instead of click time.

## v9.1.0 (released)

### Bug fixes
- **Speech no longer overlaps during menu navigation.** `MenuSystem` now calls `synth.stop()` before every `speak()` call in `announce_current()`. On the 64-bit SAPI engine, `_engine_stop()` uses a synchronous `Speak("", 0)` instead of the old async flag `2`, guaranteeing the engine is fully idle before the next utterance. On the 32-bit bridge, `speak()` now uses async flag `1` (returns immediately) and `cancel()` uses flag `2` (SVSFPurgeBeforeSpeak) — the bridge's `stop` handler acquires `_speak_lock` so stop and speak serialize correctly instead of racing.
- **Unlock no longer gets stuck on the lock screen or opens Word Processor.** Two fixes: (1) `_unlock_done()` now syncs `self.current_app = self.app_manager.current_app` after popping the lock screen — without this, `self.current_app` still pointed at the (inactive) lock screen, so every keypress went to the dead lock screen instead of the main menu; (2) the key handler now refreshes the window text and announces the current menu item when the lock screen exits, preventing the display from being stuck on "PIN:". `_unlock()` also resets `pin_mode = False` immediately, and a 1-second keyboard flush window discards events that queued during `play_blocking`.

### UI groundwork
- **Every app has a stable `app_id`.** `SoftApp.get_app_id()` returns a pinned id set on each built-in app class (`word_processor`, `calculator`, `email`, `settings`, ...), falling back to a stable class-name-derived id for any app that doesn't set one. This is the identifier UI layouts, per-app settings, and profiles will key on in v10.
- **Customizable main menu.** The main menu is now a declarative layout (`DEFAULT_MAIN_MENU` with `{id, label, shortcut, hidden, children}` entries) persisted in `settings.json` under the `main_menu` key. Users can reorder, hide, rename, change shortcuts, and remove apps. Press **Space+E** in the main menu to enter Edit Main Menu mode (also accessible from Options → Tools). Edit mode supports: Move Up/Down, Rename (text input), Set Shortcut (key capture), Show/Hide toggle, Remove from Menu, Add App (from unlisted built-ins), Save, and Restore Defaults. The layout is applied at menu load time; unlisted apps appear after listed ones, so new installs aren't lost.

## v9.0.0 (released)

### Unified 32-bit bridge (one exe)
- **Both 32-bit bridges are now one program.** `bridge/bridge_main.py` serves the SAPI TTS backend and `bits: 32` synth plugins over the same socket protocol (`tts` / `plugin <path>` modes), compiled by PyInstaller under 32-bit Python into a single `bridge/TechNoteBridge32.exe`. `core/bridge_launcher.py` resolves the launch command — the exe when present, otherwise a 32-bit Python plus the source script for development — and `BridgeTTS` (`core/tts_bridge.py`) and `BridgePluginSynth` (`core/plugin_bridge.py`) both drive it.
- **32-bit TTS engines run inside 64-bit Tech-Note.** The bridge serves SAPI (pywin32, falling back to 32-bit PowerShell's System.Speech) over a localhost socket; it appears in the TTS Engine menu as "SAPI5 (32-bit bridge)". No separate 32-bit Python install is needed when the exe ships.
- **Synth plugins can declare an optional `bits` manifest field (32 or 64) — never shown in the UI; it's a DLL-loading directive.** A synth declaring `bits: 32` cannot load its DLLs in the 64-bit process, so the plugin manager **never imports or instantiates it in-process**: it's registered bridge-only, listed in the TTS Engine menu, and `create_synth` routes it to `BridgePluginSynth`, which launches the unified bridge in `plugin` mode and proxies the whole SynthPlugin interface over the socket (generic `call` RPC, auto-respawn on death). Plugins without `bits` (or `bits: 64`) load in-process exactly as before.
- Fixed a latent deadlock in both bridge clients: the reconnect path re-entered the non-reentrant request lock, and the helper never acked `shutdown` (so close could respawn it). The helper now acks shutdown and runs the backend/plugin `shutdown()` hook before exiting.
- The bridge exe bundles the stdlib modules plugins commonly need (`platform`, `ctypes`, `re`, `time`, ...); build instructions live in `bridge/README.md`.

### Plugin settings menus
- **Plugins can contribute their own settings screens to Options.** `ScrugnPlugin.get_option_menus()` returns a list of `PluginOptionMenu(title, build_fn, path="")`; the Options app builds a **Plugin Settings** area (Options > Plugin Settings > <plugin name>) from them, and a pipe-separated `path` (e.g. `"TTS Menu|Advanced"`) places a menu anywhere in the Options tree, creating intermediate nodes if missing. `build_fn` receives the live OptionsApp so plugins build with the same Tech-Note UI calls (`MenuNode`/`MenuSystem`, `_build_list_menu`, `_build_numeric_menu`, `app.speak`, `app.settings` + `_save_settings()`), and Back returns to the exact entry that opened the menu (`MenuSystem.back()` honors a per-node return index). Only in-process plugins can contribute menus; `bits: 32` synths live in the bridge and use a companion plugin for UI.

### syst
- **The daemon family is unified under one name.** `core/syst.py` exposes a single facade — `syst.services()`, `syst.audio()`, a unified `status()` — over systmanserv + systmanau, and the Terminal gains a `syst` command (`syst status`, `syst services <args>`, `syst audio <args>`).

## v8.0.0 (released to archive)

### App lifecycle
- Options, Power, and Tutorial overlays now resume the app they interrupted instead of dropping the user back on the main menu.
- The app stack is now functional: nested apps (e.g. Plugin Manager opened from Options) return to their caller, and Sleep mode wakes back into the interrupted app.

### Screen reader
- **Character Echo now works.** The Options > Keyboard toggle was a dead setting — no code ever spoke a typed character. Typing in a text-input app (Word Processor, Notes search/tags, Address List fields, Chat composing) now speaks each letter, digit, and punctuation mark when Character Echo is On, and **never echoes password fields** (Chat's change-password flow and password fields are masked via a new `SoftApp.is_masked_input()` contract). Space isn't echoed as a character so it doesn't collide with Word Echo.
- **Word Echo was equally dead and is fixed by the same change.** The typing buffer Word Echo reads on Space was never filled — the char-echo pass now accumulates typed characters, so Word Echo speaks the completed word and clears the buffer (Enter/Escape still clear it).

### Lock screen & power
- **Lock Tech-Note in the power menu.** Shows the lock screen (only when a PIN/password is set) and, after unlock, resumes the app the power menu interrupted instead of dropping to the main menu.
- **Auto-Lock After Idle** setting in Settings > System Settings (minutes, 0 = off, same Edit Value / Reset pattern as TTS Volume). A new `auto-lock` systmanserv service checks system idle time via `GetLastInputInfo` and raises the lock screen on the window thread; the interrupted app resumes after unlock.
- **Waking from Sleep requires the PIN/password** when one is set: the first keypress routes through the lock screen instead of resuming straight into the app, and the interrupted app resumes after unlock (no credential = wake straight back as before).
- **The lockout countdown actually counts down.** The lock screen's timer was hardcoded to a 60s tick, so a 30s lockout froze on "Unlock (locked 30s)". While locked, the menu now ticks every second and updates the remaining time in place (keeping your menu position), then flips to a plain Unlock the moment it expires — and entering the lockout starts the countdown immediately.
- **The lock screen speaks "You can now unlock your system"** exactly once when the lockout expires, so the user doesn't have to keep checking the menu (normal once-a-minute clock refreshes stay silent).
- **The lock screen shows "Last failed unlock: <time>"** and warns on focus when the most recent failed attempt is under an hour old, so a legitimate user can tell someone tried their PIN/password while they were away. The attempt time is kept **in memory only — never written to disk**.
- **Restart now preserves the session** (gated by Remember Last App): the current app is saved to `resume.json` and the goodbye message correctly says "Restarting Tech-Note" instead of "Shutting down".
- **Fixed: lock screen silently discarded crash recovery / hibernate state.** `resume.json` was deleted on unlock, so anyone with a PIN/password never got the "Previous session ended unexpectedly" resume or a hibernate resume. Unlock no longer touches it.
- **Fixed: hibernate with Shutdown PIN enabled looped forever** — each correct PIN just re-prompted, because the PIN-gated action was `_do_hibernate` itself. It now gates `_hibernate_impl`, and PIN-gated restart/shutdown/hibernate all respect the unsaved-work block.
- StealthWindow gains a `post_task` bridge so background services can run app-state changes on the window thread.

### Unsaved-work protection
- New `SoftApp.is_dirty()` contract; the Word Processor reports unsaved edits.
- Shutdown, restart, sleep, and hibernate warn when apps have unsaved work, naming the affected apps (e.g. "Warning: Unsaved work in Word Processor.").
- New settings: **Block Shutdown on Unsaved Work** (`block_on_unsaved`, default On) and **Warn on Unsaved Work** (`warn_unsaved_on_shutdown`, default On) — block, warn-and-proceed, or silent policies for immediate and scheduled shutdown actions.
- Word Processor prompts to save (Save and Exit / Exit Without Saving / Cancel) before discarding unsaved edits.

### Cloud backup
- Settings > Cloud Backup: export with an optional label, restore the latest backup, and browse/restore specific backups.
- Backup listing sorts by export timestamp; restoring without a path now picks the newest backup.

### Services (systmanserv)
- New `core/systmanserv.py`: a pure-Python, systemd-inspired in-process service manager (no OS-specific APIs). Services are named, enable/disable for boot (persisted to `services.json`), start/stop/restart at runtime, interval or one-shot scheduling, status reporting, and clean shutdown via `shutdown_all()` in `_exit_app`.
- The hand-rolled daemon threads are now services: autosave (10s tick), session-save for crash recovery (60s tick), the one-shot startup update check, and the power-schedule watcher (30s tick; fires once, then disables the schedule).
- Terminal gains a `services` command: `services`, `services start|stop|restart|enable|disable <name>`.
- New task-queue API: `submit(name, run)` queues jobs that run one at a time in FIFO order (no replace-collision) — for queued downloads, sends, and the like. Queues appear in `services` status with pending/error counts and go idle when empty.
- Per-service run statistics and history: every run is logged (timestamp, ok/error, duration, job description) into a 30-entry ring buffer, with success/failure counts and average duration in status. Terminal gains `services log <name>` (journalctl-style) and `services <name>` (full status for one service).
- Restart policies: `register(..., restart="on-failure", restart_sec=1.0, max_restarts=3)` retries a failed service after the delay, up to the consecutive-failure cap, mirroring systemd Restart=on-failure; a new `restarting` state is visible in status, and a manual `services restart` clears the streak.
- Run history is journaled to `~/.tech-soft/services_journal.jsonl` (append-only JSONL, compacted when large, corrupt lines skipped), so `services log <name>` survives app restarts and even shows logs for services not registered this session.
- Per-app worker threads are now short-lived oneshot services via `run_once()`: email inbox fetch/read/send, internet downloads and page fetches, App Store catalog refresh and update checks, and the OpenCode API call (via the `core/app_workers.py` bridge, since `opencode_client.py` is blocked from the editing tools). Chat polling runs as interval services (`chat-poll` 1s, `chat-client-poll` 3s). Every service run happens in its own worker thread, so slow network tasks never block the scheduler and interval runs never overlap.

### Audio (systmanau)
- New `core/systmanau.py`: a pure-Python audio manager over a single shared `AudioPlayer`. Priority channels (speech > notify > ui > media > voice) decide what preempts what; long-lived playback (radio/media/voice) is paused and resumed around higher-priority sounds instead of being killed.
- **Pause-while-playing is now a setting, off by default.** Sounds and media play together by default — a click or notification plays *over* the radio/media without pausing it (the stream is never stopped, so the media keeps playing). Turn it **On** in Options > Audio Menu > Pause While Playing (or `audio pause on`) to restore the preempt-with-resume behavior: a higher-priority sound pauses the radio/media and resumes it after. Boot applies it from settings; `audio status` reports the current state.
- **Fixed: menu navigation sounds no longer stop the radio or media player.** Every app previously built its own `AudioPlayer` over a shared sounddevice handle, so any `play_move`/`play_click` `stop()` silenced whatever was playing. All playback now goes through the manager.
- **Radio now true-pauses instead of rebuffering.** URL playback no longer shells out to ffplay (which could only be killed); it streams through ffmpeg into the app's own sounddevice pipeline. A higher-priority sound (click, notification, speech) *pauses* the stream — ffmpeg keeps downloading, the output is silenced — and resume returns to live audio instantly, with no reconnect/rebuffer. Tuning a new station, `stop_channel`, and shutdown still hard-stop the stream, and a paused stream is killed if its session is dropped (no orphans).
- **Media tracks now true-pause and resume mid-track too.** Local files play through the same streaming engine (`kind="track"`): a click pauses the track in place and resume continues where it left off instead of restarting. Two file-specific behaviors: audio is *buffered* while paused (position preserved, unlike live radio which discards to stay current), and when ffmpeg finishes decoding before playback catches up, the buffered tail plays out so the end of a track is never truncated (the stream stays alive until the last sample, then the session ends). EQ presets still apply to track playback (applied per callback chunk when non-Flat).
- Deliberate actions (tune a station, play a track, open a voice message) queue behind transient sounds via `wait=True` instead of being dropped.
- Playback sessions surface as systmanserv services: tuning the radio registers a `media` service (visible in `services`, stoppable via `services stop media`), with the same journaling/status as every other service.
- Notification sounds are actually played: `NotificationCenter.post()` now plays the source's configured sound on the notify channel (with fallback to real `sounds/` files for the still-unshipped defaults), and chat's winsound beep is replaced by the same path.
- Ducking is now app-wide: the synth shares the manager-owned `AudioDucker` (single source of truth), and `audio duck`/`audio unduck` expose it.
- Terminal gains an `audio` command: `audio` / `audio status` (now playing, paused/pending channels, volume, EQ, muted, ducking), `audio stop [channel]`, `audio vol [value]`, `audio mute|unmute`, `audio duck|unduck`, `audio eq [preset]`.

### Bug fixes
- Scheduled shutdown's unsaved-work check no longer reads the nonexistent `app_manager._running_apps`.
- Cloud backup restore with no path no longer restores the oldest backup.

## v7.0.0 (released to archive)

- 100 components; enhancements across the app suite.
- Plugin store: the Plugin Manager gains an Online Store listing synth, braille, and filter plugins.
- New core systems: cloud sync, clipboard history, command registry, error handler levels, notification center, performance cache, pronunciation dictionary, safe mode, session manager, updater.
- Power menu: scheduled shutdown/sleep, PIN protection, hibernate.
- Tutorial app with categories, an interactive walkthrough, and all-topics modes.

## v6.0 (released to archive)

- Major feature release.

## v5.0.1 (released to archive)

- Full spell checker with suggestions.
- Speech fixes; removed the Opening message.

## v5.0.0 (released to archive)

- Menus refactor, speech fixes, settings manager, plugin UI, App Store update, rate boost.

## v4.0.0 (released to archive)

- Release.

## v3.1.0 (released to archive)

- Release.

## v3.0.0 (released to archive)

- Release.
