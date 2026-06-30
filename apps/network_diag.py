import subprocess
import threading
import socket
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode


class NetworkDiag(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._result = ""
        self._running = False
        self._input_mode = None
        self._input_text = ""
        self._build_menu()

    def _build_menu(self):
        root = MenuNode("Network Diagnostics")
        root.add_child(MenuNode("Ping (google.com)", lambda: self._run_ping("google.com")))
        root.add_child(MenuNode("DNS Lookup", self._dns_lookup))
        root.add_child(MenuNode("My IP", self._my_ip))
        root.add_child(MenuNode("Traceroute", self._start_traceroute))
        root.add_child(MenuNode("Custom Ping", self._start_custom_ping))
        if self._result:
            root.add_child(MenuNode(f"Result: {self._result[:50]}..."))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _run_ping(self, target):
        if self._running:
            return
        self._running = True
        self._result = ""
        self.speak(f"Pinging {target}.")
        threading.Thread(target=self._do_ping, args=(target,), daemon=True).start()

    def _do_ping(self, target):
        try:
            result = subprocess.run(["ping", "-n", "4", target], capture_output=True, text=True, timeout=20)
            self._result = result.stdout.strip()[:200]
        except:
            self._result = "Ping failed."
        self._running = False
        self.speak(self._result[:100])

    def _dns_lookup(self):
        self._input_mode = "dns"
        self._input_text = ""
        self.speak("Enter hostname for DNS lookup.")
        self.window.update_text("Hostname: ")

    def _do_dns(self):
        host = self._input_text.strip()
        if not host:
            return
        try:
            ips = socket.gethostbyname_ex(host)
            self._result = f"{host}: {', '.join(ips[2])}"
        except:
            self._result = f"DNS lookup failed for {host}."
        self.speak(self._result[:100])

    def _my_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            self._result = f"Local IP: {ip}"
        except:
            self._result = "Could not determine IP."
        self.speak(self._result)

    def _start_traceroute(self):
        self._input_mode = "trace"
        self._input_text = ""
        self.speak("Enter target for traceroute.")
        self.window.update_text("Target: ")

    def _do_traceroute(self):
        target = self._input_text.strip()
        if not target:
            return
        if self._running:
            return
        self._running = True
        self.speak(f"Tracing route to {target}.")
        threading.Thread(target=self._do_trace, args=(target,), daemon=True).start()

    def _do_trace(self, target):
        try:
            result = subprocess.run(["tracert", "-h", "10", target], capture_output=True, text=True, timeout=30)
            self._result = result.stdout.strip()[:200]
        except:
            self._result = "Traceroute failed."
        self._running = False
        self.speak(self._result[:100])

    def _start_custom_ping(self):
        self._input_mode = "ping"
        self._input_text = ""
        self.speak("Enter host to ping.")
        self.window.update_text("Ping target: ")

    def on_focus(self):
        self._build_menu()
        item = self.menu.get_current_item()
        self.speak("Network Diagnostics. " + (item.title if item else ""))

    def on_key(self, vk):
        if self._input_mode:
            if vk == win32con.VK_ESCAPE:
                self._input_mode = None
                self._build_menu()
                self.menu.announce_current()
                return
            if vk == win32con.VK_RETURN:
                if self._input_mode == "dns":
                    self._input_mode = None
                    self._do_dns()
                elif self._input_mode == "trace":
                    self._input_mode = None
                    self._do_traceroute()
                elif self._input_mode == "ping":
                    self._input_mode = None
                    self._run_ping(self._input_text.strip())
                return
            if vk == win32con.VK_BACK:
                self._input_text = self._input_text[:-1]
                self.window.update_text(f"{self._input_mode}: {self._input_text}")
                return
            ch = self._vk_to_char(vk)
            if ch:
                self._input_text += ch
                self.window.update_text(f"{self._input_mode}: {self._input_text}")
            return
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        else:
            self._handle_first_letter_nav(vk, self.menu)
        item = self.menu.get_current_item()
        if item:
            self.window.update_text(item.title)

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text(item.title)

    def get_help_text(self):
        return "Network Diagnostics. Ping, DNS lookup, traceroute, IP info. Space next, Backspace previous. Escape exit."
