import os
import json
import time
import urllib.request
import urllib.error
import win32con
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.config import TECH_SOFT

SETTINGS_FILE = os.path.join(TECH_SOFT, "settings.json")
SESSIONS_DIR = os.path.join(TECH_SOFT, "chatgpt_sessions")

OPENAI_BASE = "https://api.openai.com/v1"
ZEN_BASE = "https://opencode.ai/zen/v1"

MODELS = {
    "OpenAI": [
        ("GPT-5.5", "gpt-5.5"),
        ("GPT-5.5 Pro", "gpt-5.5-pro"),
        ("GPT-5.4", "gpt-5.4"),
        ("GPT-5.4 Mini", "gpt-5.4-mini"),
        ("GPT-5.4 Nano", "gpt-5.4-nano"),
        ("GPT-5.3 Codex", "gpt-5.3-codex"),
        ("GPT-5.3 Codex Spark", "gpt-5.3-codex-spark"),
        ("GPT-5.2", "gpt-5.2"),
        ("GPT-5.1", "gpt-5.1"),
        ("GPT-5", "gpt-5"),
        ("GPT-5 Nano", "gpt-5-nano"),
    ],
    "OpenCode Zen": [
        ("GPT-5.5", "gpt-5.5"),
        ("GPT-5.5 Pro", "gpt-5.5-pro"),
        ("GPT-5.4", "gpt-5.4"),
        ("GPT-5.4 Mini", "gpt-5.4-mini"),
        ("Claude Opus 4.8", "claude-opus-4-8"),
        ("Claude Sonnet 4.6", "claude-sonnet-4-6"),
        ("Claude Haiku 4.5", "claude-haiku-4-5"),
        ("Gemini 3.5 Flash", "gemini-3.5-flash"),
        ("DeepSeek V4 Pro", "deepseek-v4-pro"),
        ("MiMo-V2.5 Free", "mimo-v2.5-free"),
    ],
}


def _load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}


def _save_settings(data):
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except:
        pass


def _http_post(url, data, headers, timeout=60):
    body = json.dumps(data).encode('utf-8')
    headers.setdefault("Content-Type", "application/json")
    headers.setdefault("User-Agent", "TechNote-ChatGPT/1.0")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='replace')
        raise Exception(f"HTTP {e.code}: {error_body[:200]}")
    except urllib.error.URLError:
        raise Exception("No internet connection")


class ChatGPTClient(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.settings = _load_settings()
        self.sessions = []
        self.current_session = None
        self.messages = []
        self.msg_index = 0
        self._history = []
        self._input_mode = None
        self._input_text = ""
        self._provider = self.settings.get("chatgpt_provider", "OpenAI")
        self._model_id = self.settings.get("chatgpt_model", "gpt-5.5")
        self._system_prompt = "You are a helpful assistant. Reply concisely."
        self._build_menu()

    def _push_history(self):
        self._history.append(self.menu)

    def _pop_history(self):
        if self._history:
            self.menu = self._history.pop()
            self.menu.announce_current()
            return True
        return False

    def _build_menu(self):
        root = MenuNode("ChatGPT")
        root.add_child(MenuNode("New Chat", self._new_chat))
        root.add_child(MenuNode("Chats", self._show_chats))
        root.add_child(MenuNode("Provider", self._show_providers))
        root.add_child(MenuNode("Model", self._show_models))
        root.add_child(MenuNode("Settings", self._show_settings))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _get_api_key(self):
        keys = self.settings.get("api_keys", {})
        if self._provider == "OpenAI":
            return keys.get("openai", "")
        elif self._provider == "OpenCode Zen":
            return keys.get("opencode_zen", "")
        return ""

    def _get_base_url(self):
        if self._provider == "OpenAI":
            return OPENAI_BASE
        elif self._provider == "OpenCode Zen":
            return ZEN_BASE
        return OPENAI_BASE

    def _call_api(self, messages):
        api_key = self._get_api_key()
        if not api_key:
            raise Exception(f"No API key for {self._provider}. Go to Settings to configure.")

        url = f"{self._get_base_url()}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}

        api_messages = [{"role": "system", "content": self._system_prompt}]
        for m in messages[-20:]:
            api_messages.append({"role": m["role"], "content": m["content"]})

        data = {"model": self._model_id, "messages": api_messages, "max_tokens": 4096}
        result = _http_post(url, data, headers)
        return result.get("choices", [{}])[0].get("message", {}).get("content", "")

    def _new_chat(self):
        self._input_mode = "chat_name"
        self._input_text = ""
        self.speak("Enter chat name, or press Enter for untitled.")
        self.window.update_text("Chat name: ")

    def _create_chat(self, name=""):
        if not name.strip():
            name = f"Chat {len(self.sessions) + 1}"
        session = {
            "id": str(int(time.time())),
            "name": name,
            "messages": [],
            "created": time.strftime("%Y-%m-%d %H:%M"),
            "provider": self._provider,
            "model": self._model_id,
        }
        self.sessions.append(session)
        self._save_sessions()
        self.current_session = session
        self.messages = session["messages"]
        self.speak(f"Chat '{name}' created. Type your message.")
        self._input_mode = "chat"
        self._input_text = ""
        self.window.update_text(f"Chat: {name}")

    def _save_sessions(self):
        try:
            os.makedirs(SESSIONS_DIR, exist_ok=True)
            path = os.path.join(SESSIONS_DIR, "chats.json")
            with open(path, 'w') as f:
                json.dump(self.sessions, f, indent=2)
        except:
            pass

    def _load_sessions(self):
        path = os.path.join(SESSIONS_DIR, "chats.json")
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    self.sessions = json.load(f)
            except:
                self.sessions = []

    def _show_chats(self):
        self._load_sessions()
        if not self.sessions:
            self.speak("No chats. Start a new one.")
            return
        self._push_history()
        root = MenuNode("Chats")
        for s in self.sessions:
            name = s.get("name", "Untitled")
            count = len(s.get("messages", []))
            root.add_child(MenuNode(f"{name} ({count} messages)", lambda sid=s["id"]: self._open_chat(sid)))
        root.add_child(MenuNode("Back", self._back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _open_chat(self, session_id):
        for s in self.sessions:
            if s["id"] == session_id:
                self.current_session = s
                self.messages = s.get("messages", [])
                self.msg_index = max(0, len(self.messages) - 1)
                self.speak(f"Opened {s.get('name', 'chat')}. {len(self.messages)} messages.")
                self._show_chat_view()
                return
        self.speak("Chat not found.")

    def _show_chat_view(self):
        self._push_history()
        root = MenuNode(self.current_session.get("name", "Chat"))
        if self.messages:
            last = self.messages[-1]
            role = last.get("role", "user")
            content = last.get("content", "")[:80]
            root.add_child(MenuNode(f"Last: {role}: {content}"))
        root.add_child(MenuNode("Send Message", self._start_chat_input))
        root.add_child(MenuNode("View History", self._view_history))
        root.add_child(MenuNode("Clear History", self._clear_history))
        root.add_child(MenuNode("Chat Info", self._chat_info))
        root.add_child(MenuNode("Export", self._export_chat))
        root.add_child(MenuNode("Back", self._back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _start_chat_input(self):
        self._input_mode = "chat"
        self._input_text = ""
        self.speak("Type your message. Press Enter to send.")
        self.window.update_text("Message: ")

    def _send_message(self):
        text = self._input_text.strip()
        if not text:
            self.speak("No message.")
            return
        self._input_mode = None

        self.window.update_text("Thinking...")

        try:
            temp_msgs = self.messages + [{"role": "user", "content": text}]
            response = self._call_api(temp_msgs)
            if response:
                self.messages.append({"role": "user", "content": text})
                self.messages.append({"role": "assistant", "content": response})
                self.current_session["messages"] = self.messages
                self._save_sessions()
                self.speak(response[:500])
                self.window.update_text(response[:200])
            else:
                self.speak("No response from API.")
        except Exception as e:
            self.speak(f"Error: {str(e)[:100]}")
            self.window.update_text("API Error")

    def _view_history(self):
        if not self.messages:
            self.speak("No messages yet.")
            return
        self._push_history()
        root = MenuNode("History")
        for i, m in enumerate(self.messages):
            role = m.get("role", "user")
            content = m.get("content", "")[:60]
            root.add_child(MenuNode(f"{i+1}. {role}: {content}"))
        root.add_child(MenuNode("Back", self._back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _clear_history(self):
        self.messages.clear()
        if self.current_session:
            self.current_session["messages"] = []
            self._save_sessions()
        self.speak("History cleared.")
        self._show_chat_view()

    def _chat_info(self):
        if not self.current_session:
            return
        s = self.current_session
        self.speak(f"Chat: {s.get('name')}. Provider: {s.get('provider')}. Model: {s.get('model')}. Messages: {len(s.get('messages', []))}")

    def _export_chat(self):
        if not self.current_session:
            return
        try:
            export_dir = os.path.join(TECH_SOFT, "chatgpt_exports")
            os.makedirs(export_dir, exist_ok=True)
            filename = f"{re.sub(r'[\\\\/:*?\"<>|]', '_', self.current_session.get('name', 'chat'))}_{int(time.time())}.txt"
            filepath = os.path.join(export_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Chat: {self.current_session.get('name')}\n")
                f.write(f"Provider: {self.current_session.get('provider')}\n")
                f.write(f"Model: {self.current_session.get('model')}\n")
                f.write(f"Date: {self.current_session.get('created')}\n")
                f.write("=" * 50 + "\n\n")
                for m in self.messages:
                    role = m.get("role", "user").upper()
                    f.write(f"[{role}]\n{m.get('content', '')}\n\n")
            self.speak(f"Exported to {filename}")
        except Exception as e:
            self.speak(f"Export failed: {str(e)[:50]}")

    def _show_providers(self):
        self._push_history()
        root = MenuNode("Provider")
        for name in MODELS.keys():
            marker = "> " if name == self._provider else ""
            root.add_child(MenuNode(f"{marker}{name}", lambda n=name: self._select_provider(n)))
        root.add_child(MenuNode("Back", self._back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _select_provider(self, name):
        self._provider = name
        self.settings["chatgpt_provider"] = name
        models = MODELS.get(name, [])
        if models:
            self._model_id = models[0][1]
            self.settings["chatgpt_model"] = self._model_id
        _save_settings(self.settings)
        self.speak(f"Provider: {name}")
        self._prompt_api_key(name)

    def _prompt_api_key(self, provider_name):
        keys = self.settings.get("api_keys", {})
        key_map = {"OpenAI": "openai", "OpenCode Zen": "opencode_zen"}
        key_id = key_map.get(provider_name, provider_name.lower())
        existing = keys.get(key_id, "")
        if existing:
            self.speak(f"{provider_name} key configured. Press Enter to keep, or type new key.")
        else:
            self.speak(f"Enter API key for {provider_name}.")
        self._input_mode = "api_key"
        self._input_text = existing if existing else ""
        self._pending_key_id = key_id
        self.window.update_text("API Key: ")

    def _save_api_key(self):
        key = self._input_text.strip()
        if key:
            if "api_keys" not in self.settings:
                self.settings["api_keys"] = {}
            self.settings["api_keys"][self._pending_key_id] = key
            _save_settings(self.settings)
            self.speak("API key saved.")
        self._input_mode = None
        self._pending_key_id = None
        self._show_providers()

    def _show_models(self):
        models = MODELS.get(self._provider, [])
        if not models:
            self.speak("No models available.")
            return
        self._push_history()
        root = MenuNode(f"Models ({self._provider})")
        for display, model_id in models:
            marker = "> " if model_id == self._model_id else ""
            root.add_child(MenuNode(f"{marker}{display}", lambda mid=model_id: self._select_model(mid)))
        root.add_child(MenuNode("Back", self._back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _select_model(self, model_id):
        self._model_id = model_id
        self.settings["chatgpt_model"] = model_id
        _save_settings(self.settings)
        self.speak(f"Model: {model_id}")
        self._show_models()

    def _show_settings(self):
        self._push_history()
        root = MenuNode("Settings")
        root.add_child(MenuNode(f"Provider: {self._provider}"))
        root.add_child(MenuNode(f"Model: {self._model_id}"))
        root.add_child(MenuNode(f"System: {self._system_prompt[:50]}...", self._edit_system))
        root.add_child(MenuNode("Back", self._back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _edit_system(self):
        self._input_mode = "system"
        self._input_text = self._system_prompt
        self.speak("Enter system prompt.")
        self.window.update_text(f"System: {self._system_prompt}")

    def _save_system(self):
        text = self._input_text.strip()
        if text:
            self._system_prompt = text
            self.speak("System prompt updated.")
        self._input_mode = None
        self._show_settings()

    def _back(self):
        if self._pop_history():
            return
        self._build_menu()
        self.menu.announce_current()

    def on_focus(self):
        if self._input_mode == "chat":
            self.window.update_text(f"Message: {self._input_text}")
        elif self._input_mode == "chat_name":
            self.window.update_text(f"Chat name: {self._input_text}")
        elif self._input_mode == "api_key":
            self.window.update_text("API Key: " + "*" * len(self._input_text))
        elif self._input_mode == "system":
            self.window.update_text(f"System: {self._input_text}")
        else:
            item = self.menu.get_current_item()
            title = item.title if item else "ChatGPT"
            self.speak(f"ChatGPT. {title}")
            self.window.update_text(f"ChatGPT: {title}")

    def on_key(self, vk):
        if self._input_mode:
            if vk == win32con.VK_ESCAPE:
                self._input_mode = None
                self.speak("Cancelled.")
                return
            if vk == win32con.VK_RETURN:
                if self._input_mode == "chat":
                    self._send_message()
                elif self._input_mode == "chat_name":
                    self._create_chat(self._input_text)
                elif self._input_mode == "api_key":
                    self._save_api_key()
                elif self._input_mode == "system":
                    self._save_system()
                return
            if vk == win32con.VK_BACK:
                self._input_text = self._input_text[:-1]
                if self._input_mode == "api_key":
                    self.window.update_text("API Key: " + "*" * len(self._input_text))
                else:
                    self.window.update_text(self._input_text)
                return
            ch = self._vk_to_char(vk)
            if ch:
                self._input_text += ch
                if self._input_mode == "api_key":
                    self.window.update_text("API Key: " + "*" * len(self._input_text))
                else:
                    self.window.update_text(self._input_text)
            return

        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))

        item = self.menu.get_current_item()
        if item:
            self.window.update_text("ChatGPT: " + item.title)

    def on_key_up(self, vk):
        if self._input_mode:
            return
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text("ChatGPT: " + item.title)

    def get_help_text(self):
        if self._input_mode == "chat":
            return "Type message. Enter to send. Escape to cancel."
        if self._input_mode == "api_key":
            return "Type API key. Enter to save. Escape to cancel."
        return "ChatGPT Client. Space next, Backspace previous, Enter select."
