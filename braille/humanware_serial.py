import serial
import threading
import time

class TouchPlusDisplay:
    def __init__(self, port, cells=32):
        self.port = port
        self.cells = cells
        self.ser = None
        self._lock = threading.Lock()
        self._connect()

    def _connect(self):
        try:
            self.ser = serial.Serial(self.port, baudrate=9600, timeout=1, write_timeout=1)
        except Exception:
            self.ser = None

    def is_connected(self):
        return self.ser is not None and self.ser.is_open

    def display_text(self, text):
        if not self.is_connected():
            return
        line = text[:self.cells].ljust(self.cells)
        cmd = f"\r{line}\r"
        with self._lock:
            try:
                self.ser.write(cmd.encode())
            except Exception:
                pass

    def display_with_cursor(self, text, cursor_pos):
        if not self.is_connected():
            return
        line = text[:self.cells].ljust(self.cells)
        cmd = f"\r{cursor_pos}:{line}\r"
        with self._lock:
            try:
                self.ser.write(cmd.encode())
            except Exception:
                pass

    def close(self):
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
