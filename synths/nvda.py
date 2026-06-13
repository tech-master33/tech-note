import ctypes
import os

IS_32BIT = 0

class Synth:
    def __init__(self):
        self.dll = None
        self.load_dll()

    def load_dll(self):
        dll_path = "nvdaControllerClient.dll"
        if not os.path.exists(dll_path):
            dll_path = os.path.join("bin", "nvdaControllerClient64.dll")

        try:
            self.dll = ctypes.windll.LoadLibrary(dll_path)
            print("NVDA Controller Client loaded successfully.")
        except Exception as e:
            try:
                self.dll = ctypes.windll.LoadLibrary("nvdaControllerClient32.dll")
            except:
                print(f"Error loading NVDA Controller Client: {e}")

    def speak(self, text, interrupt=True):
        if not self.dll:
            return
        try:
            if interrupt:
                self.stop()
            self.dll.nvdaController_speakText(ctypes.c_wchar_p(text))
        except Exception as e:
            print(f"NVDA speech error: {e}")

    def stop(self):
        if self.dll:
            self.dll.nvdaController_cancelSpeech()

    def test(self):
        if not self.dll:
            return False
        return self.dll.nvdaController_testIfRunning() == 0

    def get_rate(self):
        return 0

    def set_rate(self, value):
        pass

    def get_volume(self):
        return 100

    def set_volume(self, value):
        pass

    def get_voice_names(self):
        return ["NVDA"]

    def get_current_voice_name(self):
        return "NVDA"

    def set_voice_by_index(self, index):
        pass

    def get_voice_index(self):
        return 0

    def set_punctuation_level(self, level):
        pass

    def reset_temp_params(self):
        pass

    def set_temp_params(self, rate=None, pitch=None):
        pass
