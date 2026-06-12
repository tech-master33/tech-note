# BrailleNote Start Menu Replacement

A self-voicing, keyboard-driven start menu replacement for Windows, inspired by the BrailleNote mPower/Apex (KeySoft) interface.

## Features
- **Stealth UI**: Completely invisible to NVDA and other screen readers (no "blank" or "pane" sounds).
- **Multi-Synth Support**: 
    - **Keynote Gold**: Direct DLL access (KeySoft's iconic voice).
    - **Eloquence**: Direct DLL access via `eci.dll`.
    - **NVDA**: Speaks through NVDA using the Controller Client.
    - **SAPI5**: Standard Windows voices.
- **64-bit Architecture**: Main app runs in 64-bit Python for performance.
- **32-bit Bridge**: Handles legacy 32-bit synthesis DLLs automatically.
- **First Letter Navigation**: Press the first letter of any menu item to jump to it instantly.
- **Addon System**: Easily add new "Soft Apps" or "Synths".

## Setup Instructions

### 1. Requirements
- **64-bit Python**: For the main application.
- **Dependencies**: `pip install pywin32 comtypes pycryptodome`

### 2. DLLs
Place your legacy DLLs in the `bin/` folder:
- **Eloquence**: `eci.dll` (Legacy/Abandonware - search for community repositories).
- **Keynote Gold**: `b32_tts.dll` (Legacy/Abandonware - often found in "BestSpeech" or NVDA addon folders).
- **NVDA Controller**: `nvdaControllerClient64.dll` (Official - download the [NVDA Controller Client API](https://www.nvaccess.org/files/nvda/releases/) from NV Access).

## Default Synth Logic
At "release time," the application will automatically attempt to use synths in this priority order:
1. **Keynote Gold** (Classic BrailleNote feel)
2. **NVDA** (Communication through your current screen reader)
3. **SAPI5** (Built-in Windows voices)
4. **Eloquence** (Only if none of the above are available)

### 3. Running the App
    `python boot_64.py`

Optional internet apps require: `pip install requests beautifulsoup4`
Optional FM Radio app requires: `pip install pygame`

## Navigation
- **Space / Down Arrow**: Next item.
- **Backspace / Up Arrow**: Previous item.
- **Enter**: Select / Open.
- **Escape**: Go back / Exit menu.
- **A-Z**: First-letter navigation.

## GitHub Setup
1.  Initialize a repository: `git init`
2.  Add files: `git add .`
3.  Commit: `git commit -m "Initial BrailleNote Menu implementation"`
4.  Push to GitHub.
5.  Enable **GitHub Pages** in settings to host your "Soft App Store" JSON (coming soon).

## Plugin System
- **Apps**: Add `.py` files to the `apps/` folder.
- **Synths**: Add `.py` files to the `synths/` folder. Use `IS_32BIT = 1` for legacy DLLs.
