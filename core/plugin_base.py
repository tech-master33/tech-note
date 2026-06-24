import abc


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
