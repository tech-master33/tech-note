import ctypes
import os

IS_32BIT = 0

class Synth:
    def __init__(self):
        self.dll = None
        self.load_dll()

    def load_dll(self):
        # Look for nvdaControllerClient.dll
        # Usually we use the bitness-appropriate one. 
        # Since this is for the 64-bit main app, we look for the 64-bit DLL.
        dll_path = "nvdaControllerClient.dll"
        if not os.path.exists(dll_path):
            dll_path = os.path.join("bin", "nvdaControllerClient64.dll")
        
        try:
            self.dll = ctypes.windll.LoadLibrary(dll_path)
            print("NVDA Controller Client loaded successfully.")
        except Exception as e:
            # Try 32-bit as fallback if we are somehow in a 32-bit process
            try:
                self.dll = ctypes.windll.LoadLibrary("nvdaControllerClient32.dll")
            except:
                print(f"Error loading NVDA Controller Client: {e}")

    def speak(self, text, interrupt=True):
        if not self.dll:
            return
            
        try:
            # nvdaController_speakText(const wchar_t* text)
            if interrupt:
                self.stop()
            self.dll.nvdaController_speakText(ctypes.c_wchar_p(text))
        except Exception as e:
            print(f"NVDA speech error: {e}")

    def stop(self):
        if self.dll:
            self.dll.nvdaController_cancelSpeech()

    def test(self):
        if not self.dll: return False
        return self.dll.nvdaController_testIfRunning() == 0
