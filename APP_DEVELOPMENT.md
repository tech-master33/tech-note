# App Development Guide

Tech-Note apps are the core building blocks of the user experience — from the word processor to the calculator to the terminal. This guide covers the complete app framework, lifecycle, and patterns.

---

## Table of Contents

1. [Overview](#1-overview)
2. [SoftApp Base Class](#2-softapp-base-class)
3. [AppManager Lifecycle](#3-appmanager-lifecycle)
4. [Tutorial: Minimal App](#4-tutorial-minimal-app)
5. [Tutorial: Menu-Driven App](#5-tutorial-menu-driven-app)
6. [Tutorial: Text-Input App](#6-tutorial-text-input-app)
7. [Registering Apps](#7-registering-apps)
8. [State Persistence](#8-state-persistence)
9. [Using the Synth](#9-using-the-synth)
10. [Best Practices](#10-best-practices)

---

## 1. Overview

An app is a Python class that inherits from `SoftApp` and is registered in the main menu. Apps get full control over keyboard input while active, can speak text, display braille, and manage their own state.

### How Apps Work

1. User navigates the main menu and selects an app
2. The app's constructor is called with `(manager, window)` arguments
3. `on_focus()` is called when the app becomes active
4. All key presses go to `on_key()` while the app is active
5. The app sets `self.active = False` or calls `exit_app()` when done
6. The previous app is resumed or the main menu regains control

### Key Concepts

- **Manager**: The `BrailleNoteApp` singleton, accessed via `self.manager`
- **Window**: The `StealthWindow` for visual display, accessed via `self.window`
- **Speak**: Call `self.speak(text)` or `self.manager.synth.speak(text)` to speak
- **Menu**: Use `MenuSystem` for navigation within your app
- **Text Input**: Use `_start_text_input()` for typing text

---

## 2. SoftApp Base Class

Full reference of `SoftApp` (`core/app_base.py`).

### Constructor

```python
def __init__(self, manager, window, app_type='app')
```

| Parameter | Description |
|-----------|-------------|
| `manager` | The `BrailleNoteApp` instance (your app's parent) |
| `window` | The `StealthWindow` for visual UI |
| `app_type` | Optional type label (default: `'app'`) |

**Instance attributes set by constructor:**
| Attribute | Description |
|-----------|-------------|
| `self.manager` | Reference to `BrailleNoteApp` |
| `self.window` | Reference to `StealthWindow` |
| `self.speak` | Bound method: `self.manager.speak` |
| `self.stop` | Bound method: `self.manager.synth.stop` |
| `self.active` | `bool` — set to `False` to signal app exit |
| `self.app_type` | Optional type string |
| `self.input_mode` | Current input mode: `'menu'` or `'text'` (default `'menu'`) |
| `self._input_buf` | Text input buffer |
| `self._input_prompt` | Text input prompt string |
| `self._input_callback` | Callback for text input submission |

### Lifecycle Methods (all optional)

| Method | When Called | Purpose |
|--------|-------------|---------|
| `on_focus()` | App becomes active (launched or resumed) | Announce state, refresh content |
| `on_pause()` | Another app is launched on top | Save temporary state |
| `on_resume()` | App becomes active again after being paused | Restore temporary state, refresh |
| `on_destroy()` | App is being destroyed (user exited) | Final cleanup |
| `on_key(vk)` | Key pressed while app is active | Handle key input |
| `on_key_up(vk)` | Key released while app is active | Handle key release (e.g., Space for next) |
| `get_help_text()` | F1 help system | Return a help string |
| `get_state()` | Hibernate/resume | Return serializable state dict |
| `set_state(state)` | Hibernate/resume | Restore state from dict |

### Built-in Helper Methods

| Method | Description |
|--------|-------------|
| `_announce(text, speak=True)` | Update window text and optionally speak it |
| `_handle_menu_key(vk, menu)` | Standard menu navigation: Up/Left/Down/Right/Escape/Backspace/Space |
| `_handle_first_letter_nav(vk, menu)` | A-Z first-letter navigation in menus |
| `_handle_text_input(vk)` | Manage text input: enter, escape, backspace, character typing |
| `_start_text_input(prompt, callback, initial="")` | Enter text input mode. `callback` receives the entered text. |
| `_cancel_text_input()` | Cancel text input without submitting |
| `_submit_text_input()` | Submit the current input buffer (calls the callback) |
| `is_text_input_active()` | Returns `True` if currently in text input mode |
| `_load_json(path, default=None)` | Load JSON from a file |
| `_save_json(path, data)` | Atomically save JSON to a file |
| `_vk_to_char(vk)` | Convert a virtual key code to a character |
| `exit_app()` | Set `self.active = False` and reset temp synth params |

---

## 3. AppManager Lifecycle

`AppManager` (`core/app_base.py`) manages the app stack.

### Methods

| Method | Description |
|--------|-------------|
| `launch(app_class)` | Create a new app, pause the current one, push to stack, focus new app |
| `exit_current()` | Call `on_destroy()` + `exit_app()` on current app, pop stack, `on_resume()` previous |
| `is_active()` | Returns `True` if any app is active |
| `reset()` | Destroy all apps and clear the stack |

### Lifecycle Flow

```
User selects "Word Processor" in main menu
  → app_manager.launch(TechEdit)
    → current_app.on_pause()        # if an app was active
    → new_app = TechEdit(manager, window)
    → new_app.on_focus()
    → current_app = new_app
    → push old app onto stack

User presses Escape in Word Processor
  → app_manager.exit_current()
    → current_app.on_destroy()
    → current_app.exit_app()
    → pop previous app from stack
    → previous_app.on_resume()
    → current_app = previous_app
```

---

## 4. Tutorial: Minimal App

This app speaks when launched and exits on any key press.

### Step 1: Create the file

```python
# apps/hello_app.py
from core.app_base import SoftApp


class HelloApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)

    def on_focus(self):
        self._announce("Hello world! Press any key to exit.")

    def on_key(self, vk):
        self.exit_app()
```

### Step 2: Register in the menu

Add to `core/menu.py` in the `build_braillenote_menu()` function:

```python
from apps.hello_app import HelloApp

# Add after other imports and before return root:
root.add_child(MenuNode("Hello World", lambda: app_callback(HelloApp), "z"))
```

---

## 5. Tutorial: Menu-Driven App

This app shows a menu with options and handles navigation.

```python
# apps/color_app.py
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem


class ColorApp(SoftApp):
    COLORS = ["Red", "Green", "Blue"]

    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._build_menu()

    def _build_menu(self):
        root = MenuNode("Colors")
        for color in self.COLORS:
            root.add_child(MenuNode(color, lambda c=color: self._select_color(c)))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _select_color(self, color):
        self.speak(f"You selected {color}")

    def on_focus(self):
        self._announce("Color picker. Choose a color.")

    def on_key(self, vk):
        self._handle_menu_key(vk, self.menu)
        item = self.menu.get_current_item()
        if item:
            self.window.update_text(item.title)

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text(item.title)
```

---

## 6. Tutorial: Text-Input App

This app asks for your name and then greets you.

```python
# apps/greet_app.py
from core.app_base import SoftApp


class GreetApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._name = None

    def on_focus(self):
        if not self._name:
            self._start_text_input("What is your name?", self._on_name)

    def _on_name(self, name):
        if name:
            self._name = name
            self.speak(f"Hello, {name}!")
        self.exit_app()

    def on_key(self, vk):
        # The base class handles text input for us
        if vk == win32con.VK_ESCAPE:
            self._cancel_text_input()
            self.exit_app()
            return
        super().on_key(vk)
```

---

## 7. Registering Apps

### Built-in Apps (Hardcoded)

Add entries in `core/menu.py` inside `build_braillenote_menu()`:

```python
from apps.my_app import MyApp
root.add_child(MenuNode("My App", lambda: app_callback(MyApp), "x"))
```

The third argument is an optional shortcut key (letter or number). Use letters that are not already taken by other menu items.

### Installed Apps (Dynamic)

Apps can also be installed dynamically by placing a manifest in the `apps/` directory:

1. Create a subdirectory in `apps/your_app/`
2. Add a `manifest.json`:
   ```json
   {
       "name": "Your App",
       "module": "apps.your_app",
       "class": "YourAppClass"
   }
   ```
3. The app is automatically picked up when the menu is built.

---

## 8. State Persistence

Apps can save and restore state for hibernate/resume.

### Example

```python
def get_state(self):
    return {
        "cursor_position": self.cursor_pos,
        "current_file": self.current_file,
        "scroll_position": self.scroll_pos,
    }

def set_state(self, state):
    self.cursor_pos = state.get("cursor_position", 0)
    self.current_file = state.get("current_file", "")
    self.scroll_pos = state.get("scroll_position", 0)
```

The state dict must be JSON-serializable (strings, numbers, bools, lists, dicts). It is automatically saved to `~/.tech-soft/resume.json` when the device hibernates and restored on boot.

---

## 9. Using the Synth

Apps access the speech synthesizer through `self.speak` (bound method) or directly via `self.manager.synth`.

### Speaking Text

```python
self.speak("Hello world")              # Interrupts current speech
self.speak("Hello world", False)       # Queues text (doesn't interrupt)
self.manager.synth.speak("Hello")      # Direct access to synth object
```

### Stopping Speech

```python
self.stop()                            # Immediately stop speech
self.manager.synth.stop()              # Direct access
```

### Temporary Voice Overrides

Use `set_temp_params()` to temporarily change voice, rate, or pitch for your app. Settings are automatically restored when the app exits.

```python
self.manager.set_temp_params(rate=5, pitch=60, voice_index=2)
```

Or call `reset_temp_params()` manually to restore defaults early.

### Waiting for Speech to Finish

```python
self.manager.synth.wait_until_done(5000)  # Wait up to 5 seconds
```

### Learning from Existing Apps

The best way to learn app development is to study the built-in apps:

| App | File | What It Demonstrates |
|-----|------|---------------------|
| TechCalc | `apps/tech_calc.py` | Menu-driven app, calculator logic |
| NotesApp | `apps/notes_app.py` | Menu-driven, JSON persistence, text input |
| TechEdit | `apps/tech_edit.py` | Complex state machine, text editing, file I/O, session resume |
| TechFiles | `apps/tech_files.py` | Dynamic menus, file browsing, custom text input |
| TerminalApp | `apps/terminal_app.py` | Text input with history, command dispatch |
| PluginManagerApp | `apps/plugin_manager_app.py` | Plugin management, detail views |

---

## 10. Best Practices

### Key Handling

- Call `super().on_key(vk)` at the end of your override to get default text input handling
- Use `_handle_menu_key()` for standard menu navigation
- Use `_handle_first_letter_nav()` for first-letter menu navigation
- Handle `VK_ESCAPE` for exiting and `VK_BACK` for "back" consistently

### Menu Design

- Keep menu trees shallow (no more than 2-3 levels deep)
- Provide a "Back" option at the end of every menu
- Use shortcut letters that make sense for the item (first letter is conventional)
- Announce the current item on focus

### Performance

- Don't block `on_key()` — it runs on the main thread
- Use background threads for long operations
- Load/save JSON files quickly with `_load_json()` / `_save_json()`

### Error Handling

- Wrap external operations (file I/O, network) in try/except
- Speak error messages to the user rather than crashing
- Use `core.error_handler.log()` for logging

### Text Input

- Always provide a prompt when starting text input
- Handle `VK_ESCAPE` to cancel text input
- Remember that `_input_buf` is managed by the base class during text input
- The callback receives the final text string

### Help Text

Implement `get_help_text()` to return a concise description of your app's controls. This is spoken when the user presses F1 while in your app.
