import os
import sys
import json
import win32con
import time
import comtypes.client
import pythoncom
from core.menu import MenuSystem, build_braillenote_menu
from ui.stealth_window import StealthWindow
from synths.sapi_synth import SapiSynthBase
from synths.registry import create_synth
from apps.lock_screen import LockScreenApp
from apps.options_menu import OptionsApp
from apps.power_menu import PowerApp
from core.setup_core import TechNoteSetup
from core.audio_player import AudioPlayer
from core.config import TECH_SOFT

pythoncom.CoInitialize()

class BrailleNoteApp:
    def __init__(self):
        self.tech_soft = TECH_SOFT
        if not os.path.exists(self.tech_soft):
            os.makedirs(self.tech_soft)
            for folder in ['documents', 'downloads', 'contacts', 'desktop']:
                os.makedirs(os.path.join(self.tech_soft, folder))

        self.synth = SapiSynthBase()
        self._apply_settings()
        self.window = StealthWindow(on_key_down=self.handle_key)
        
        # Apply visual settings to window
        self._apply_visual_settings()
        
        self.menu = None
        self.current_app = None

        # Play startup sound only if enabled
        settings_path = os.path.join(self.tech_soft, 'settings.json')
        play_startup = True
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    s = json.load(f)
                if s.get("startup_sound") == "Off":
                    play_startup = False
            except: pass

        if play_startup:
            startup_sound = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sounds', 'startup.mp3')
            if os.path.exists(startup_sound):
                player = AudioPlayer()
                player.play_sound_blocking(startup_sound)

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
            except Exception:
                pass

    def _start_setup(self):
        setup = TechNoteSetup(self.synth, self.window)
        setup.finish_callback = self.on_setup_complete
        self.current_app = setup
        setup.run_setup()

    def _reload_app(self):
        self.current_app = None
        self.menu = None
        account_path = os.path.join(self.tech_soft, 'account.json')
        if os.path.exists(account_path):
            self.load_account_and_menu(account_path)
        else:
            self._start_setup()

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

        self.synth.set_voice(self.account.get('default_synth', 'Auto'))

        if self.account.get("pin"):
            self.launch_app(lambda m, w: LockScreenApp(m, w, self.load_main_menu))
        else:
            self.load_main_menu()

    def load_main_menu(self):
        self.menu_root = build_braillenote_menu(
            self.synth, self.window, self.launch_app, self._reset_and_restart
        )
        self.menu = MenuSystem(self.menu_root, self.synth.speak)
        self.synth.speak("Main Menu")

    def launch_app(self, app_class):
        self.current_app = app_class(self.synth, self.window)
        self.current_app.on_focus()

    def _open_options(self):
        if self.menu is None:
            return
        self.current_app = OptionsApp(self.synth, self.window)
        self.current_app.on_focus()

    def _open_power_menu(self):
        if self.menu is None:
            return
        self.current_app = PowerApp(
            self.synth, self.window,
            on_restart=self._reload_app,
            on_exit=self._exit_app
        )
        self.current_app.on_focus()

    def _exit_app(self):
        self.window.close()

    def _get_status_info(self):
        import datetime
        import psutil
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip("0")
        date_str = now.strftime("%A, %B %d")
        status = f"{time_str}. {date_str}. "
        try:
            bat = psutil.sensors_battery()
            if bat:
                pct = int(bat.percent)
                plugged = "charging" if bat.power_plugged else "on battery"
                status += f"Battery {pct} percent, {plugged}."
        except:
            pass
        return status

    def handle_key(self, vk):
        print(f"Key pressed: {vk}")
        
        # --- Truly Global Shortcuts (Always Work) ---

        # Global Status Bar (F5)
        if vk == win32con.VK_F5:
            info = self._get_status_info()
            self.synth.speak(info)
            return

        # Global Help (F1)
        if vk == win32con.VK_F1:
            if self.current_app and self.current_app.active:
                self.synth.speak(self.current_app.get_help_text())
            else:
                self.synth.speak("Main Menu. Space for next, Backspace for previous. Enter to open. Space plus O for options. Backtick for power.")
            return

        # Global Options (Space + O)
        if self.window.space_down and vk == 0x4F:
            print("Global Chord: Space + O")
            self._open_options()
            return

        # Global Power Menu (Backtick / Grave)
        if vk == 0xC0 or vk == 0xDF:
            print("Global Power menu")
            self._open_power_menu()
            return

        # --- Active App Delegation ---
        if self.current_app and self.current_app.active:
            self.current_app.on_key(vk)
            if not self.current_app.active:
                self.current_app = None
                if self.menu:
                    self.menu.announce_current()
            return

        # --- Main Menu Navigation ---
        if not self.menu:
            print("Menu not loaded")
            return

        if vk == win32con.VK_SPACE:
            print("Space detected")
            self.menu.next()
        elif vk == win32con.VK_BACK:
            print("Backspace detected")
            self.menu.previous()
        elif vk == win32con.VK_DOWN:
            self.menu.next()
        elif vk == win32con.VK_UP:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif vk == win32con.VK_ESCAPE:
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
    try:
        app = BrailleNoteApp()
        app.run()
    except Exception:
        import traceback
        with open("crash.log", "w") as f:
            traceback.print_exc(file=f)
        input("Application crashed. Check crash.log for details. Press Enter to exit.")
