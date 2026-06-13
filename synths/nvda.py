import ctypes
import os

IS_32BIT = 0

class Synth:
    def __init__(self):
        self.dll = None
        self.is_valid = False
        self.load_dll()

    def load_dll(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir) # Assuming synths is directly under project root

        # Prioritize nvdaControllerClient64.dll in the project root
        dll_path_64_root = os.path.join(project_root, "nvdaControllerClient64.dll")
        if os.path.exists(dll_path_64_root):
            try:
                self.dll = ctypes.windll.LoadLibrary(dll_path_64_root)
                print("NVDA Controller Client 64-bit loaded successfully from project root.")
                self.is_valid = True
                return
            except Exception as e:
                print(f"Error loading NVDA Controller Client 64-bit from project root: {e}")

        # Fallback to nvdaControllerClient.dll in the project root
        dll_path_default_root = os.path.join(project_root, "nvdaControllerClient.dll")
        if os.path.exists(dll_path_default_root):
            try:
                self.dll = ctypes.windll.LoadLibrary(dll_path_default_root)
                print("NVDA Controller Client default loaded successfully from project root.")
                self.is_valid = True
                return
            except Exception as e:
                print(f"Error loading NVDA Controller Client default from project root: {e}")

        # Fallback to bin/nvdaControllerClient64.dll relative to project root
        dll_path_bin_64 = os.path.join(project_root, "bin", "nvdaControllerClient64.dll")
        if os.path.exists(dll_path_bin_64):
            try:
                self.dll = ctypes.windll.LoadLibrary(dll_path_bin_64)
                print("NVDA Controller Client 64-bit loaded successfully from bin relative to root.")
                self.is_valid = True
                return
            except Exception as e:
                print(f"Error loading NVDA Controller Client 64-bit from bin relative to root: {e}")

        # Final fallback to 32-bit in the project root
        dll_path_32_root = os.path.join(project_root, "nvdaControllerClient32.dll")
        if os.path.exists(dll_path_32_root):
            try:
                self.dll = ctypes.windll.LoadLibrary(dll_path_32_root)
                print("NVDA Controller Client 32-bit loaded successfully from project root (fallback).")
                self.is_valid = True
                return
            except Exception as e:
                print(f"Error loading NVDA Controller Client 32-bit from project root (fallback): {e}")

        # Fallback to system PATH for 32-bit
        try:
            self.dll = ctypes.windll.LoadLibrary("nvdaControllerClient32.dll")
            print("NVDA Controller Client 32-bit loaded successfully from system PATH (fallback).")
            self.is_valid = True
            return
        except Exception as e:
            print(f"Error loading NVDA Controller Client 32-bit from system PATH (fallback): {e}")

        print("NVDA Controller Client DLL not found or could not be loaded.")

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

    def get_pitch(self):
        return 50

    def set_pitch(self, value):
        pass

    def get_capital_pitch_change(self):
        return "Off"

    def set_capital_pitch_change(self, value):
        pass

    def get_volume_ducking(self):
        return False

    def set_volume_ducking(self, enabled):
        pass

    def reset_temp_params(self):
        pass

    def set_temp_params(self, rate=None, pitch=None):
        pass
