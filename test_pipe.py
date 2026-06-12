import win32file
import win32con
import time

pipe_path = r'\\.\pipe\BrailleNoteBridge'
try:
    print("Attempting to connect to pipe...")
    handle = win32file.CreateFile(
        pipe_path,
        win32con.GENERIC_WRITE,
        0, None,
        win32con.OPEN_EXISTING,
        0, None
    )
    print("Connected!")
    win32file.WriteFile(handle, b"SPEAK:keynote:Test\n")
    print("Sent.")
except Exception as e:
    print(f"Error: {e}")
