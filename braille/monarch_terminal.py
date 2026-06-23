import serial
import threading
import time

class MonarchDisplay:
    def __init__(self, port, rows=10, cols=32):
        self.port = port
        self.rows = rows
        self.cols = cols
        self.ser = None
        self._lock = threading.Lock()
        self._buffer = [""] * rows
        self._connect()

    def _connect(self):
        try:
            self.ser = serial.Serial(self.port, baudrate=115200, timeout=1, write_timeout=1)
        except Exception:
            self.ser = None

    def is_connected(self):
        return self.ser is not None and self.ser.is_open

    def display_text(self, text):
        lines = self._split_lines(text)
        self._buffer = lines
        cmd = self._format_lines(lines)
        with self._lock:
            try:
                self.ser.write(cmd.encode())
            except Exception:
                pass

    def display_with_cursor(self, text, cursor_pos, line=0):
        lines = self._split_lines(text)
        self._buffer = lines
        marked = list(lines)
        if 0 <= line < len(marked):
            pos = min(cursor_pos, len(marked[line]))
            marked[line] = marked[line][:pos] + "\x07" + marked[line][pos:]
        cmd = self._format_lines(marked)
        with self._lock:
            try:
                self.ser.write(cmd.encode())
            except Exception:
                pass

    def _split_lines(self, text):
        lines = text.split("\n")
        result = []
        for line in lines:
            while len(line) > self.cols:
                result.append(line[:self.cols])
                line = line[self.cols:]
            result.append(line)
        while len(result) < self.rows:
            result.append("")
        return result[:self.rows]

    def _format_lines(self, lines):
        return "\r".join(l.ljust(self.cols) for l in lines) + "\r"

    def close(self):
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
