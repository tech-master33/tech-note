# Tech-Note

A self-voicing, keyboard-driven interface for Windows, modeled after the BrailleNote mPower/Apex (KeySoft) series. No screen reader required.

## Features
- **Self-voicing**: Built-in SAPI5 speech, no screen reader needed
- **Stealth UI**: Invisible to screen readers to avoid noise
- **Keyboard-driven**: Full control via keyboard, no mouse
- **Sound schemes**: Classic, Minimal, Default
- **App Store**: Download and install community apps
- **Chat**: Internet messaging with rooms, DMs, and voice messages

## Built-in Apps
- **Productivity**: Word Processor, Calculator, File Manager, Planner, Address List, Email, Notes
- **Communication**: Chat (messaging), Internet Browser, OpenCode AI Client, ChatGPT Client
- **Utilities**: Settings, Tutorial, Habit Tracker
- **Media**: Media Player, FM Radio
- **Games**: Game Center (with multiple games)
- **System**: App Store, Power Menu, Lock Screen, Options Menu

## Navigation
- **Space**: Next item
- **Backspace**: Previous item
- **Enter**: Select / Open
- **Escape**: Go back / Exit
- **First letter (A-Z)**: Jump to item
- **Space + O**: Options menu
- **Backtick (`)**: Power Menu
- **F1**: Help
- **F5**: Status info
- **Shift + F1**: Tutorial
- **Alt+F4**: Blocked (use Power Menu to exit)

## Requirements
- **64-bit Python 3.10+**
- `pip install -r requirements.txt`

## Running
```bash
python boot_64.py
```
