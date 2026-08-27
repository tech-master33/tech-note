import os
import sys
import json
import subprocess
import win32api
import win32con
import time
import pythoncom
from core.menu import MenuSystem, build_braillenote_menu, _get_sound_path, SOUNDS_DIR, SOUND_SCHEME
from ui.stealth_window import StealthWindow
from synths.sapi_synth import SapiSynthBase
from synths.registry import create_synth
from menus.options_menu import OptionsApp
from menus.power_menu import PowerApp
from menus.tutorial_app import TutorialApp
from core.setup_core import TechNoteSetup
from core.systmanau import get_audio_manager
from core.config import TECH_SOFT
import core.error_handler
from core.notification_center import get_center as get_notification_center
import core.safe_mode
from core.app_base import AppManager

pythoncom.CoInitialize()

class BrailleNoteApp:
    def __init__(self):
        self.tech_soft = TECH_SOFT
        if not os.path.exists(self.tech_soft):
            os.makedirs(self.tech_soft)
            for folder in ['documents', 'downloads', 'contacts', 'desktop']:
                os.makedirs(os.path.join(self.tech_soft, folder))

        self.synth = SapiSynthBase()
        core.error_handler.load_level_from_settings()
        self._notifications = get_notification_center()
        self._apply_settings()

        self._power_vk = 0xC0
        self._power_key_name = "backtick (above Tab)"
        self.window = StealthWindow(on_key_down=self.handle_key, on_key_up=self.handle_key_up)

        self.menu = None
        self.app_manager = AppManager(self)
        self.current_app = None
        self._typing_buffer = ""
        self._char_echo = "Off"
        self._word_echo = "Off"
        self._key_bindings = {}
        self._announce_position = True
        self._state_keys = "Off"
        self.space_used_in_chord = False
        self._shutting_down = False
        self._search_mode = False
        self._search_buffer = ""
        self._last_unlock_time = -float('inf')
        self._auto_lock_due = False
        self._sleeping = False

        # Detect keyboard layout for power key assignment
        self._detect_keyboard_layout()

        # Play startup sound before any speech
        self._play_startup_sound()

        # Apply visual settings to window (may trigger speech)
        self._apply_visual_settings()

    def speak(self, text, interrupt=True):
        if self.synth:
            self.synth.speak(text, interrupt)

    def stop(self):
        if self.synth:
            self.synth.stop()

    def reset_temp_params(self):
        if self.synth:
            self.synth.reset_temp_params()

    def set_temp_params(self, **kwargs):
        if self.synth:
            self.synth.set_temp_params(**kwargs)

    def _play_startup_sound(self):
        try:
            settings_path = os.path.join(self.tech_soft, 'settings.json')
            if os.path.exists(settings_path):
                try:
                    with open(settings_path, 'r') as f:
                        s = json.load(f)
                    if s.get("startup_sound") == "Off":
                        return False
                except:
                    pass
            path = _get_sound_path('startup.mp3')
            if not os.path.exists(path):
                path = os.path.join(SOUNDS_DIR, 'startup.mp3')
            if os.path.exists(path):
                get_audio_manager().play_blocking("ui", path)
        except Exception as e:
            print(f"Startup sound error: {e}")
        return True

    def _detect_keyboard_layout(self):
        settings_path = os.path.join(self.tech_soft, 'settings.json')
        saved_layout = None
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    s = json.load(f)
                saved_layout = s.get("keyboard_layout")
            except:
                pass
        if saved_layout in ("US", "UK", "Arabic"):
            self._keyboard_layout = saved_layout
        else:
            hkl = win32api.GetKeyboardLayout(0)
            lang_id = hkl & 0xFFFF
            primary_lang = lang_id & 0x3FF
            if primary_lang == 0x01: # LANG_ARABIC
                self._keyboard_layout = "Arabic"
            else:
                self._keyboard_layout = "UK" if lang_id == 0x0809 else "US"

        if self._keyboard_layout == "UK":
            self._power_vk = 0xDF
            self._power_key_name = "backtick (left of Z)"
        elif self._keyboard_layout == "Arabic":
            # Arabic keyboards usually have backtick at 0xC0 like US
            self._power_vk = 0xC0
            self._power_key_name = "backtick (above Tab)"
        else:
            self._power_vk = 0xC0
            self._power_key_name = "backtick (above Tab)"
        try:
            s = {}
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    s = json.load(f)
            s["keyboard_layout"] = self._keyboard_layout
            with open(settings_path, 'w') as f:
                json.dump(s, f)
        except Exception:
            pass

    def _apply_visual_settings(self):
        settings_path = os.path.join(self.tech_soft, 'settings.json')
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    s = json.load(f)
                colors = {"Black": (0,0,0), "Blue": (0,0,128), "Gray": (64,64,64)}
                bg = colors.get(s.get("bg_color", "Black"), (0,0,0))
                fs = s.get("font_size", "Medium")
                self.window.set_display_settings(bg_color=bg, font_size=fs)
            except Exception as e: core.error_handler.log(e, "Loading display settings")

        account_path = os.path.join(self.tech_soft, 'account.json')
        if not os.path.exists(account_path):
            print("No account found, launching setup.")
            self._start_setup()
        else:
            self.load_account_and_menu(account_path)

        print("TechNote Start Menu Running.")

    def _apply_settings(self):
        settings_path = os.path.join(self.tech_soft, 'settings.json')
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    s = json.load(f)
                rate = s.get("rate")
                volume = s.get("volume")
                voice_index = s.get("voice_index")
                if rate is not None:
                    self.synth.set_rate(rate)
                if volume is not None:
                    self.synth.set_volume(volume)
                if voice_index is not None:
                    names = self.synth.get_voice_names()
                    if 0 <= voice_index < len(names):
                        self.synth.set_voice_by_index(voice_index)
                pl = s.get("punctuation_level", "Some")
                self.synth.set_punctuation_level(pl)
                self._char_echo = s.get("char_echo", "Off")
                self._word_echo = s.get("word_echo", "Off")
                self._key_bindings = s.get("key_bindings", {})
                self._announce_position = s.get("announce_position", "On")
                self._state_keys = s.get("state_keys", "Off")
                self.synth.set_pitch(s.get("pitch", 50))
                self.synth.set_capital_pitch_change(s.get("capital_pitch_change", "Off"))
                self.synth.set_volume_ducking(s.get("volume_ducking", "Off") == "On")
                import core.menu
                core.menu.SOUND_SCHEME = s.get("sound_scheme", "Default")
                get_audio_manager().set_pause_while_playing(
                    s.get("pause_while_playing", "Off") != "Off")
            except Exception:
                pass
        else:
            self._char_echo = "Off"
            self._word_echo = "Off"
            self._key_bindings = {}

    def _get_time_format(self):
        try:
            settings_path = os.path.join(self.tech_soft, 'settings.json')
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    s = json.load(f)
                return s.get("time_format", "12-hour")
        except Exception:
            pass
        return "12-hour"

    def _start_setup(self):
        setup = TechNoteSetup(self, self.window)
        setup.finish_callback = self.on_setup_complete
        self.current_app = setup
        setup.run_setup()

    def _reset_settings_to_defaults(self):
        try:
            settings_path = os.path.join(self.tech_soft, 'settings.json')
            if os.path.exists(settings_path):
                os.remove(settings_path)
        except Exception:
            pass

    def _reload_app(self):
        self._restart_process()

    def _reset_and_restart(self):
        self.current_app = None
        self.menu = None
        account_path = os.path.join(self.tech_soft, 'account.json')
        if os.path.exists(account_path):
            try:
                os.remove(account_path)
            except:
                pass
        self._start_setup()

    def on_setup_complete(self):
        print("Setup complete, loading.")
        account_path = os.path.join(self.tech_soft, 'account.json')
        if os.path.exists(account_path):
            self.load_account_and_menu(account_path)
        else:
            self._start_setup()

    def load_account_and_menu(self, path):
        try:
            with open(path, 'r') as f:
                self.account = json.load(f)
        except (json.JSONDecodeError, IOError):
            self.speak("Account corrupted. Re-running setup.")
            self._start_setup()
            return

        synth_module = self.account.get("synth_module", "sapi_synth")
        if synth_module != "sapi_synth":
            new_synth = create_synth(synth_module)
            if new_synth:
                self.synth = new_synth
        self._apply_settings()

        voice_name = self.account.get('default_synth', 'Auto')
        if hasattr(self.synth, 'set_voice'):
            self.synth.set_voice(voice_name)
        self.synth.save_defaults()

        if self.account.get("pin") or self.account.get("password"):
            self.launch_app(lambda m, w: self._create_lock_screen(m, w))
        else:
            self.load_main_menu()

    def _write_clean_flag(self, value):
        try:
            with open(os.path.join(self.tech_soft, '.clean_shutdown'), 'w') as f:
                f.write('1' if value else '0')
        except:
            pass

    def _read_clean_flag(self):
        try:
            path = os.path.join(self.tech_soft, '.clean_shutdown')
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return f.read().strip() == '1'
        except:
            pass
        return True

    def _save_session_state(self):
        """Persist the current app for crash recovery (systmanserv
        'session-save' service, 60-second tick)."""
        try:
            if self.current_app and self.current_app.active:
                app_module = self.current_app.__class__.__module__
                if app_module not in ("menus.power_menu", "menus.lock_screen"):
                    app_data = {
                        "app_module": app_module,
                        "app_class": self.current_app.__class__.__name__
                    }
                    if hasattr(self.current_app, "get_state"):
                        app_data["state"] = self.current_app.get_state()
                    with open(os.path.join(self.tech_soft, 'resume.json'), 'w') as f:
                        json.dump(app_data, f)
        except:
            pass

    def _start_services(self):
        """Register and start the systmanserv boot services: autosave,
        session-save for crash recovery, and the one-shot startup update
        check. Replaces the old hand-rolled daemon threads."""
        from core.systmanserv import get_manager
        import core.auto_save
        m = get_manager()
        # Long-lived audio playback (radio/media) surfaces as services
        get_audio_manager().set_service_manager(m)
        m.register(
            "autosave",
            description="Autosave dirty apps every 10 seconds",
            run=core.auto_save.tick,
            interval=10,
        )
        m.register(
            "session-save",
            description="Persist the current app for crash recovery every 60 seconds",
            run=self._save_session_state,
            interval=60,
        )
        m.register(
            "update-check",
            description="Check for updates once at startup",
            run=self._check_startup_update,
            oneshot=True,
        )
        # Bridge apps that still spawn raw worker threads (opencode_client is
        # blocked from the editing tools, so it is patched here, not edited)
        try:
            from core.app_workers import install_legacy_bridges
            install_legacy_bridges()
        except Exception:
            pass
        m.register(
            "auto-lock",
            description="Lock the screen after the configured idle period (auto_lock_minutes, 0 = off)",
            run=self._auto_lock_tick,
            interval=15,
        )
        m.start_all()

    def load_main_menu(self):
        import core.menu
        core.menu.ANNOUNCE_POSITION = self._announce_position == "On"

        if core.safe_mode.should_enter_safe_mode():
            core.safe_mode.set_safe_mode(True)
            self.synth.speak("Safe mode: third-party apps disabled, settings reset.")
            self._reset_settings_to_defaults()

        self.menu_root = build_braillenote_menu(
            self, self.window, self.launch_app, self._reset_and_restart,
            safe_mode=core.safe_mode.is_safe_mode()
        )
        self.menu = MenuSystem(self.menu_root, self.speak, stop_func=self.stop)

        # Crash detection
        clean = self._read_clean_flag()
        resume_path = os.path.join(self.tech_soft, 'resume.json')
        if not clean and os.path.exists(resume_path):
            self.synth.speak("Previous session ended unexpectedly. Resuming last session.")
        self._write_clean_flag(False)

        # Start systmanserv boot services
        self._start_services()

        # Check for resume
        if os.path.exists(resume_path):
            try:
                with open(resume_path, 'r') as f:
                    resume_data = json.load(f)
                
                # Verify if auto-resume is enabled in settings
                settings_path = os.path.join(self.tech_soft, 'settings.json')
                auto_resume = True
                if os.path.exists(settings_path):
                    with open(settings_path, 'r') as sf:
                        s = json.load(sf)
                        auto_resume = s.get("auto_resume_apps", True)
                
                if auto_resume:
                    app_module = resume_data.get("app_module", "")
                    # Don't resume system utilities
                    if app_module in ("menus.power_menu", "menus.lock_screen"):
                        try:
                            os.remove(resume_path)
                        except:
                            pass
                    else:
                        import importlib
                        module = importlib.import_module(app_module)
                        app_class = getattr(module, resume_data["app_class"])
                        
                        if clean:
                            self.speak("Resuming last session.")
                        self.launch_app(app_class)
                        
                        if "state" in resume_data and hasattr(self.current_app, "set_state"):
                            self.current_app.set_state(resume_data["state"])
                        return
            except Exception as e:
                print(f"Resume failed: {e}")

        self.speak("Main Menu")

    def refresh_main_menu(self):
        import core.menu
        import core.safe_mode
        core.menu.ANNOUNCE_POSITION = self._announce_position == "On"
        self.menu_root = build_braillenote_menu(
            self, self.window, self.launch_app, self._reset_and_restart,
            safe_mode=core.safe_mode.is_safe_mode()
        )
        self.menu = MenuSystem(self.menu_root, self.speak, stop_func=self.stop)

    def _create_lock_screen(self, manager, window):
        from menus.lock_screen import LockScreenApp
        return LockScreenApp(manager, window, self.load_main_menu)

    def launch_app(self, app_class_or_callable):
        self._typing_buffer = ""
        # Pause current app before launching new one
        if self.app_manager.is_active():
            try:
                self.current_app.on_pause()
            except Exception:
                pass
        try:
            self.current_app = app_class_or_callable(self, self.window)
            self.current_app.on_focus()
        except Exception as e:
            core.error_handler.log(e, f"launch_app failed for {app_class_or_callable}", level=core.error_handler.LEVEL_ERROR)
            # Resume previous app on failure
            if self.app_manager.current_app:
                self.current_app = self.app_manager.current_app
                try:
                    self.current_app.on_resume()
                except Exception:
                    pass
            else:
                self.current_app = None
                if self.menu:
                    self.menu.announce_current()
            count = core.safe_mode.record_crash()
            self.synth.speak(f"App failed to launch. Crash {count} of 3.")
            return
        self.app_manager.current_app = self.current_app
        core.safe_mode.record_clean_exit()
        # Per-app voice override
        app_name = self.current_app.__class__.__name__
        settings_path = os.path.join(self.tech_soft, 'settings.json')
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                pav = settings.get("per_app_voice", {})
                if app_name in pav:
                    override = pav[app_name]
                    self.synth.set_temp_params(
                        rate=override.get("rate"),
                        pitch=override.get("pitch"),
                        voice_index=override.get("voice_index")
                    )
            except Exception as e:
                core.error_handler.log(e, "per-app voice override", level=core.error_handler.LEVEL_WARN)

    def _finalize_exited_app(self):
        """The current app has set active=False. Resume the app it interrupted
        (if any) or fall back to the main menu."""
        self.app_manager.exit_current()
        self.current_app = self.app_manager.current_app
        if self.current_app is None and self.menu:
            self.menu.announce_current()

    def _open_options(self):
        self._typing_buffer = ""
        self.app_manager.push_current()
        self.current_app = OptionsApp(self, self.window)
        self.current_app.on_focus()
        self.app_manager.current_app = self.current_app

    def _open_edit_main_menu(self):
        """Open Options directly into Edit Main Menu mode."""
        self._typing_buffer = ""
        self.app_manager.push_current()
        self.current_app = OptionsApp(self, self.window)
        self.app_manager.current_app = self.current_app
        self.current_app._enter_edit_menu()

    def _open_power_menu(self):
        self._typing_buffer = ""
        # Save current app for resume before opening power menu
        if self.current_app and self.current_app.active:
            app_module = self.current_app.__class__.__module__
            if app_module not in ("menus.power_menu", "menus.lock_screen"):
                try:
                    app_data = {
                        "app_module": app_module,
                        "app_class": self.current_app.__class__.__name__
                    }
                    if hasattr(self.current_app, "get_state"):
                        app_data["state"] = self.current_app.get_state()
                    with open(os.path.join(self.tech_soft, 'resume.json'), 'w') as f:
                        json.dump(app_data, f)
                except Exception as e: core.error_handler.log(e, "Saving resume data")
        # Pause and remember the interrupted app so it can be resumed on Back
        self.app_manager.push_current()
        self.current_app = PowerApp(
            self, self.window,
            on_restart=self._reload_app,
            on_exit=self._exit_app,
            on_lock=self._lock_from_power
        )
        self.current_app.on_focus()
        self.app_manager.current_app = self.current_app

    # --------------------------------------------------------------- locking

    def _lock_from_power(self):
        """Lock from the power menu: swap the power menu (already on the app
        stack above the interrupted app) for the lock screen, so a successful
        unlock resumes the app the power menu interrupted."""
        from menus.lock_screen import LockScreenApp
        self._typing_buffer = ""
        lock = LockScreenApp(self, self.window, self._unlock_done)
        self.current_app = lock
        self.app_manager.current_app = lock
        lock.on_focus()

    def _lock_now(self):
        """Show the lock screen from anywhere. The current app (if any) is
        paused and stacked so it resumes after unlock; from the main menu the
        user returns to the menu."""
        from menus.lock_screen import LockScreenApp
        self._typing_buffer = ""
        self.app_manager.push_current()
        lock = LockScreenApp(self, self.window, self._unlock_done)
        self.current_app = lock
        self.app_manager.current_app = lock
        lock.on_focus()

    def _unlock_done(self):
        """Lock screen succeeded: pop it and resume the app it interrupted
        (or return to the main menu if nothing was open)."""
        self._last_unlock_time = time.time()
        self.app_manager.exit_current()
        # Sync boot_64's current_app with the app manager — without this,
        # self.current_app still pointed at the lock screen and every key
        # went to the (now inactive) lock screen's on_key.
        self.current_app = self.app_manager.current_app
        if self.current_app is None and self.menu:
            self.menu.announce_current()

    def _account_has_credential(self):
        try:
            from core.config import ACCOUNT_PATH
            if os.path.exists(ACCOUNT_PATH):
                with open(ACCOUNT_PATH, 'r') as f:
                    acct = json.load(f)
                return bool(acct.get("pin") or acct.get("password"))
        except Exception:
            pass
        return False

    @staticmethod
    def _idle_seconds():
        """Seconds since the last keyboard/mouse input anywhere on the
        system (GetLastInputInfo)."""
        import ctypes
        try:
            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
                return 0.0
            return (ctypes.windll.kernel32.GetTickCount() - lii.dwTime) / 1000.0
        except Exception:
            return 0.0

    def _auto_lock_tick(self):
        """Called by the 'auto-lock' service (15s tick on the systmanserv
        worker thread). If the idle threshold is met and a credential exists,
        flag the lock and hand it to the window thread — app state must only
        be touched there."""
        try:
            minutes = 0
            settings_path = os.path.join(self.tech_soft, 'settings.json')
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    minutes = json.load(f).get("auto_lock_minutes", 0) or 0
            if minutes <= 0:
                return
            if self._idle_seconds() < minutes * 60:
                return
            if not self._account_has_credential():
                return
            self._auto_lock_due = True
            self.window.post_task(self._apply_idle_lock)
        except Exception:
            pass

    def _apply_idle_lock(self):
        """Run on the window thread: if an auto-lock is due and we're not
        already locked or shutting down, show the lock screen."""
        if not self._auto_lock_due:
            return
        self._auto_lock_due = False
        if self._shutting_down:
            return
        from menus.lock_screen import LockScreenApp
        from menus.power_menu import PowerApp
        if isinstance(self.current_app, (LockScreenApp, PowerApp)):
            return
        self._lock_now()

    def _read_notifications(self):
        count = self._notifications.get_unread_count()
        latest = self._notifications.get_latest()
        if latest:
            self.synth.speak(f"{count} notification{'s' if count != 1 else ''}. Latest from {latest['source']}: {latest['text']}")
            self._notifications.mark_read()
        else:
            self.synth.speak("No notifications.")

    def _cycle_voice_profile(self):
        settings_path = os.path.join(self.tech_soft, 'settings.json')
        profiles = {}
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    profiles = json.load(f).get("voice_profiles", {})
            except Exception:
                pass
        if not profiles:
            self.synth.speak("No voice profiles saved. Use Options menu to create one.")
            return
        names = sorted(profiles.keys())
        current_voice = self.synth.get_voice_index()
        current_rate = self.synth.get_rate()
        current_pitch = self.synth.get_pitch()
        idx = 0
        for i, name in enumerate(names):
            p = profiles[name]
            if (p.get("voice_index") == current_voice and
                p.get("rate") == current_rate and
                p.get("pitch") == current_pitch):
                idx = (i + 1) % len(names)
                break
        profile_name = names[idx]
        profile = profiles[profile_name]
        try:
            self.synth.apply_profile(
                voice_index=profile.get("voice_index"),
                rate=profile.get("rate"),
                pitch=profile.get("pitch")
            )
            self.synth.speak(f"Profile: {profile_name}")
        except Exception:
            self.synth.speak("Failed to apply profile.")

    def _open_tutorial(self):
        self._typing_buffer = ""
        self.app_manager.push_current()
        self.current_app = TutorialApp(self, self.window)
        self.current_app.on_focus()
        self.app_manager.current_app = self.current_app

    def _check_startup_update(self):
        try:
            from core.updater import check_on_startup
            check_on_startup(synth=self.synth, window=self.window)
        except Exception:
            pass

    def _restart_process(self):
        # Preserve the app across the restart (same as hibernate, gated by
        # auto_resume_apps) so a restart lands back where the user was. The
        # current app here is the power menu (already inactive), so look
        # below it on the app stack for the app it interrupted.
        try:
            auto_resume = True
            settings_path = os.path.join(self.tech_soft, 'settings.json')
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    auto_resume = json.load(f).get("auto_resume_apps", True)
            if auto_resume:
                app = self.current_app
                if app is None or app.__class__.__module__ in (
                        "menus.power_menu", "menus.lock_screen"):
                    stack = getattr(self.app_manager, "_app_stack", [])
                    app = stack[-1] if stack else None
                if app is not None and app.__class__.__module__ not in (
                        "menus.power_menu", "menus.lock_screen"):
                    app_data = {
                        "app_module": app.__class__.__module__,
                        "app_class": app.__class__.__name__
                    }
                    if hasattr(app, "get_state"):
                        app_data["state"] = app.get_state()
                    with open(os.path.join(self.tech_soft, 'resume.json'), 'w') as f:
                        json.dump(app_data, f)
        except Exception as e:
            core.error_handler.log(e, "Saving restart resume data")
        subprocess.Popen([sys.executable] + sys.argv, creationflags=subprocess.CREATE_NO_WINDOW)
        self._exit_app(mode="restart")
        os._exit(0)

    def _dirty_apps(self):
        """Return the running apps that report unsaved changes."""
        dirty = []
        for app in self.app_manager.get_running_apps():
            try:
                if app.is_dirty():
                    dirty.append(app)
            except Exception:
                pass
        return dirty

    def _unsaved_app_names(self):
        """Natural-language list of the dirty apps' titles, or '' if none."""
        titles = []
        for app in self._dirty_apps():
            try:
                title = app.get_app_title()
            except Exception:
                title = None
            titles.append(title or "an app")
        if not titles:
            return ""
        if len(titles) == 1:
            return titles[0]
        if len(titles) == 2:
            return f"{titles[0]} and {titles[1]}"
        return f"{', '.join(titles[:-1])}, and {titles[-1]}"

    def _unsaved_blocks_exit(self):
        """Return True if shutdown/restart/sleep/hibernate should abort when apps
        have unsaved work (settings key block_on_unsaved, default True). When
        False, the app warns and proceeds instead."""
        try:
            settings_path = os.path.join(self.tech_soft, 'settings.json')
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    s = json.load(f)
                return s.get("block_on_unsaved", True)
        except Exception:
            pass
        return True

    def _unsaved_warnings_enabled(self):
        """Master switch for unsaved-work warnings on shutdown. When False,
        shutdown/restart/sleep/hibernate proceed silently regardless of unsaved
        work (settings key warn_unsaved_on_shutdown, default True)."""
        try:
            settings_path = os.path.join(self.tech_soft, 'settings.json')
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    s = json.load(f)
                return s.get("warn_unsaved_on_shutdown", True)
        except Exception:
            pass
        return True

    def _exit_app(self, mode="shutdown"):
        # Load latest settings for shutdown logic
        settings = {}
        settings_path = os.path.join(self.tech_soft, 'settings.json')
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
            except Exception as e: core.error_handler.log(e, "Loading settings")

        # Stop all background services cleanly
        try:
            from core.systmanserv import get_manager
            get_manager().shutdown_all()
        except Exception:
            pass

        # 7. Keyboard Lockout
        if settings.get("shutdown_key_protection", True):
            self._shutting_down = True

        # 6. Night Mode Filter
        if settings.get("night_mode_filter", False):
            try:
                self.window.update_text(" ")
                self.window.set_display_settings(bg_color=(0,0,0))
            except Exception as e: core.error_handler.log(e, "Applying night mode filter")

        # Delete resume.json unless hibernating or restarting (a restart keeps
        # the saved app so the new session resumes it; hibernate keeps it for
        # the same reason)
        resume_path = os.path.join(self.tech_soft, 'resume.json')
        if mode not in ("hibernate", "restart"):
            try:
                if os.path.exists(resume_path):
                    os.remove(resume_path)
            except Exception as e: core.error_handler.log(e, "Removing resume.json")
        else:
            # Hibernate: save current app if eligible
            if settings.get("auto_resume_apps", True) and self.current_app and self.current_app.active:
                app_module = self.current_app.__class__.__module__
                if app_module not in ("menus.power_menu", "menus.lock_screen"):
                    try:
                        app_data = {
                            "app_module": app_module,
                            "app_class": self.current_app.__class__.__name__
                        }
                        if hasattr(self.current_app, "get_state"):
                            app_data["state"] = self.current_app.get_state()
                        with open(resume_path, 'w') as f:
                            json.dump(app_data, f)
                    except Exception as e: core.error_handler.log(e, "Saving hibernate resume data")

        # 3. Volume Fade-Out
        if settings.get("smooth_shutdown_audio", True):
            try:
                get_audio_manager().fade_out(1000)
            except Exception as e: core.error_handler.log(e, "Fading out audio")
        else:
            try:
                get_audio_manager().stop_all()
            except Exception as e: core.error_handler.log(e, "Stopping audio")

        # 2. Custom Goodbye Message
        goodbye_msg = settings.get("custom_goodbye", "Shutting down Tech-Note.")
        if mode == "restart":
            goodbye_msg = "Restarting Tech-Note."
        elif mode == "sleep":
            goodbye_msg = "Entering Sleep Mode."
        elif mode == "hibernate":
            goodbye_msg = "Hibernating Tech-Note."

        # Warn about unsaved work before any lossy mode (shutdown, restart,
        # sleep, hibernate). Prepended so speech is not cut off by the goodbye.
        # Skipped entirely when unsaved-work warnings are disabled in settings.
        if self._unsaved_warnings_enabled():
            names = self._unsaved_app_names()
            if names:
                goodbye_msg = f"Warning: Unsaved work in {names}. " + goodbye_msg

        try:
            self.synth.speak(goodbye_msg)
        except Exception as e: core.error_handler.log(e, "Speaking goodbye message")

        try:
            if hasattr(self.synth, 'wait_until_done'):
                self.synth.wait_until_done(5000)
            else:
                time.sleep(1.5)
        except:
            time.sleep(1.5)

        if mode == "sleep":
            self.speak("Sleep mode active. Press any key to wake.")
            self._sleeping = True
            self._shutting_down = False
            # Restart background services for the resumed session (they were
            # stopped by shutdown_all above)
            try:
                from core.systmanserv import get_manager
                get_manager().start_all()
            except Exception:
                pass
            return

        # Play shutdown sound after speech finishes
        try:
            path = os.path.join(SOUNDS_DIR, 'shutdown.wav')
            if not os.path.exists(path):
                path = _get_sound_path('shutdown.wav')
            if not os.path.exists(path):
                path = _get_sound_path('shutdown.mp3')
            if not os.path.exists(path):
                path = _get_sound_path('unlock.mp3')
            if os.path.exists(path):
                get_audio_manager().play_blocking("ui", path)
        except Exception as e: core.error_handler.log(e, "Playing shutdown sound")

        self._write_clean_flag(True)

        try:
            from core.plugin_manager import get_plugin_manager
            get_plugin_manager().shutdown_all()
        except Exception as e:
            core.error_handler.log(e, "Plugin shutdown")

        try:
            self.window.close()
        except:
            pass
        os._exit(0)

    def _vk_to_char(self, vk):
        import ctypes
        if vk == win32con.VK_SPACE:
            return ' '
        if vk in (win32con.VK_RETURN, win32con.VK_BACK, win32con.VK_ESCAPE):
            return None
        state = (ctypes.c_byte * 256)()
        if not ctypes.windll.user32.GetKeyboardState(ctypes.byref(state)):
            return None
        buf = ctypes.create_unicode_buffer(5)
        hkl = ctypes.windll.user32.GetKeyboardLayout(0)
        sc = win32api.MapVirtualKey(vk, 0)
        res = ctypes.windll.user32.ToUnicodeEx(
            vk, sc, ctypes.byref(state), buf, len(buf), 0, hkl
        )
        if res > 0:
            return buf.value
        return None

    def _get_status_info(self):
        import datetime
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M" if self._get_time_format() == "24-hour" else "%I:%M %p").lstrip("0")
        date_str = now.strftime("%A, %B %d")
        status = f"{time_str}. {date_str}. "
        try:
            import psutil
            bat = psutil.sensors_battery()
            if bat:
                pct = int(bat.percent)
                plugged = "charging" if bat.power_plugged else "on battery"
                status += f"Battery {pct} percent, {plugged}."
        except:
            pass
        return status

    def _is_key_match(self, vk, action_name):
        bindings = self._key_bindings.get(action_name, [])
        if not bindings:
            defaults = {
                "next_item": [32],   # Space
                "prev_item": [8],    # Backspace
                "select": [13],      # Enter
                "back": [27],        # Escape
                "help": [112],       # F1
                "status": [116],     # F5
                "power_menu": [self._power_vk],
            }
            bindings = defaults.get(action_name, [])
        return vk in bindings

    def handle_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            space_chord = self.space_used_in_chord
            self.space_used_in_chord = False

        # Search mode Space handling
        if self._search_mode and vk == win32con.VK_SPACE:
            self._search_buffer += " "
            self.menu.search(self._search_buffer)
            return

        if self.current_app and self.current_app.active:
            try:
                self.current_app.on_key_up(vk)
            except Exception as e:
                print(f"App on_key_up error: {e}")
            return

        if vk == win32con.VK_SPACE:
            if not space_chord:
                # If no chord was used, trigger next_item on Space release
                if not (self.current_app and self.current_app.active):
                    if self.menu and self._is_key_match(vk, "next_item"):
                        self.menu.next()
                        self.window.update_text(self.menu.get_current_item().title)

    def handle_key(self, vk):
        if self._shutting_down:
            return
        print(f"Key pressed: {vk}")

        # Wake from sleep: the first keypress wakes the session. With a
        # PIN/password set, route through the lock screen instead of resuming
        # straight into the app; after unlock the interrupted app resumes.
        if self._sleeping:
            self._sleeping = False
            if self._account_has_credential():
                self._lock_now()
                return

        # If the current app already exited outside of on_key (e.g. sleep mode
        # or an on_key_up exit), resume the interrupted app / return to the menu.
        if self.current_app and not self.current_app.active:
            self._finalize_exited_app()
            return

        # Block all global shortcuts when locked or during setup/login
        from menus.lock_screen import LockScreenApp
        if isinstance(self.current_app, LockScreenApp):
            lock_app = self.current_app
            if lock_app and lock_app.active:
                try:
                    self.current_app.on_key(vk)
                except Exception as e:
                    print(f"Lock screen on_key error: {e}")
            # Detect unlock: the lock screen just exited during on_key.
            # This MUST be outside the active check - _unlock_done (called
            # from on_key) already set active=False and synced current_app.
            if not lock_app.active:
                self._last_unlock_time = time.time()
                if self.current_app is lock_app:
                    self.current_app = None
                if self.current_app is None and self.menu:
                    title = self.menu.get_current_item().title if self.menu.get_current_item() else "Main Menu"
                    self.window.update_text(title)
                    self.menu.announce_current()
            return

        if isinstance(self.current_app, TechNoteSetup):
            try:
                self.current_app.on_key(vk)
            except Exception as e:
                print(f"Setup on_key error: {e}")
            return

        # Power menu (layout-aware backtick) — blocked for 1s after unlock
        if time.time() - self._last_unlock_time > 1.0:
            if vk == self._power_vk or self._is_key_match(vk, "power_menu"):
                print("Global Power menu")
                self._open_power_menu()
                return

        # Global Options (Space + O)
        if self.window.space_down and vk == 0x4F:
            print("Global Chord: Space + O")
            self.space_used_in_chord = True
            self._open_options()
            return

        # Global Edit Main Menu (Space + E)
        if self.window.space_down and vk == 0x45:
            print("Global Chord: Space + E")
            self.space_used_in_chord = True
            self._open_edit_main_menu()
            return

        # Global Notifications (Space + N)
        if self.window.space_down and vk == 0x4E:
            print("Global Chord: Space + N")
            self.space_used_in_chord = True
            self._read_notifications()
            return

        # Repeat Last Speech (Space + R)
        if self.window.space_down and vk == 0x52:
            print("Global Chord: Space + R")
            self.space_used_in_chord = True
            self.synth.repeat_last()
            return

        # Cycle Voice Profile (Space + V)
        if self.window.space_down and vk == 0x56:
            print("Global Chord: Space + V")
            self.space_used_in_chord = True
            self._cycle_voice_profile()
            return

        # Global Tutorial (Shift + F1)
        if vk == win32con.VK_F1 and (win32api.GetAsyncKeyState(win32con.VK_SHIFT) & 0x8000):
            self._open_tutorial()
            return

        # State key announcements (before app delegation)
        if self._state_keys == "On" and vk in (0x14, 0x90, 0x91):
            state_map = {0x14: "Caps lock", 0x90: "Num lock", 0x91: "Scroll lock"}
            name = state_map[vk]
            is_on = win32api.GetKeyState(vk) & 1
            self.synth.speak(f"{name} {'on' if is_on else 'off'}")
            return

        # --- Active App Delegation (apps get ALL keys first) ---
        if self.current_app and self.current_app.active:
            text_active = self.current_app.is_text_input_active() if hasattr(self.current_app, 'is_text_input_active') else False
            masked = False
            if hasattr(self.current_app, 'is_masked_input'):
                try:
                    masked = bool(self.current_app.is_masked_input())
                except Exception:
                    masked = False

            # Word echo on Space (only when in text input)
            if text_active and self._word_echo == "On" and vk == win32con.VK_SPACE and self._typing_buffer:
                self.synth.speak(self._typing_buffer)
                self._typing_buffer = ""

            # Clear buffer on Enter or Escape
            if vk in (win32con.VK_RETURN, win32con.VK_ESCAPE):
                self._typing_buffer = ""

            # Character echo (when enabled): speak each typed character in
            # text input, never on masked fields like passwords. The same
            # pass accumulates characters into the typing buffer, which is
            # what Word Echo speaks on Space — both echo settings were dead
            # because nothing ever filled that buffer.
            if text_active and not masked:
                ch = self._vk_to_char(vk)
                if ch and ch.isprintable():
                    if vk != win32con.VK_SPACE:
                        self._typing_buffer += ch
                    if self._char_echo == "On" and vk != win32con.VK_SPACE:
                        self.synth.speak(ch)

            try:
                self.current_app.on_key(vk)
            except Exception as e:
                print(f"App on_key error: {e}")
            if not self.current_app.active:
                self._finalize_exited_app()
            return

        # --- Main Menu / No App Active ---
        if not self.menu:
            print("Menu not loaded")
            return

        # Flush any keyboard events that queued during the unlock sound.
        # play_blocking freezes the thread; keys presssed while the sound
        # plays land in the OS queue and fire now — discard them.
        if time.time() - self._last_unlock_time < 1.0:
            return

        if self._is_key_match(vk, "help"):
            self.synth.speak(f"Main Menu. Space for next, Backspace for previous. Enter to open. Space plus O for options. Space plus E to edit menu. {self._power_key_name} for power.")
            return

        if self._is_key_match(vk, "status"):
            info = self._get_status_info()
            self.synth.speak(info)
            return

        # Search mode trigger
        if vk == 0xBF:
            self._search_mode = True
            self._search_buffer = ""
            self.synth.speak("Search apps")
            self.window.update_text("Search:")
            return

        # Search mode key handling
        if self._search_mode:
            if vk == win32con.VK_RETURN:
                self._search_mode = False
                self.menu.select()
            elif vk == win32con.VK_ESCAPE:
                self._search_mode = False
                self._search_buffer = ""
                self.menu.clear_search()
                self.menu.announce_current()
            elif vk == win32con.VK_BACK:
                if self._search_buffer:
                    self._search_buffer = self._search_buffer[:-1]
                    if self._search_buffer:
                        self.menu.search(self._search_buffer)
                    else:
                        self.menu.clear_search()
            else:
                ch = self._vk_to_char(vk)
                if ch:
                    self._search_buffer += ch
                    self.menu.search(self._search_buffer)
            return

        if self._is_key_match(vk, "next_item") and vk != win32con.VK_SPACE:
            print("Next item")
            self.menu.next()
        elif self._is_key_match(vk, "prev_item"):
            print("Previous item")
            self.menu.previous()
        elif self._is_key_match(vk, "select"):
            self.menu.select()
        elif self._is_key_match(vk, "back"):
            self.menu.back()
        elif 0x41 <= vk <= 0x5A:
            char = chr(vk)
            self.menu.first_letter_nav(char)
        elif vk == 0xBB or vk == win32con.VK_CONTROL:
            self.synth.stop()

        if self.menu:
            title = self.menu.get_current_item().title if self.menu.get_current_item() else "Main Menu"
            print(f"Updating window text to: {title}")
            self.window.update_text(title)

    def run(self):
        try:
            while self.window.running:
                time.sleep(0.1)
        finally:
            self.window.close()

if __name__ == "__main__":
    # Redirect all stdout and stderr to out.log in the project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    out_log_path = os.path.join(project_root, "out.log")
    try:
        log_file = open(out_log_path, "w", buffering=1)
        sys.stdout = log_file
        sys.stderr = log_file
        import atexit
        atexit.register(lambda: log_file.close() if not log_file.closed else None)
    except Exception as e:
        print(f"Failed to redirect output to {out_log_path}: {e}", file=sys.stderr)

    try:
        app = BrailleNoteApp()
        app.run()
    except Exception as e:
        import traceback
        import sys
        print("\n--- APPLICATION CRASH ---", file=sys.stderr)
        print("An unhandled exception occurred:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        
        project_root = os.path.dirname(os.path.abspath(__file__))
        crash_log_path = os.path.join(project_root, "crash.log")
        
        try:
            with open(crash_log_path, "w") as f:
                traceback.print_exc(file=f)
            print(f"Crash details saved to {crash_log_path}", file=sys.stderr)
        except Exception as file_e:
            print(f"ERROR: Could not write to {crash_log_path}: {file_e}", file=sys.stderr)
        
        input("Application crashed. Check out.log and crash.log for details. Press Enter to exit.")
