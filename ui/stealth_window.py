import ctypes
import ctypes.wintypes
import win32gui
import win32con
import win32api
import threading
import time
import pythoncom

# Constants for Stealth UI
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
LWA_ALPHA = 0x2

class StealthWindow:
    def __init__(self, on_key_down=None, on_key_up=None):
        self.hwnd = None
        self.on_key_down = on_key_down
        self.on_key_up = on_key_up
        self.space_down = False
        self.running = True
        self.current_text = "Main Menu"
        
        # UI Settings
        self.bg_color = win32api.RGB(0, 0, 0) # Default Black
        self.font_height = 48
        self.font_weight = 700
        self.block_close = False
        
        self.thread = threading.Thread(target=self._create_window)
        self.thread.daemon = True
        self.thread.start()
        
        # Wait for hwnd to be created
        for i in range(50):
            if self.hwnd: break
            time.sleep(0.1)
        if not self.hwnd:
            print("StealthWindow: ERROR: Window hwnd not created after 5 seconds")

    def set_display_settings(self, bg_color=None, font_size=None):
        if bg_color is not None:
            # bg_color should be (R, G, B) tuple
            self.bg_color = win32api.RGB(*bg_color)
        if font_size is not None:
            sizes = {"Small": 24, "Medium": 48, "Large": 72}
            self.font_height = sizes.get(font_size, 48)
        if self.hwnd:
            win32gui.InvalidateRect(self.hwnd, None, True)

    def _create_window(self):
        print("StealthWindow: _create_window started")
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._wnd_proc
        wc.lpszClassName = "BrailleNoteStealthUI"
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.hbrBackground = win32gui.GetStockObject(win32con.BLACK_BRUSH)
        wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        
        try:
            class_atom = win32gui.RegisterClass(wc)
            print("StealthWindow: RegisterClass succeeded")
        except Exception as e:
            print(f"StealthWindow: RegisterClass (may already be registered): {e}")
            
        ex_style = WS_EX_LAYERED | win32con.WS_EX_APPWINDOW
        
        # Center the window
        screen_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        screen_h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        w, h = 800, 600
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2

        self.hwnd = win32gui.CreateWindowEx(
            ex_style,
            wc.lpszClassName,
            "Tech-Note",
            win32con.WS_POPUP | win32con.WS_VISIBLE,
            x, y, w, h,
            0, 0, wc.hInstance, None
        )
        print(f"StealthWindow: CreateWindowEx returned {self.hwnd}")
        
        if self.hwnd:
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
            win32gui.UpdateWindow(self.hwnd)
            win32gui.SetLayeredWindowAttributes(self.hwnd, 0, 255, LWA_ALPHA)
            win32gui.SetWindowPos(self.hwnd, -1, 0, 0, 0, 0, 
                                 win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            try:
                # Common trick: send ALT to allow SetForegroundWindow
                win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
                win32gui.SetForegroundWindow(self.hwnd)
                win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
                print("StealthWindow: SetForegroundWindow succeeded")
            except Exception as e:
                print(f"StealthWindow: SetForegroundWindow failed: {e}")
        else:
            print("StealthWindow: ERROR: CreateWindowEx failed to return a valid hwnd")
            return

        pythoncom.CoInitialize()
        win32gui.PumpMessages()

    def show(self):
        if self.hwnd:
            print(f"StealthWindow: Explicitly showing window {self.hwnd}")
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
            win32gui.UpdateWindow(self.hwnd)
        else:
            print("StealthWindow: ERROR: show() called but hwnd is None")

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_KEYDOWN:
            if wparam == win32con.VK_SPACE:
                self.space_down = True
            if self.on_key_down:
                try:
                    self.on_key_down(wparam)
                except Exception as e:
                    print(f"StealthWindow: on_key_down error: {e}")
            return 0
        elif msg == win32con.WM_KEYUP:
            if wparam == win32con.VK_SPACE:
                self.space_down = False
            if self.on_key_up:
                try:
                    self.on_key_up(wparam)
                except Exception as e:
                    print(f"StealthWindow: on_key_up error: {e}")
            return 0
        elif msg == win32con.WM_PAINT:
            hdc, ps = win32gui.BeginPaint(hwnd)
            rect = win32gui.GetClientRect(hwnd)
            
            # Create a solid brush for the background color
            brush = win32gui.CreateSolidBrush(self.bg_color)
            win32gui.FillRect(hdc, rect, brush)
            win32gui.DeleteObject(brush)
            
            win32gui.SetTextColor(hdc, win32api.RGB(255, 255, 255))
            win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
            
            font_obj = None
            try:
                import win32ui
                font_obj = win32ui.CreateFont({
                    "name": "Arial",
                    "height": self.font_height,
                    "weight": self.font_weight,
                })
                font = font_obj.GetSafeHandle()
            except:
                font = win32gui.GetStockObject(win32con.SYSTEM_FONT)
                
            old_font = win32gui.SelectObject(hdc, font)
            win32gui.DrawText(hdc, self.current_text, -1, rect, 
                             win32con.DT_CENTER | win32con.DT_TOP | win32con.DT_WORDBREAK)
            
            win32gui.SelectObject(hdc, old_font)
            win32gui.EndPaint(hwnd, ps)
            return 0
        elif msg == win32con.WM_SYSCOMMAND:
            if wparam & 0xFFF0 == win32con.SC_CLOSE:
                if self.block_close:
                    return 0
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                return 0
            return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
        elif msg == win32con.WM_CLOSE:
            if self.block_close:
                return 0
            win32gui.DestroyWindow(hwnd)
            return 0
        elif msg == 0x003D:  # WM_GETOBJECT
            return 0
        elif msg == win32con.WM_ACTIVATE:
            if wparam == win32con.WA_INACTIVE:
                # When inactive, allow other windows to be on top.
                # Crucial for Alt+Tab switcher to be visible.
                win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                                     win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
            else:
                # When active, stay on top
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                     win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            return 0
        elif msg == win32con.WM_DESTROY:
            self.running = False
            ctypes.windll.user32.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def update_text(self, text):
        self.current_text = text
        if self.hwnd:
            win32gui.InvalidateRect(self.hwnd, None, True)

    def close(self):
        self.running = False
        if self.hwnd and win32gui.IsWindow(self.hwnd):
            try:
                for alpha in range(255, 0, -15):
                    win32gui.SetLayeredWindowAttributes(self.hwnd, 0, max(alpha, 0), LWA_ALPHA)
                    time.sleep(0.02)
            except:
                pass
            win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)
