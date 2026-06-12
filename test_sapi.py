import win32com.client
import pythoncom
import sys

def test_sapi():
    try:
        pythoncom.CoInitialize()
        print("CoInitialize successful.")
        
        # Try to dispatch SAPI.SpVoice directly
        voice = win32com.client.Dispatch("SAPI.SpVoice")
        print("Dispatch successful.")
        
        # Check if it has the Speak method
        if hasattr(voice, "Speak"):
            print("Speak method found.")
            # Try a very basic speak
            voice.Speak("Testing COM speech", 1)
            print("Speak call successful.")
        else:
            print("Speak method NOT found.")
            
    except Exception as e:
        print(f"Error: {e}")
        # Print detailed COM info
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sapi()
