import core.error_handler

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

    def on_pause(self):
        """Called when another app is about to become active."""
        pass

    def on_resume(self):
        """Called when this app becomes active again after being paused."""
        pass

    def get_help_text(self):
        """Return a string explaining the app's controls."""
        return "No help available for this application."

    def get_state(self):
        """Return serializable state for save/resume."""
        return None

    def set_state(self, state):
        """Restore state from saved data."""
        pass

    def _vk_to_char(self, vk):
        import ctypes
        import win32api
        import win32con

        if vk == win32con.VK_SPACE: return ' '
        if vk == win32con.VK_RETURN: return None
        if vk == win32con.VK_BACK: return None

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

    def is_text_input_active(self):
        return False

    def exit_app(self):
        """Close the app and return to the main menu."""
        self.manager.reset_temp_params()
        self.active = False


class AppManager:
    def __init__(self, manager):
        self.manager = manager
        self.current_app = None
        self._app_stack = []

    def launch(self, app_class_or_callable):
        try:
            if self.current_app and self.current_app.active:
                try:
                    self.current_app.on_pause()
                except Exception as e:
                    core.error_handler.log(e, f"on_pause failed for {type(self.current_app).__name__}")
            new_app = app_class_or_callable(self.manager, self.manager.window)
            new_app.on_focus()
            if self.current_app:
                self._app_stack.append(self.current_app)
            self.current_app = new_app
            return True
        except Exception as e:
            core.error_handler.log(e, f"AppManager.launch failed for {app_class_or_callable}", level=core.error_handler.LEVEL_ERROR)
            if self.current_app:
                try:
                    self.current_app.on_resume()
                except Exception:
                    pass
            return False

    def exit_current(self):
        if not self.current_app:
            return
        try:
            self.current_app.exit_app()
        except Exception as e:
            core.error_handler.log(e, f"exit_current failed for {type(self.current_app).__name__}")
        self.current_app = None
        if self._app_stack:
            self.current_app = self._app_stack.pop()
            try:
                self.current_app.on_resume()
            except Exception as e:
                core.error_handler.log(e, f"on_resume failed for {type(self.current_app).__name__}")

    def is_active(self):
        return self.current_app is not None and self.current_app.active

    def reset(self):
        if self.current_app:
            try:
                self.current_app.exit_app()
            except Exception:
                pass
            self.current_app = None
        self._app_stack.clear()
