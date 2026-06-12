import ctypes
import os

IS_32BIT = 1

class Synth:
    def __init__(self):
        self.dll = None
        self.handle = None
        self.load_dll()

    def load_dll(self):
        # Look for eci.dll in the current directory or bin/
        dll_path = "eci.dll"
        if not os.path.exists(dll_path):
            dll_path = os.path.join("bin", "eci.dll")
        
        try:
            # Eloquence is usually a stdcall DLL (windll)
            self.dll = ctypes.windll.LoadLibrary(dll_path)
            
            # Define function signatures
            self.dll.eciNew.restype = ctypes.c_void_p
            self.dll.eciAddText.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
            self.dll.eciSpeakText.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
            self.dll.eciDelete.argtypes = [ctypes.c_void_p]
            self.dll.eciStop.argtypes = [ctypes.c_void_p]
            self.dll.eciPause.argtypes = [ctypes.c_void_p, ctypes.c_int]
            
            self.handle = self.dll.eciNew()
            print("Eloquence DLL loaded successfully.")
        except Exception as e:
            print(f"Error loading Eloquence DLL: {e}")

    def speak(self, text, interrupt=True):
        if not self.handle:
            return
        
        if interrupt:
            self.stop()
            
        # Eloquence usually expects Windows-1252 (cp1252)
        try:
            encoded_text = text.encode('cp1252', errors='replace')
            self.dll.eciAddText(self.handle, encoded_text)
            self.dll.eciSynthesize(self.handle)
        except Exception as e:
            print(f"Eloquence speech error: {e}")

    def stop(self):
        if self.handle:
            self.dll.eciStop(self.handle)

    def pause(self):
        if self.handle:
            self.dll.eciPause(self.handle, 1)

    def resume(self):
        if self.handle:
            self.dll.eciPause(self.handle, 0)

    def __del__(self):
        if self.handle and self.dll:
            self.dll.eciDelete(self.handle)
