# Tech-Note

A self-voicing, keyboard-driven interface for Windows, inspired by the BrailleNote mPower/Apex (KeySoft).

## Features
- **Self-voicing**: Built-in SAPI5 speech, no screen reader required
- **Stealth UI**: Invisible to screen readers (no "blank" or "pane" sounds)
- **Keyboard-driven**: All navigation via keyboard, no mouse needed
- **Apps**: Word processor, calculator, file manager, email, internet, media player, planner, address book, FM radio
- **First Letter Navigation**: Press the first letter of any menu item to jump to it

## Requirements
- **64-bit Python 3.10+**
- **Dependencies**: `pip install -r requirements.txt`

## Running
    python boot_64.py

## Navigation
- **Space / Down Arrow**: Next item
- **Backspace / Up Arrow**: Previous item
- **Enter**: Select / Open
- **Escape**: Go back / Exit app
- **Space + O**: Options menu (speech rate, volume, voice)
- **Backtick (`)**: Power menu (restart, shutdown)
- **A-Z**: First-letter navigation in menus
