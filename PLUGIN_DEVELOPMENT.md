# Plugin Development Guide

Tech-Note plugins (`.scrugn` files) let you add speech synthesizers, braille displays, and text filters. This guide covers everything you need to create, package, and distribute plugins.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Plugin Types](#2-plugin-types)
3. [Manifest Format](#3-manifest-format)
4. [Synth Plugin Tutorial](#4-synth-plugin-tutorial)
5. [Braille Plugin Tutorial](#5-braille-plugin-tutorial)
6. [Filter Plugin Tutorial](#6-filter-plugin-tutorial)
7. [Complete Interface Reference](#7-complete-interface-reference)
8. [Adding Terminal Commands](#8-adding-terminal-commands)
9. [Packaging and Distribution](#9-packaging-and-distribution)
10. [Best Practices](#10-best-practices)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Overview

A plugin is a `.scrugn` file (a ZIP archive containing your code and resources) placed in `~/.tech-soft/plugins/`. The Plugin Manager scans this directory on startup, extracts each archive to a temporary location, and loads the entry point module.

### How Plugin Loading Works

1. Plugin Manager scans `~/.tech-soft/plugins/` for `*.scrugn` files
2. Opens the archive and reads `manifest.json`
3. Extracts to a temporary directory
4. Imports the entry point module (default: `__init__.py`)
5. Finds any class that inherits from the appropriate base class (`SynthPlugin`, `BrailleDisplayPlugin`, or `FilterPlugin`)
6. Instantiates the class and calls `initialize()`
7. Registers the plugin for use by the application
8. Any commands returned by `get_commands()` are registered with the Command Registry

### File Structure

```
my_plugin.scrugn
├── manifest.json          # Required: plugin metadata
├── __init__.py            # Entry point (or configured in manifest)
├── bin/                   # Optional: bundled binaries
│   ├── my_dll.dll
│   └── my_data.dat
└── ...                    # Any additional Python modules
```

---

## 2. Plugin Types

| Type | Base Class | Purpose |
|------|-----------|---------|
| `synth` | `SynthPlugin` | Text-to-speech engine |
| `braille` | `BrailleDisplayPlugin` | Braille display driver |
| `filter` | `FilterPlugin` | Text transformation filter |

---

## 3. Manifest Format

The `manifest.json` file is required at the root of the `.scrugn` archive.

### Full Schema

```json
{
    "id": "my_plugin",
    "name": "My Plugin",
    "version": "1.0.0",
    "plugin_type": "synth",
    "entry": "__init__.py",
    "description": "A brief description of what this plugin does.",
    "author": "Your Name"
}
```

### Fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `id` | No | — | Internal identifier (currently unused) |
| `name` | No | Filename | Display name shown in the Plugin Manager |
| `version` | No | `"1.0"` | Version string (shown in Plugin Manager) |
| `plugin_type` | **Yes** | — | One of: `"synth"`, `"braille"`, `"filter"` |
| `entry` | **Yes** | `"__init__.py"` | Entry point file relative to archive root |
| `description` | No | `""` | Human-readable description |
| `author` | No | `"Unknown"` | Author name |

---

## 4. Synth Plugin Tutorial

This section walks through creating a minimal speech synthesizer plugin.

### Step 1: Create the project directory

```
my_synth/
├── manifest.json
└── __init__.py
```

### Step 2: Write manifest.json

```json
{
    "name": "My Synth",
    "version": "1.0.0",
    "plugin_type": "synth",
    "entry": "__init__.py",
    "description": "A minimal speech synthesizer",
    "author": "Your Name"
}
```

### Step 3: Write the plugin code

```python
from core.plugin_base import SynthPlugin


class MySynth(SynthPlugin):
    plugin_name = "My Synth"
    plugin_version = "1.0.0"

    def initialize(self):
        # Set up your synthesizer here (load DLLs, connect to services, etc.)
        return True

    def shutdown(self):
        # Clean up resources
        pass

    def speak(self, text, interrupt=True):
        # Speak the given text.
        # If interrupt is True, stop current speech first.
        if interrupt:
            self.stop()
        # Send text to your TTS engine
        print(f"Speaking: {text}")

    def stop(self):
        # Immediately stop any current speech
        pass

    def get_rate(self):
        return 0

    def set_rate(self, value):
        pass

    def get_volume(self):
        return 100

    def set_volume(self, value):
        pass

    def get_pitch(self):
        return 50

    def set_pitch(self, value):
        pass

    def get_voice_names(self):
        return ["Default"]

    def set_voice(self, name):
        pass

    def get_current_voice_name(self):
        return "Default"

    def get_voice_index(self):
        return 0

    def set_voice_by_index(self, index):
        pass

    def set_punctuation_level(self, level):
        pass

    def get_punctuation_level(self):
        return "Some"

    def set_capital_pitch_change(self, value):
        pass

    def get_capital_pitch_change(self):
        return "Off"

    def set_volume_ducking(self, enabled):
        pass

    def get_volume_ducking(self):
        return False

    def save_defaults(self):
        pass

    def reset_temp_params(self):
        pass

    def set_temp_params(self, rate=None, pitch=None, voice_index=None):
        pass

    def apply_profile(self, voice_index=None, rate=None, pitch=None):
        pass

    def repeat_last(self):
        pass

    def wait_until_done(self, timeout_ms=5000):
        pass

    def get_speech_history(self):
        return []

    def get_history_max(self):
        return 50

    def set_history_max(self, value):
        pass
```

### Step 4: Package and install

```bash
python tools/pack_scrugn.py pack my_synth/
# Creates My Synth.scrugn in the current directory
```

Copy the `.scrugn` file to `~/.tech-soft/plugins/` or use the Plugin Manager's "Install plugin" option.

### Real-world Example

For a complete example, examine the DECtalk synthesizer plugin at `dectalk-scrugn/__init__.py`. It demonstrates:
- Loading a DLL via ctypes
- Configuring function argument types
- Handling the `speak()`/`stop()` lifecycle correctly (calling `self.stop()` when `interrupt=True`)
- Implementing voice switching via `TextToSpeechSetSpeaker`
- Rate and volume control

---

## 5. Braille Plugin Tutorial

```python
from core.plugin_base import BrailleDisplayPlugin


class MyBraille(BrailleDisplayPlugin):
    plugin_name = "My Braille Display"
    plugin_version = "1.0.0"

    def initialize(self):
        # Connect to the braille display hardware
        return True

    def shutdown(self):
        # Disconnect and clean up
        pass

    def write(self, text):
        # Send text to the braille display
        # Text is already translated to braille by the braille manager
        pass

    def read_input(self):
        # Read input from the display's input buttons/routing keys
        # Return the input or None if no input available
        return None
```

---

## 6. Filter Plugin Tutorial

```python
from core.plugin_base import FilterPlugin


class MyFilter(FilterPlugin):
    plugin_name = "My Filter"
    plugin_version = "1.0.0"

    def initialize(self):
        return True

    def shutdown(self):
        pass

    def process(self, text):
        # Modify the text before it is spoken
        # Return the modified text
        return text.upper()  # Example: speak everything in uppercase
```

---

## 7. Complete Interface Reference

### ScrugnPlugin (base for all plugins)

| Method | Required | Signature | Description |
|--------|----------|-----------|-------------|
| `initialize()` | **Yes** | `(self) -> bool` | Set up plugin resources. Return `True` on success. |
| `shutdown()` | **Yes** | `(self)` | Clean up resources. Called during app shutdown. |
| `get_commands()` | No | `(self) -> list` | Return a list of `(name, help_text, handler)` tuples for Terminal commands (see section 8). |

Class attributes: `plugin_type`, `plugin_name`, `plugin_version`

### SynthPlugin — Required Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `speak()` | `(self, text, interrupt=True)` | Speak `text`. If `interrupt` is `True`, stop current speech first. |
| `stop()` | `(self)` | Immediately stop all speech output. |

### SynthPlugin — Optional Methods (with defaults)

All of these have default implementations in the base class that return safe defaults or do nothing. Override them to provide full functionality.

| Method | Default | Description |
|--------|---------|-------------|
| `get_rate()` | returns `0` | Get current speech rate |
| `set_rate(value)` | no-op | Set speech rate |
| `get_volume()` | returns `100` | Get current volume |
| `set_volume(value)` | no-op | Set volume (0-100) |
| `get_pitch()` | returns `50` | Get current pitch |
| `set_pitch(value)` | no-op | Set pitch (0-100) |
| `get_voice_names()` | returns `[]` | Get list of available voice names |
| `set_voice(name)` | no-op | Switch to a voice by name |
| `get_current_voice_name()` | returns `""` | Get name of currently selected voice |
| `get_voice_index()` | returns `0` | Get index of current voice |
| `set_voice_by_index(index)` | no-op | Switch to a voice by index |
| `set_punctuation_level(level)` | no-op | Set punctuation level ("None", "Some", "Most", "All") |
| `get_punctuation_level()` | returns `"Some"` | Get current punctuation level |
| `set_capital_pitch_change(value)` | no-op | Set capital pitch behavior ("Off", "Say Cap", "Raise Pitch") |
| `get_capital_pitch_change()` | returns `"Off"` | Get current capital pitch setting |
| `set_volume_ducking(enabled)` | no-op | Enable/disable audio ducking |
| `get_volume_ducking()` | returns `False` | Check if ducking is enabled |
| `save_defaults()` | no-op | Save current settings as defaults |
| `reset_temp_params()` | no-op | Restore saved defaults |
| `set_temp_params(rate, pitch, voice_index)` | no-op | Temporarily override settings |
| `apply_profile(voice_index, rate, pitch)` | no-op | Apply a voice profile |
| `repeat_last()` | no-op | Repeat the last spoken text |
| `wait_until_done(timeout_ms)` | no-op | Wait for speech to finish (or timeout) |
| `get_speech_history()` | returns `[]` | Get list of recently spoken texts |
| `get_history_max()` | returns `50` | Get max history size |
| `set_history_max(value)` | no-op | Set max history size |

### BrailleDisplayPlugin

| Method | Required | Signature | Description |
|--------|----------|-----------|-------------|
| `write(text)` | **Yes** | `(self, text)` | Send pre-translated braille to the display |
| `read_input()` | **Yes** | `(self)` | Read input from the display (return input or `None`) |
| `initialize()` | **Yes** | `(self) -> bool` | Connect to the display hardware |
| `shutdown()` | **Yes** | `(self)` | Disconnect and clean up |

### FilterPlugin

| Method | Required | Signature | Description |
|--------|----------|-----------|-------------|
| `process(text)` | **Yes** | `(self, text) -> str` | Transform the input text and return the result |
| `initialize()` | **Yes** | `(self) -> bool` | Set up filter resources |
| `shutdown()` | **Yes** | `(self)` | Clean up resources |

---

## 8. Adding Terminal Commands

Plugins can expose commands to the Terminal app. Override `get_commands()` in your plugin class to return a list of command definitions.

### Method Signature

```python
def get_commands(self):
    return [
        ("command_name", "Help text for this command", self._handler_method),
    ]
```

Each tuple contains:
- **Name**: The command name (users type this in the Terminal)
- **Help text**: Shown when the user runs the `help` command
- **Handler**: A callable that takes a single string argument and returns a result string

Commands are registered with the prefix `PluginName:command_name` to avoid naming conflicts. For example, a plugin named "My Synth" with a command "status" would be invoked as `My Synth:status`.

### Example: Adding Commands to a Synth Plugin

```python
from core.plugin_base import SynthPlugin


class MySynth(SynthPlugin):
    # ... other methods ...

    def get_commands(self):
        return [
            ("status", "Show synthesizer status", self._cmd_status),
            ("diagnose", "Run diagnostics", self._cmd_diagnose),
        ]

    def _cmd_status(self, arg):
        # arg is the text after the command name (empty if none)
        return f"My Synth v{self.plugin_version}, rate={self.get_rate()}, vol={self.get_volume()}"

    def _cmd_diagnose(self, arg):
        # Run diagnostics and return result
        return "Diagnostics: OK"
```

---

## 9. Packaging and Distribution

### Using the Packaging Tool

The `tools/pack_scrugn.py` script creates and extracts `.scrugn` files.

**Pack a plugin:**
```bash
python tools/pack_scrugn.py pack my_synth/ -o MySynth.scrugn
```

**Extract a plugin:**
```bash
python tools/pack_scrugn.py extract MySynth.scrugn -o my_synth_extracted
```

### Manual Installation

1. Copy the `.scrugn` file to `~/.tech-soft/plugins/`
2. Restart Tech-Note, or open the Plugin Manager app (it rescans on focus)
3. If it's a synth plugin, go to Options > TTS Engine to select it

### Using the Plugin Manager App

1. Open the Plugin Manager from the main menu or Options menu
2. Select "Install plugin"
3. Browse to your `.scrugn` file and confirm

### Distribution

Share the `.scrugn` file. Users place it in their `~/.tech-soft/plugins/` directory. There is no centralized plugin store at this time.

---

## 10. Best Practices

### Error Handling

- Never let exceptions escape from `speak()`, `stop()`, or `write()` — the app may crash
- Use try/except blocks around all external calls (DLLs, network, serial)
- Return `True` from `initialize()` only if all setup succeeded

### Threading

- `speak()`, `stop()`, and `write()` may be called from any thread
- Use locks (`threading.Lock()`) around shared state
- Do not block the calling thread for long periods — use background threads for audio playback

### Bundling Binaries

- Place DLLs, dictionaries, and other resources in a `bin/` directory inside the plugin
- Use `Path(__file__).parent / "bin" / "my_file.dll"` to locate them at runtime
- Only bundle what you need — keep the `.scrugn` file small

### The Interrupt Pattern

The most common bug in synth plugins is not handling `interrupt=True` correctly.

**Correct pattern:**
```python
def speak(self, text, interrupt=True):
    if interrupt:
        self.stop()  # Clear current speech first
    # Then speak the new text
```

**Wrong pattern:**
```python
def speak(self, text, interrupt=True):
    # Don't just pass interrupt as a flag to your engine
    # Make sure to actually stop/reset before speaking
    pass
```

### Plugin Identity

- Set `plugin_name` and `plugin_version` as class attributes (they override manifest values)
- Use a unique class name to avoid conflicts

### Cleanup

- `shutdown()` will be called on app exit — close handles, free memory, disconnect from services
- Do not rely on `__del__` for cleanup; the app may not always garbage-collect promptly

---

## 11. Troubleshooting

### Plugin not showing up

- Check that the `.scrugn` file is in `~/.tech-soft/plugins/`
- Verify `manifest.json` has `plugin_type` and `entry` set correctly
- Check the Python console/log for error messages
- Open the Plugin Manager app and press F1 to refresh

### App crashes on plugin load

- Check that your base class import is correct: `from core.plugin_base import SynthPlugin`
- Verify your class inherits from the correct base class
- Make sure `initialize()` returns `True` on success or handles failures gracefully
- Wrap your entry point code in try/except blocks

### Speech doesn't interrupt

If pressing Control or navigating doesn't stop current speech, your `speak()` method is probably not calling `self.stop()` when `interrupt=True`. See [The Interrupt Pattern](#the-interrupt-pattern).

### "Unknown synth module" error

- Ensure the plugin is loaded (check Plugin Manager)
- Go to Options > TTS Engine and re-select your plugin
- The synth selection is stored in `~/.tech-soft/account.json` under `synth_module`

### Terminal commands not appearing

- Verify your plugin's `get_commands()` method returns a list of tuples
- Each tuple must be exactly `(name, help_text, handler)` (3 elements)
- The handler must be a callable that accepts a single string argument
- Commands use the prefix `PluginName:command_name` in the Terminal
