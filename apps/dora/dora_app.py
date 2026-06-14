import threading
import win32con
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
        self._setup = None
        self._build_menu()
        if is_first_run():
            self._run_setup()

    def _build_menu(self):
        root = MenuNode("Dora Assistant")
        root.add_child(MenuNode("Activate Voice", self._activate_voice))
        root.add_child(MenuNode("Enter Command", self._enter_command_mode))
        root.add_child(MenuNode("Toggle AI Chat", self._toggle_ai))
        root.add_child(MenuNode("Set Timer", self._set_timer))
        root.add_child(MenuNode("Check Battery", self._check_battery))
        root.add_child(MenuNode("Tell Time", self._tell_time))
        root.add_child(MenuNode("Settings", self._settings_menu))
        root.add_child(MenuNode("Exit Dora", self._exit_dora))
        self.menu = MenuSystem(root, self.speak)

    def _build_settings_menu(self):
        root = MenuNode("Dora Settings")
        settings = load_settings()
        ai_state = "On" if settings.get('ai_enabled') else "Off"
        root.add_child(MenuNode(f"AI Chat: {ai_state}", self._toggle_ai))
        root.add_child(MenuNode("Change Wake Word", self._change_wake_word))
        root.add_child(MenuNode("AI Endpoint", self._change_endpoint))
        root.add_child(MenuNode("AI Model", self._change_model))
        root.add_child(MenuNode("Back", self._back_to_main))
        return MenuSystem(root, self.speak)

    def on_focus(self):
        self._build_menu()
        item = self.menu.get_current_item()
        title = item.title if item else "Dora Assistant"
        self.window.update_text(title)
        self.speak("Dora Assistant. " + title)

    def on_key(self, vk):
        if self._setup and self._setup.active:
            self._setup.on_key(vk)
            if not self._setup.active:
                self._setup = None
                self.assistant.settings = load_settings()
                self.assistant.username = self.assistant.settings.get('username', 'User')
                self._build_menu()
                self.speak("Setup complete. Dora is ready.")
            return
        if self.menu is None:
            return
        if vk == win32con.VK_SPACE:
            self.menu.next()
        elif vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif vk == win32con.VK_ESCAPE:
            self._exit_dora()
        item = self.menu.get_current_item()
        if item:
            self.window.update_text(item.title)

    def _activate_voice(self):
        if self.voice_thread and self.voice_thread.is_alive():
            self.speak("Voice mode already active.")
            return
        self.voice_thread = threading.Thread(
            target=self.assistant.run_voice_loop, daemon=True
        )
        self.voice_thread.start()

    def _enter_command_mode(self):
        self.speak("Say a command.")
        command = self.assistant.listen()
        if command:
            self.assistant.process_command(command)
        else:
            self.speak("No command heard.")

    def _toggle_ai(self):
        settings = load_settings()
        settings['ai_enabled'] = not settings.get('ai_enabled', False)
        save_settings(settings)
        self.assistant.ai_mode = settings['ai_enabled']
        state = "enabled" if settings['ai_enabled'] else "disabled"
        self.speak(f"AI chat {state}.")

    def _set_timer(self):
        self.speak("How many minutes?")
        response = self.assistant.listen()
        if response and any(c.isdigit() for c in response):
            timer_skill.start_timer(self.assistant, response)
        else:
            self.speak("No time specified.")

    def _check_battery(self):
        from apps.dora.skills.system import get_battery_status
        get_battery_status(self.assistant)

    def _tell_time(self):
        from apps.dora.skills.information import tell_time
        tell_time(self.assistant)

    def _settings_menu(self):
        self.menu = self._build_settings_menu()
        self.menu.announce_current()

    def _change_wake_word(self):
        self.speak("Say the wake word.")
        word = self.assistant.listen()
        if word:
            settings = load_settings()
            settings['wake_word'] = word.split()[0].lower()
            save_settings(settings)
            self.assistant.settings = load_settings()
            self.speak(f"Wake word set to {word.split()[0]}.")

    def _change_endpoint(self):
        self.speak("Say the AI endpoint URL.")
        url = self.assistant.listen()
        if url and 'http' in url:
            settings = load_settings()
            settings['ai_endpoint'] = url
            save_settings(settings)
            self.assistant.settings = load_settings()
            self.speak("Endpoint updated.")

    def _change_model(self):
        self.speak("Say the model name.")
        model = self.assistant.listen()
        if model:
            settings = load_settings()
            settings['ai_model'] = model.strip()
            save_settings(settings)
            self.assistant.settings = load_settings()
            self.speak(f"Model set to {model.strip()}.")

    def _back_to_main(self):
        self._build_menu()
        self.menu.announce_current()

    def _run_setup(self):
        self._setup = DoraSetup(self.assistant, self.speak)
        self._setup.run()

    def _exit_dora(self):
        self.assistant.stop_voice_loop()
        self.assistant.is_running = False
        self.exit_app()
