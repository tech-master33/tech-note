import ctypes
import ctypes.wintypes
import win32gui
import win32con
import win32api
import threading
import time

# Constants for Stealth UI
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
LWA_ALPHA = 0x2

class StealthWindow:
    def __init__(self, on_key_down=None):
        self.hwnd = None
        self.on_key_down = on_key_down
        self.space_down = False
        self.running = True
        self.current_text = "Main Menu"
        
        self.thread = threading.Thread(target=self._create_window)
        self.thread.daemon = True
        self.thread.start()
        
        # Wait for hwnd to be created
        for _ in range(10):
            if self.hwnd: break
            time.sleep(0.1)

    def _create_window(self):
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._wnd_proc
        wc.lpszClassName = "BrailleNoteStealthUI"
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.hbrBackground = win32gui.GetStockObject(win32con.BLACK_BRUSH)
        wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        
        try:
            class_atom = win32gui.RegisterClass(wc)
        except:
            class_atom = 0 
            
        ex_style = WS_EX_LAYERED | WS_EX_TOOLWINDOW 
        
        # Center the window
        screen_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        screen_h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        w, h = 800, 600
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2

        self.hwnd = win32gui.CreateWindowEx(
            ex_style,
            wc.lpszClassName,
            " ", # Space title (hide from screen readers)
            win32con.WS_POPUP | win32con.WS_VISIBLE,
            x, y, w, h,
            0, 0, wc.hInstance, None
        )

        win32gui.SetLayeredWindowAttributes(self.hwnd, 0, 255, LWA_ALPHA)
        
        win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 
                             win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

        win32gui.PumpMessages()

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_KEYDOWN:
            if wparam == win32con.VK_SPACE:
                self.space_down = True
            if self.on_key_down:
                self.on_key_down(wparam)
            return 0
        elif msg == win32con.WM_KEYUP:
            if wparam == win32con.VK_SPACE:
                self.space_down = False
            return 0
        elif msg == win32con.WM_PAINT:
            hdc, ps = win32gui.BeginPaint(hwnd)
            rect = win32gui.GetClientRect(hwnd)
            win32gui.FillRect(hdc, rect, win32gui.GetStockObject(win32con.BLACK_BRUSH))
            win32gui.SetTextColor(hdc, win32api.RGB(255, 255, 255))
            win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
            
            font_obj = None
            try:
                import win32ui
                font_obj = win32ui.CreateFont({
                    "name": "Arial",
                    "height": 48,
                    "weight": 700,
                })
                font = font_obj.GetSafeHandle()
            except:
                font = win32gui.GetStockObject(win32con.SYSTEM_FONT)
                
            old_font = win32gui.SelectObject(hdc, font)
            win32gui.DrawText(hdc, self.current_text, -1, rect, 
                             win32con.DT_CENTER | win32con.DT_TOP | win32con.DT_WORDBREAK)
            
            win32gui.SelectObject(hdc, old_font)
            if font_obj:
                font_obj.DeleteObject()
            win32gui.EndPaint(hwnd, ps)
            return 0
        elif msg == win32con.WM_SYSCOMMAND:
            if wparam == win32con.SC_CLOSE:
                return 0
            return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
        elif msg == win32con.WM_CLOSE:
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
        if self.hwnd:
            win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)
