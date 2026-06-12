import os
import time

pipe_path = r'\\.\pipe\BrailleNoteBridge'

def send(msg):
    try:
        with open(pipe_path, 'w') as f:
            f.write(msg + "\n")
        print(f"Sent: {msg}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    send("SET:keynote")
    time.sleep(1)
    send("SPEAK:Test speech from bridge")
    time.sleep(1)
    send("SET:eloquence")
    time.sleep(1)
    send("SPEAK:Testing Eloquence")
