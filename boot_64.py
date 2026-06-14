import os
import sys
import json
import subprocess
import win32api
import win32con
import threading
import time
import pythoncom
from core.menu import MenuSystem, build_braillenote_menu, _get_sound_path, SOUNDS_DIR, SOUND_SCHEME
from ui.stealth_window import StealthWindow
from synths.sapi_synth import SapiSynthBase
from synths.registry import create_synth
from apps.options_menu import OptionsApp
from apps.power_menu import PowerApp
from apps.tutorial_app import TutorialApp
from core.setup_core import TechNoteSetup
from core.audio_player import AudioPlayer
from core.config import TECH_SOFT

pythoncom.CoInitialize()

class BrailleNoteApp:
    def __init__(self):
        self.tech_soft = TECH_SOFT
        self.assistant = None
        if not os.path.exists(self.tech_soft):
            os.makedirs(self.tech_soft)
            for folder in ['documents', 'downloads', 'contacts', 'desktop']:
                os.makedirs(os.path.join(self.tech_soft, folder))

        self.synth = SapiSynthBase()
        self._apply_settings()
        self.window = StealthWindow(on_key_down=self.handle_key)

        self.menu = None
        self.current_app = None
        self._typing_buffer = ""
        self._char_echo = "Off"
        self._word_echo = "Off"
        self._key_bindings = {}
        self._announce_position = True
        self._state_keys = "Off"

        # Detect keyboard layout for power key assignment
        self._detect_keyboard_layout()

        # Play startup sound before any speech
        self._play_startup_sound()

        # Apply visual settings to window (may trigger speech)
        self._apply_visual_settings()

    def _play_startup_sound(self):
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
            AudioPlayer().play_sound_blocking(path)
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
        if saved_layout in ("US", "UK"):
            self._keyboard_layout = saved_layout
        else:
            hkl = win32api.GetKeyboardLayout(0)
            lang_id = hkl & 0xFFFF
            self._keyboard_layout = "UK" if lang_id == 0x0809 else "US"
        if self._keyboard_layout == "UK":
            self._power_vk = 0xDF
            self._power_key_name = "backtick (left of Z)"
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
            except: pass

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
            except Exception:
                pass
        else:
            self._char_echo = "Off"
            self._word_echo = "Off"
            self._key_bindings = {}

    def _start_setup(self):
        setup = TechNoteSetup(self.synth, self.window)
        setup.finish_callback = self.on_setup_complete
        self.current_app = setup
        setup.run_setup()

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
            self.synth.speak("Account corrupted. Re-running setup.")
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

        if self.account.get("pin") or self.account.get("password"):
            self.launch_app(lambda m, w: self._create_lock_screen(m, w))
        else:
            self.load_main_menu()

    def load_main_menu(self):
        import core.menu
        core.menu.ANNOUNCE_POSITION = self._announce_position == "On"
        self.menu_root = build_braillenote_menu(
            self.synth, self.window, self.launch_app, self._reset_and_restart
        )
        self.menu = MenuSystem(self.menu_root, self.synth.speak)
        self.synth.speak("Main Menu")

    def _create_lock_screen(self, synth, window):
        from apps.lock_screen import LockScreenApp
        return LockScreenApp(synth, window, self.load_main_menu)

    def launch_app(self, app_class_or_callable):
        self._typing_buffer = ""
        self.current_app = app_class_or_callable(self.synth, self.window)
        self.current_app.on_focus()

    def _open_options(self):
        if self.menu is None:
            return
        self._typing_buffer = ""
        self.current_app = OptionsApp(self.synth, self.window)
        self.current_app.on_focus()

    def _open_power_menu(self):
        if self.menu is None:
            return
        self._typing_buffer = ""
        self.current_app = PowerApp(
            self.synth, self.window,
            on_restart=self._reload_app,
            on_exit=self._exit_app
        )
        self.current_app.on_focus()

    def _open_tutorial(self):
        if self.menu is None and not self.current_app:
            return
        self._typing_buffer = ""
        self.current_app = TutorialApp(self.synth, self.window)
        self.current_app.on_focus()

    def _restart_process(self):
        subprocess.Popen([sys.executable] + sys.argv, creationflags=subprocess.CREATE_NO_WINDOW)
        self._exit_app()
        os._exit(0)

    def _exit_app(self):
        self.window.close()

    def _activate_assistant(self):
        if self.assistant is None:
            from core.assistant import VoiceAssistant
            self.assistant = VoiceAssistant(
                self.synth.speak,
                on_shutdown=self._exit_app,
                on_restart=self._reload_app,
            )
        threading.Thread(target=self.assistant.run, daemon=True).start()

    def _get_status_info(self):
        import datetime
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip("0")
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
                "next_item": [32],
                "prev_item": [8],
                "select": [13],
                "back": [27],
                "help": [112],
                "status": [116],
                "power_menu": [self._power_vk],
            }
            bindings = defaults.get(action_name, [])
        return vk in bindings

    def handle_key(self, vk):
        print(f"Key pressed: {vk}")

        # --- Truly Global (always work, before app delegation) ---

        # Voice Assistant (F2)
        if vk == win32con.VK_F2:
            self._activate_assistant()
            return

        # Power menu (layout-aware backtick)
        if vk == self._power_vk or self._is_key_match(vk, "power_menu"):
            print("Global Power menu")
            self._open_power_menu()
            return

        # Global Options (Space + O)
        if self.window.space_down and vk == 0x4F:
            print("Global Chord: Space + O")
            self._open_options()
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
            # Character echo
            if self._char_echo == "On" and 0x30 <= vk <= 0x5A:
                try:
                    shift = win32api.GetAsyncKeyState(win32con.VK_SHIFT) & 0x8000
                    caps = win32api.GetAsyncKeyState(win32con.VK_CAPITAL) & 1
                    if 0x41 <= vk <= 0x5A:
                        upper = shift ^ caps
                        ch = chr(vk) if upper else chr(vk).lower()
                    else:
                        ch = chr(vk)
                    self.synth.speak(ch)
                    self._typing_buffer += ch
                except:
                    self._typing_buffer += chr(vk) if 0x30 <= vk <= 0x5A else ""
            # Word echo on Space
            if self._word_echo == "On" and vk == win32con.VK_SPACE and self._typing_buffer:
                self.synth.speak(self._typing_buffer)
                self._typing_buffer = ""
            # Clear buffer on Enter or Escape
            if vk in (win32con.VK_RETURN, win32con.VK_ESCAPE):
                self._typing_buffer = ""

            try:
                self.current_app.on_key(vk)
            except Exception as e:
                print(f"App on_key error: {e}")
            if not self.current_app.active:
                self.current_app = None
                if self.menu:
                    self.menu.announce_current()
            return

        # --- Main Menu / No App Active ---
        if not self.menu:
            print("Menu not loaded")
            return

        if self._is_key_match(vk, "help"):
            self.synth.speak(f"Main Menu. Space for next, Backspace for previous. Enter to open. Space plus O for options. {self._power_key_name} for power. Shift F1 for tutorial.")
            return

        if self._is_key_match(vk, "status"):
            info = self._get_status_info()
            self.synth.speak(info)
            return

        if self._is_key_match(vk, "next_item"):
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
        log_file = open(out_log_path, "a", buffering=1)
        sys.stdout = log_file
        sys.stderr = log_file
    except Exception as e:
        print(f"Failed to redirect output to {out_log_path}: {e}", file=sys.stderr)

    try:
        app = BrailleNoteApp()
        app.run()
    except Exception as e: # Catch the exception object
        import traceback
        import sys # Import sys for stderr
        print("\n--- APPLICATION CRASH ---", file=sys.stderr)
        print("An unhandled exception occurred:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr) # Print to stderr
        
        # Ensure crash.log is written to the project root explicitly
        project_root = os.path.dirname(os.path.abspath(__file__))
        crash_log_path = os.path.join(project_root, "crash.log")
        
        try:
            with open(crash_log_path, "w") as f:
                traceback.print_exc(file=f)
            print(f"Crash details saved to {crash_log_path}", file=sys.stderr)
        except Exception as file_e: # Catch exception during file write
            print(f"ERROR: Could not write to {crash_log_path}: {file_e}", file=sys.stderr)
            print("Please check file permissions or disk space.", file=sys.stderr)
        
        input("Application crashed. Check out.log and crash.log for details. Press Enter to exit.")
