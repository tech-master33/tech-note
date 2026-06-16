# MystMenu (Tech-Note)

A self-voicing, keyboard-driven interface for Windows, inspired by the BrailleNote mPower/Apex (KeySoft) series. MystMenu provides a streamlined, accessible environment for users who prefer keyboard navigation and speech feedback.

## Features
- **Self-voicing**: Built-in SAPI5 and SAPI4 speech support, no screen reader required.
- **Stealth UI**: Invisible to traditional screen readers to avoid "blank" or "pane" sounds, providing a clean audio experience.
- **Audio Ducking**: Automatically lowers system volume (background music, etc.) when the interface is speaking.
- **Sound Schemes**: Choose from multiple sound schemes including Classic, Minimal, and Default.
- **Keyboard-driven**: Full control via keyboard shortcuts and first-letter navigation.
- **Extensible**: Includes an integrated **App Store** to download and install new applications.

## Major Components
- **Main Menu**: Central hub for accessing core applications.
- **Game Center**: A collection of accessible games.
- **App Store**: Online catalog for discovering and installing additional modules.
- **Recovery System**: Built-in recovery tools for system maintenance.

## Applications
- **Productivity**: Word Processor, Calculator, File Manager, Planner, Address List, Email, Todo List, Notes.
- **Communication**: Chat App (Internet-based messaging), Internet Browser.
- **Utilities**: Unit Converter, Weather, Stopwatch, Alarm Clock, Password Generator, Typing Test.
- **Entertainment**: Media Player, FM Radio, and a wide variety of games.
- **Games**: Blackjack, Connect Four, Dice Roller, Game 2048, Hangman, Memory Match, Minesweeper, Puzzle Game, Snake, Solitaire, Sudoku, Tic Tac Toe.

## Navigation
- **Space / Down Arrow**: Next item in menu.
- **Backspace / Up Arrow**: Previous item in menu.
- **Enter**: Select / Open application.
- **Escape**: Go back / Exit application.
- **Space + O**: Options menu (Adjust speech rate, volume, voice, and sound schemes).
- **F1**: Contextual Help / Shortcuts list.
- **F5**: Status Info (Announces current time, date, and battery percentage).
- **Shift + F1**: Open Tutorial.
- **Backtick (`)**: Power Menu (Restart, Shutdown, Exit to Windows).
- **Alt + F4**: Immediate Exit.
- **A-Z**: First-letter navigation (Press the first letter of any menu item to jump to it).

## Requirements
- **64-bit Python 3.10+**
- **Dependencies**: Install via `pip install -r requirements.txt`

## Running
Execute the following command in the project root:
```bash
python boot_64.py
```
