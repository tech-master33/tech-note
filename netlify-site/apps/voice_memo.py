import os
import json
import time
import win32con
import threading
from core.app_base import SoftApp
from core.config import TECH_SOFT
from core.menu import MenuNode, MenuSystem

try:
    import sounddevice as sd
    import soundfile as sf
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False

class VoiceMemoApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.memos_dir = os.path.join(TECH_SOFT, 'voice_memos')
        os.makedirs(self.memos_dir, exist_ok=True)
        self.menu = None
        self.state = "menu"
        self.recording = False
        self.playing = False
        self._record_thread = None
        self._play_thread = None
        self._record_frames = []
        self._record_samplerate = 44100
        self._record_channels = 1
        self._current_file = None

    def _build_menu(self):
        root = MenuNode("Voice Memos")
        root.add_child(MenuNode("New Recording", self._start_recording, "n"))
        memos = self._list_memos()
        for m in memos:
            root.add_child(MenuNode(m, lambda name=m: self._select_memo(name)))
        if not memos:
            root.add_child(MenuNode("No recordings"))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _list_memos(self):
        files = [f for f in os.listdir(self.memos_dir) if f.endswith('.wav')]
        files.sort(reverse=True)
        return files

    def _select_memo(self, filename):
        self._current_file = filename
        path = os.path.join(self.memos_dir, filename)
        try:
            info = sf.info(path)
            duration = self._format_duration(info.duration)
            self.speak(f"{filename}. Duration: {duration}.")
        except:
            self.speak(filename)
        
        root = MenuNode(filename)
        root.add_child(MenuNode("Play", self._play_memo))
        root.add_child(MenuNode("Delete", self._delete_memo))
        root.add_child(MenuNode("Back", self._build_menu_back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _build_menu_back(self):
        self._build_menu()
        self.menu.announce_current()

    def _format_duration(self, seconds):
        m, s = divmod(int(seconds), 60)
        if m > 0:
            return f"{m} minute{'s' if m != 1 else ''} {s} second{'s' if s != 1 else ''}"
        return f"{s} second{'s' if s != 1 else ''}"

    def _start_recording(self):
        if not HAS_AUDIO:
            self.speak("Audio recording requires sounddevice and soundfile.")
            return
        self.recording = True
        self._record_frames = []
        self.speak("Recording. Press Escape to stop.")
        self.window.update_text("Recording...")
        self._record_thread = threading.Thread(target=self._do_record, daemon=True)
        self._record_thread.start()

    def _do_record(self):
        try:
            with sd.InputStream(samplerate=self._record_samplerate,
                                channels=self._record_channels,
                                dtype='int16') as stream:
                while self.recording:
                    data, overflowed = stream.read(1024)
                    self._record_frames.append(data.copy())
        except Exception:
            self.recording = False

    def _stop_recording(self):
        if not self.recording:
            return
        self.recording = False
        if self._record_thread:
            self._record_thread.join(timeout=2)
        
        if not self._record_frames:
            self.speak("No audio recorded.")
            self.state = "menu"
            return

        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"memo_{timestamp}.wav"
        path = os.path.join(self.memos_dir, filename)
        
        try:
            import numpy as np
            audio_data = np.concatenate(self._record_frames, axis=0)
            sf.write(path, audio_data, self._record_samplerate)
            duration = self._format_duration(len(audio_data) / self._record_samplerate)
            self.speak(f"Saved: {filename}. Duration: {duration}.")
        except Exception:
            self.speak("Failed to save recording.")
        
        self._record_frames = []
        self._build_menu()
        self.menu.announce_current()

    def _play_memo(self):
        if not HAS_AUDIO:
            self.speak("Playback requires sounddevice and soundfile.")
            return
        if not self._current_file:
            return
        
        path = os.path.join(self.memos_dir, self._current_file)
        if not os.path.exists(path):
            self.speak("File not found.")
            return

        self.playing = True
        self.speak(f"Playing {self._current_file}.")
        self.window.update_text(f"Playing: {self._current_file}")
        self._play_thread = threading.Thread(target=self._do_play, args=(path,), daemon=True)
        self._play_thread.start()

    def _do_play(self, path):
        try:
            data, samplerate = sf.read(path)
            sd.play(data, samplerate)
            sd.wait()
        except Exception:
            pass
        finally:
            self.playing = False

    def _delete_memo(self):
        if not self._current_file:
            return
        path = os.path.join(self.memos_dir, self._current_file)
        try:
            if os.path.exists(path):
                os.remove(path)
            self.speak(f"Deleted {self._current_file}.")
        except Exception:
            self.speak("Failed to delete.")
        self._current_file = None
        self._build_menu()
        self.menu.announce_current()

    def on_focus(self):
        self._build_menu()
        item = self.menu.get_current_item()
        self.speak("Voice Memos. " + item.title)
        self.window.update_text("Voice Memos: " + item.title)

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            if self.recording:
                self._stop_recording()
                return
            if self.playing:
                try:
                    sd.stop()
                except:
                    pass
                self.playing = False
                self.speak("Stopped.")
                return
            if self.state != "menu":
                self.state = "menu"
                self.on_focus()
                return
            self.exit_app()
            return

        if self.state == "menu":
            self._handle_menu(vk)

    def _handle_menu(self, vk):
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))
        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Voice Memos: " + item.title)

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            if self.state == "menu":
                self.menu.next()
                item = self.menu.get_current_item()
                if item:
                    self.window.update_text("Voice Memos: " + item.title)

    def get_help_text(self):
        if self.recording:
            return "Recording. Press Escape to stop."
        if self.playing:
            return "Playing. Press Escape to stop."
        return "Voice Memos. Space for next, Backspace for previous. Enter to select. Escape to exit."
