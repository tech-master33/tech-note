import abc


class PluginOptionMenu:
    """A menu a plugin contributes to Options.

    title — the spoken/displayed menu label.
    path — where in the Options tree the menu appears, as a pipe-separated
        route such as "TTS Menu|Advanced". Intermediate nodes are created
        if missing. Empty means the default slot: Options > Plugin
        Settings > <plugin name>.
    build_fn(options_app) -> MenuNode — called when the user opens the
        menu. It receives the OptionsApp instance, so a plugin can speak(),
        read/write `app.settings`, persist with `app._save_settings()`, and
        build its screen with the Tech-Note UI primitives (MenuNode,
        MenuSystem, `_build_list_menu`, `_build_numeric_menu`, ...).
    """

    def __init__(self, title, build_fn, path=""):
        self.title = title
        self.build_fn = build_fn
        self.path = path


class ScrugnPlugin(abc.ABC):
    plugin_type = None
    plugin_name = ""
    plugin_version = "1.0"

    @abc.abstractmethod
    def initialize(self):
        pass

    @abc.abstractmethod
    def shutdown(self):
        pass

    def get_commands(self):
        return []

    def get_option_menus(self):
        """Option screens this plugin contributes to the Options app.

        Return a list of PluginOptionMenu. Each entry becomes a menu the
        user can open from Options; the menu is built with Tech-Note UI
        primitives at open time.
        """
        return []


class SynthPlugin(ScrugnPlugin):
    plugin_type = "synth"

    @abc.abstractmethod
    def speak(self, text, interrupt=True):
        pass

    @abc.abstractmethod
    def stop(self):
        pass

    def get_rate(self):
        return 0

    def set_rate(self, value):
        pass

    def get_volume(self):
        return 100

    def set_volume(self, value):
        pass

    def get_pitch(self):
        return 50

    def set_pitch(self, value):
        pass

    def get_voice_names(self):
        return []

    def set_voice(self, name):
        pass

    def get_current_voice_name(self):
        return ""

    def get_voice_index(self):
        return 0

    def set_voice_by_index(self, index):
        pass

    def set_punctuation_level(self, level):
        pass

    def get_punctuation_level(self):
        return "Some"

    def set_capital_pitch_change(self, value):
        pass

    def get_capital_pitch_change(self):
        return "Off"

    def set_volume_ducking(self, enabled):
        pass

    def get_volume_ducking(self):
        return False

    def save_defaults(self):
        pass

    def reset_temp_params(self):
        pass

    def set_temp_params(self, rate=None, pitch=None, voice_index=None):
        pass

    def apply_profile(self, voice_index=None, rate=None, pitch=None):
        pass

    def repeat_last(self):
        pass

    def wait_until_done(self, timeout_ms=5000):
        pass

    def get_speech_history(self):
        return []

    def get_history_max(self):
        return 50

    def set_history_max(self, value):
        pass


class BrailleDisplayPlugin(ScrugnPlugin):
    plugin_type = "braille"

    @abc.abstractmethod
    def write(self, text):
        pass

    @abc.abstractmethod
    def read_input(self):
        pass


class FilterPlugin(ScrugnPlugin):
    plugin_type = "filter"

    @abc.abstractmethod
    def process(self, text):
        return text
