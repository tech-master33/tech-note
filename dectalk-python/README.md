# dectalk - Python bindings for DECtalk TTS

Python ctypes bindings for the DECtalk text-to-speech engine (64-bit Windows).

## Install

```bash
pip install dectalk-python/
```

Or from PyPI (when published):
```bash
pip install dectalk
```

## Usage

```python
from dectalk import Dectalk

tts = Dectalk()
tts.load_dictionary()

tts.speaker = 0       # Perfect Paul
tts.rate = 180         # words per minute
tts.speak("Hello world")
tts.sync()
tts.close()
```

### Save to WAV file

```python
tts = Dectalk()
tts.load_dictionary()
tts.synthesize_to_wav("Hello world", "output.wav")
tts.close()
```

## API

| Method | Description |
|--------|-------------|
| `speak(text)` | Speak text synchronously |
| `rate` | Get/set speaking rate (words/min) |
| `speaker` | Get/set voice (0-8) |
| `volume` | Get/set volume |
| `pause()` / `resume()` | Pause/resume speech |
| `synthesize_to_wav(text, path)` | Speak to WAV file |
| `synthesize_to_memory(text)` | Speak to bytes |
