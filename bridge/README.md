# Tech-Note 32-bit Bridge

One 32-bit program that lets 64-bit Tech-Note use 32-bit-only speech
technology. It serves two jobs over the same localhost JSON socket:

- **`tts` mode** — SAPI TTS (pywin32, falling back to 32-bit PowerShell's
  System.Speech), so 32-bit-only voices run inside the 64-bit app.
- **`plugin <plugin.scrugn>` mode** — hosts a `bits: 32` synth plugin.
  The plugin (and every DLL it loads via ctypes) runs here, because a
  32-bit DLL cannot be loaded into the 64-bit Tech-Note process.

The 64-bit side (`core/bridge_launcher.py`) prefers the compiled
`TechNoteBridge32.exe`; if it isn't present it falls back to running
`bridge_main.py` under a 32-bit Python, so development works without the
exe. `BridgeTTS` (`core/tts_bridge.py`) and `BridgePluginSynth`
(`core/plugin_bridge.py`) drive it; the helper is respawned automatically
if it dies.

## Running directly

```
python32 bridge_main.py tts [port]
python32 bridge_main.py plugin <plugin.scrugn> [port]
```

On startup it prints `LISTENING <port>`; commands are newline-delimited
JSON (`ping`, `speak`, `stop`, `rate`/`get_rate`, `volume`/`get_volume`,
`pitch`/`get_pitch`, `voice`/`voices`/`get_voice`, the generic
`call` verb, `shutdown`).

## Building the exe

The exe must be built with a **32-bit** Python so it can load 32-bit
DLLs. From the project root:

```
# 1. Create a 32-bit build environment (point PY32 at your 32-bit python)
"C:\...\Python311-32\python.exe" -m venv bridge/build-venv
bridge/build-venv/Scripts/python -m pip install pyinstaller pywin32

# 2. Build (hidden imports bundle the stdlib modules plugins commonly use)
bridge/build-venv/Scripts/pyinstaller --onefile --name TechNoteBridge32 \
  --paths . \
  --hidden-import core.plugin_base \
  --hidden-import platform --hidden-import ctypes --hidden-import ctypes.wintypes \
  --hidden-import re --hidden-import time --hidden-import random \
  --hidden-import collections --hidden-import functools --hidden-import traceback \
  --hidden-import logging --hidden-import io --hidden-import struct \
  --hidden-import math --hidden-import codecs --hidden-import string \
  --hidden-import unicodedata --hidden-import base64 --hidden-import hashlib \
  --hidden-import select --hidden-import queue --hidden-import enum \
  --hidden-import itertools --hidden-import gc --hidden-import warnings \
  --distpath bridge/build/dist --workpath bridge/build/work --specpath bridge/build \
  bridge/bridge_main.py

# 3. Ship it
cp bridge/build/dist/TechNoteBridge32.exe bridge/TechNoteBridge32.exe
```

`bridge/build-venv/` and `bridge/build/` are gitignored; the exe itself
is committed so end users don't need a 32-bit Python.

## Plugin notes

The exe is a frozen environment: it bundles the stdlib modules listed
above plus `core.plugin_base`. A bridge-hosted plugin should stick to
those (ctypes + the SynthPlugin base cover typical DLL work); anything
else must be declared as an extra `--hidden-import` when rebuilding.
