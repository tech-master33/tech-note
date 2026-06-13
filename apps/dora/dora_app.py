import threading
import win32con
import win32api
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from apps.dora.dora_core import DoraAssistant
from apps.dora.dora_config import load_settings, save_settings, is_first_run
from apps.dora.dora_setup import DoraSetup
from apps.dora.skills import timer as timer_skill

class DoraApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.assistant = DoraAssistant(self.speak)
        self.voice_thread = None
        self._text_mode = None
        self._text_buffer = ""
        self._text_field = None
        self._build_menu()
        if is_first_run():
            self._run_setup()

    def _build_menu(self):
        root = MenuNode("Dora Assistant")
        root.add_child(MenuNode("Enter Command", self._enter_command_mode))
        root.add_child(MenuNode("Activate Voice", self._activate_voice))
        root.add_child(MenuNode("Set Timer", self._set_timer))
        root.add_child(MenuNode("Check Battery", self._check_battery))
        root.add_child(MenuNode("Tell Time", self._tell_time))
        root.add_child(MenuNode("Settings", self._settings_menu))
        root.add_child(MenuNode("Exit Dora", self._exit_dora))
        self.menu = MenuSystem(root, self.speak)

    def on_focus(self):
        self._build_menu()
        item = self.menu.get_current_item()
        title = item.title if item else "Dora Assistant"
        self.window.update_text(title)
        self.speak("Dora Assistant. " + title)

    def on_key(self, vk):
        if hasattr(self, '_setup') and self._setup and self._setup.active:
            self._setup.on_key(vk)
            if not self._setup.active:
                self._setup = None
                self.assistant.settings = load_settings()
                self.assistant.username = self.assistant.settings.get('username', 'User')
                self._build_menu()
                self.speak("Setup complete. Dora is ready.")
            return

        if self._text_mode:
            if self._text_mode in ("command", "text", "timer"):
                self._handle_text_input(vk)
            return

        if self.menu is None:
            return
        if vk == win32con.VK_ESCAPE:
            self._exit_dora()
            return
        if vk in (win32con.VK_BACK, win32con.VK_UP):
            self.menu.previous()
        elif vk in (win32con.VK_DOWN, win32con.VK_SPACE):
            self.menu.next()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        item = self.menu.get_current_item()
        if item:
            self.window.update_text(item.title)

    def _enter_command_mode(self):
        self._text_mode = "command"
        self._text_buffer = ""
        self.speak("Type a command. Press Enter to run.")
        self.window.update_text("Command: ")

    def _settings_menu(self):
        self._build_settings_menu()
        self.menu.announce_current()

    def _build_settings_menu(self):
        root = MenuNode("Dora Settings")
        settings = load_settings()
        ai_state = "On" if settings.get('ai_enabled') else "Off"
        root.add_child(MenuNode(f"AI Chat: {ai_state}", self._toggle_ai))
        root.add_child(MenuNode("Change Wake Word", lambda: self._start_text_input("wake_word", "Enter wake word.")))
        root.add_child(MenuNode("AI Endpoint", lambda: self._start_text_input("ai_endpoint", "Enter AI endpoint URL.")))
        root.add_child(MenuNode("AI Model", lambda: self._start_text_input("ai_model", "Enter AI model name.")))
        root.add_child(MenuNode("Back", self._back_to_main))
        self.menu = MenuSystem(root, self.speak)

    def _start_text_input(self, field, prompt):
        self._text_mode = "text"
        self._text_field = field
        self._text_buffer = ""
        self.speak(prompt)
        self.window.update_text(f"{field.replace('_', ' ').title()}: ")

    def _handle_text_input(self, vk):
        if vk == win32con.VK_ESCAPE:
            self._text_mode = None
            self._back_to_main()
            return
        if vk == win32con.VK_RETURN:
            val = self._text_buffer.strip()
            if self._text_mode == "command":
                if val:
                    self.assistant.process_command(val.lower())
                else:
                    self.speak("No command entered.")
                self._text_mode = None
                self._back_to_main()
                return
            if self._text_mode == "text":
                if val:
                    self._save_text_setting(val)
                else:
                    self.speak("Cannot be empty.")
                return
            if self._text_mode == "timer":
                if val and any(c.isdigit() for c in val):
                    timer_skill.start_timer(self.assistant, val)
                else:
                    self.speak("No time specified.")
                self._text_mode = None
                self._back_to_main()
                return
            return
        if vk == win32con.VK_BACK:
            if self._text_buffer:
                self._text_buffer = self._text_buffer[:-1]
                self.window.update_text(self._text_buffer if self._text_buffer else " ")
            return
        ch = self._vk_to_char(vk)
        if ch is not None:
            self._text_buffer += ch
            self.window.update_text(self._text_buffer)

    def _save_text_setting(self, val):
        settings = load_settings()
        if self._text_field == "wake_word":
            word = val.split()[0].lower()
            settings['wake_word'] = word
            self.assistant.settings = load_settings()
            self.speak(f"Wake word set to {word}.")
        elif self._text_field == "ai_endpoint":
            if 'http' in val or 'localhost' in val:
                settings['ai_endpoint'] = val
                self.assistant.settings = load_settings()
                self.speak("Endpoint updated.")
            else:
                self.speak("Invalid URL.")
                return
        elif self._text_field == "ai_model":
            settings['ai_model'] = val.strip()
            self.assistant.settings = load_settings()
            self.speak(f"Model set to {val.strip()}.")
        save_settings(settings)
        self._text_mode = None
        self._settings_menu()

    def _vk_to_char(self, vk):
        shift = win32api.GetAsyncKeyState(win32con.VK_SHIFT) & 0x8000
        caps = win32api.GetAsyncKeyState(win32con.VK_CAPITAL) & 1
        if 0x41 <= vk <= 0x5A:
            upper = shift ^ caps
            return chr(vk).upper() if upper else chr(vk).lower()
        shift_syms = {0x30: ')', 0x31: '!', 0x32: '@', 0x33: '#',
                      0x34: '$', 0x35: '%', 0x36: '^', 0x37: '&',
                      0x38: '*', 0x39: '('}
        if 0x30 <= vk <= 0x39:
            return shift_syms[vk] if shift else chr(vk)
        if vk == win32con.VK_SPACE:
            return ' '
        sym_map = {
            0xBD: ('-', '_'), 0xBB: ('=', '+'), 0xC0: ('`', '~'),
            0xDB: ('[', '{'), 0xDD: (']', '}'), 0xDC: ('\\', '|'),
            0xBA: (';', ':'), 0xDE: ("'", '"'),
            0xBC: (',', '<'), 0xBE: ('.', '>'), 0xBF: ('/', '?'),
        }
        if vk in sym_map:
            return sym_map[vk][1] if shift else sym_map[vk][0]
        if vk == 0xDC:
            return '|' if shift else '\\'
        return None

    def _activate_voice(self):
        if self.voice_thread and self.voice_thread.is_alive():
            self.speak("Voice mode already active.")
            return
        self.voice_thread = threading.Thread(
            target=self.assistant.run_voice_loop, daemon=True
        )
        self.voice_thread.start()

    def _toggle_ai(self):
        settings = load_settings()
        settings['ai_enabled'] = not settings.get('ai_enabled', False)
        save_settings(settings)
        self.assistant.ai_mode = settings['ai_enabled']
        state = "enabled" if settings['ai_enabled'] else "disabled"
        self.speak(f"AI chat {state}.")
        self._settings_menu()

    def _set_timer(self):
        self._text_mode = "timer"
        self._text_buffer = ""
        self.speak("Enter minutes for the timer.")
        self.window.update_text("Timer minutes: ")

    def _check_battery(self):
        from apps.dora.skills.system import get_battery_status
        get_battery_status(self.assistant)

    def _tell_time(self):
        from apps.dora.skills.information import tell_time
        tell_time(self.assistant)

    def _back_to_main(self):
        self._text_mode = None
        self._build_menu()
        self.menu.announce_current()

    def _run_setup(self):
        setup = DoraSetup(self.assistant, self.speak)
        self._text_mode = None
        self._setup = setup
        setup.run()

    def _exit_dora(self):
        self.assistant.stop_voice_loop()
        self.assistant.is_running = False
        self.exit_app()
