import ctypes
import os

IS_32BIT = 1

class Synth:
    def __init__(self):
        self.dll = None
        self.state = None
        self.load_dll()

    def load_dll(self):
        # Look for b32_tts.dll in bin/ or current dir
        dll_path = "b32_tts.dll"
        if not os.path.exists(dll_path):
            dll_path = os.path.join("bin", "b32_tts.dll")
        
        try:
            # Keynote Gold / BestSpeech is usually cdecl or stdcall
            # We'll try windll first, then cdll if needed
            self.dll = ctypes.windll.LoadLibrary(dll_path)
            
            # Keynote API often requires initialization with a path to resources
            # bst_init(const char* module_path)
            if hasattr(self.dll, "bst_init"):
                self.dll.bst_init.restype = ctypes.c_void_p
                self.dll.bst_init.argtypes = [ctypes.c_char_p]
                
                module_path = os.path.dirname(os.path.abspath(dll_path))
                self.state = self.dll.bst_init(module_path.encode('utf-8'))
                
            print("Keynote Gold DLL loaded successfully.")
        except Exception as e:
            print(f"Error loading Keynote Gold DLL: {e}")

    def speak(self, text, interrupt=True):
        if not self.dll:
            return
            
        try:
            # Signature: bst_speak(state, size, text, voice, rate, gain, pcm_header)
            # Or bst_speak_text(text) depending on the specific wrapper
            if hasattr(self.dll, "bst_speak_text"):
                self.dll.bst_speak_text(text.encode('utf-8'))
            elif hasattr(self.dll, "bst_speak"):
                # Simplified call if the state is handled internally or passed
                # This is a placeholder for the actual complex call if needed
                self.dll.bst_speak(self.state, None, text.encode('utf-8'), 0, 0, 0, False)
        except Exception as e:
            print(f"Keynote speech error: {e}")

    def stop(self):
        if self.dll and hasattr(self.dll, "bst_stop"):
            self.dll.bst_stop()

    def __del__(self):
        if self.state and self.dll and hasattr(self.dll, "bst_free"):
            self.dll.bst_free(self.state)
