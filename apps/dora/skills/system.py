import os
import subprocess

def shutdown_computer(assistant, command):
    assistant.speak("Shutting down in 10 seconds.")
    os.system("shutdown /s /t 10")

def restart_computer(assistant, command):
    assistant.speak("Restarting in 10 seconds.")
    os.system("shutdown /r /t 10")

def cancel_shutdown(assistant, command):
    assistant.speak("Shutdown cancelled.")
    os.system("shutdown /a")

def get_battery_status(assistant, command=None):
    try:
        import psutil
        battery = psutil.sensors_battery()
        if battery is None:
            assistant.speak("No battery found on this system.")
            return
        percent = battery.percent
        status = "charging" if battery.power_plugged else "on battery"
        if percent == 100 and battery.power_plugged:
            status = "fully charged"
        assistant.speak(f"Battery at {percent} percent, {status}.")
    except Exception as e:
        assistant.speak("Could not check battery status.")

def open_application(assistant, command):
    app_map = {
        'chrome': 'chrome.exe',
        'firefox': 'firefox.exe',
        'notepad': 'notepad.exe',
        'calculator': 'calc.exe',
        'edge': 'msedge.exe',
        'vlc': 'vlc.exe',
    }
    clean = command.lower().replace('open', '').replace('start', '').replace('launch', '').strip()
    if clean in app_map:
        assistant.speak(f"Opening {clean}.")
        subprocess.Popen(app_map[clean], shell=True)
    else:
        assistant.speak(f"Attempting to open {clean}.")
        subprocess.Popen(f'start "" "{clean}"', shell=True)
