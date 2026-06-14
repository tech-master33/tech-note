class SoftApp:
    def __init__(self, manager, window, app_type='app'):
        self.manager = manager
        self.window = window
        self.speak = manager.speak
        self.stop = manager.stop
        self.active = True
        self.app_type = app_type

    def on_key(self, vk):
        """Handle keyboard input when the app is active."""
        pass

    def on_key_up(self, vk):
        """Handle keyboard release when the app is active."""
        pass

    def on_focus(self):
        """Called when the app becomes active."""
        pass

    def get_help_text(self):
        """Return a string explaining the app's controls."""
        return "No help available for this application."

    def exit_app(self):
        """Close the app and return to the main menu."""
        self.manager.reset_temp_params()
        self.active = False
