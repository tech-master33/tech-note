import json
import os
import tempfile
import win32con
import core.error_handler


class SoftApp:
    def __init__(self, manager, window, app_type='app'):
        self.manager = manager
        self.window = window
        self.speak = manager.speak
        self.stop = manager.stop
        self.active = True
        self.app_type = app_type
        self.input_mode = None
        self.input_buf = ""
        self.input_prompt = ""
        self.input_callback = None

    def on_key(self, vk):
        pass

    def on_key_up(self, vk):
        pass

    def on_focus(self):
        pass

    def on_pause(self):
        pass

    def on_resume(self):
        pass

    def on_destroy(self):
        pass

    def get_help_text(self):
        return "No help available for this application."

    def get_state(self):
        return None

    def set_state(self, state):
        pass

    def exit_app(self):
        self.manager.reset_temp_params()
        self.active = False

    def _announce(self, text, speak=True):
        self.window.update_text(text)
        if speak:
            self.speak(text)

    def _handle_menu_key(self, vk, menu):
        if vk == win32con.VK_UP or vk == win32con.VK_LEFT:
            if menu.previous():
                item = menu.get_current_item()
                self._announce(item.title if item else "")
        elif vk == win32con.VK_DOWN or vk == win32con.VK_RIGHT:
            if menu.next():
                item = menu.get_current_item()
                self._announce(item.title if item else "")
        elif vk == win32con.VK_ESCAPE:
            self.exit_app()
        elif vk == win32con.VK_BACK:
            if menu.previous():
                item = menu.get_current_item()
                self._announce(item.title if item else "")

    def _handle_first_letter_nav(self, vk, menu):
        if 0x41 <= vk <= 0x5A:
            menu.first_letter_nav(chr(vk))
            item = menu.get_current_item()
            if item:
                self._announce(item.title)

    def _handle_text_input(self, vk):
        if not self.input_mode:
            return False
        if vk == win32con.VK_ESCAPE:
            self._cancel_text_input()
        elif vk == win32con.VK_RETURN:
            self._submit_text_input()
        elif vk == win32con.VK_BACK:
            self.input_buf = self.input_buf[:-1]
            text = f"{self.input_prompt}{self.input_buf}"
            self.window.update_text(text)
        else:
            ch = self._vk_to_char(vk)
            if ch and ord(ch) >= 32:
                self.input_buf += ch
                text = f"{self.input_prompt}{self.input_buf}"
                self.window.update_text(text)
        return True

    def _start_text_input(self, prompt, callback, initial=""):
        self.input_mode = True
        self.input_buf = initial
        self.input_prompt = prompt
        self.input_callback = callback
        self._announce(prompt + initial)

    def _cancel_text_input(self):
        self.input_mode = False
        self.input_buf = ""
        self.input_prompt = ""
        self.input_callback = None

    def _submit_text_input(self):
        cb = self.input_callback
        data = self.input_buf
        self.input_mode = False
        self.input_buf = ""
        self.input_prompt = ""
        self.input_callback = None
        if cb:
            cb(data)

    def _load_json(self, path, default=None):
        if not os.path.exists(path):
            return default
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return default

    def _save_json(self, path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8',
            dir=os.path.dirname(path), suffix='.tmp', delete=False
        )
        try:
            json.dump(data, tmp, indent=2)
            tmp.close()
            os.replace(tmp.name, path)
        except Exception:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass
            raise

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
        return bool(self.input_mode)


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
            self.current_app.on_destroy()
        except Exception as e:
            core.error_handler.log(e, f"on_destroy failed for {type(self.current_app).__name__}")
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
                self.current_app.on_destroy()
            except Exception:
                pass
            try:
                self.current_app.exit_app()
            except Exception:
                pass
            self.current_app = None
        self._app_stack.clear()
