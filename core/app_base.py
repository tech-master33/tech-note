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

    def _vk_to_char(self, vk):
        import ctypes
        import win32api
        import win32con

        # Map special keys manually if needed, but ToUnicode handles most
        if vk == win32con.VK_SPACE: return ' '
        if vk == win32con.VK_RETURN: return None # Handled by on_key
        if vk == win32con.VK_BACK: return None   # Handled by on_key

        # ToUnicode implementation
        state = (ctypes.c_byte * 256)()
        if not ctypes.windll.user32.GetKeyboardState(ctypes.byref(state)):
            return None
        
        buf = ctypes.create_unicode_buffer(5)
        # Get current thread keyboard layout
        hkl = ctypes.windll.user32.GetKeyboardLayout(0)
        
        # Scan code
        sc = win32api.MapVirtualKey(vk, 0)
        
        res = ctypes.windll.user32.ToUnicodeEx(
            vk, sc, ctypes.byref(state), buf, len(buf), 0, hkl
        )
        
        if res > 0:
            return buf.value
        return None

    def exit_app(self):
        """Close the app and return to the main menu."""
        self.manager.reset_temp_params()
        self.active = False
