import urllib.request
import json
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode


class WeatherApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.state = "menu"
        self.city = ""
        self.input_buf = ""
        self.weather_data = None
        self.error_msg = ""
        self.menu = None
        self._build_menu()

    def _build_menu(self):
        root = MenuNode("Weather")
        root.add_child(MenuNode("Enter City", self._start_input))
        if self.weather_data:
            root.add_child(MenuNode("Last Result", self._show_result))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _start_input(self):
        self.state = "input"
        self.input_buf = ""
        self.speak("Enter city name.")
        self.window.update_text("City:")

    def _show_result(self):
        if self.weather_data:
            self.state = "result"
            d = self.weather_data
            self.speak(f"Weather in {d['city']}: {d['temp_c']} degrees Celsius, {d['temp_f']} Fahrenheit, feels like {d['feels_c']} Celsius. {d['desc']}. Humidity {d['humidity']} percent. Wind {d['wind_kmph']} kilometers per hour {d['wind_dir']}. Visibility {d['visibility']} kilometers. UV index {d['uv']}.")
            self.window.update_text(self._render_result())
        else:
            self.speak("No previous result.")

    def _fetch_weather(self, city):
        try:
            url = f"https://wttr.in/{city}?format=j1"
            req = urllib.request.Request(url, headers={"User-Agent": "TechNote/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                current = data.get("current_condition", [{}])[0]
                self.weather_data = {
                    "city": city.title(),
                    "temp_c": current.get("temp_C", "?"),
                    "temp_f": current.get("temp_F", "?"),
                    "feels_c": current.get("FeelsLikeC", "?"),
                    "feels_f": current.get("FeelsLikeF", "?"),
                    "desc": current.get("weatherDesc", [{}])[0].get("value", "Unknown"),
                    "humidity": current.get("humidity", "?"),
                    "wind_kmph": current.get("windspeedKmph", "?"),
                    "wind_dir": current.get("winddir16Point", "?"),
                    "visibility": current.get("visibility", "?"),
                    "uv": current.get("uvIndex", "?"),
                }
                self.error_msg = ""
                self._show_result()
        except Exception as e:
            self.error_msg = f"Failed to get weather: {str(e)}"
            self.speak(self.error_msg)
            self.state = "menu"
            self._build_menu()
            self.window.update_text(self._render_menu())

    def _render_menu(self):
        lines = ["Weather"]
        if self.error_msg:
            lines.append(self.error_msg)
        return "\n".join(lines)

    def _render_result(self):
        if not self.weather_data:
            return "Weather"
        d = self.weather_data
        lines = [
            f"Weather for {d['city']}",
            "",
            f"Temperature:   {d['temp_c']}C / {d['temp_f']}F",
            f"Feels like:    {d['feels_c']}C / {d['feels_f']}F",
            f"Conditions:    {d['desc']}",
            f"Humidity:      {d['humidity']}%",
            f"Wind:          {d['wind_kmph']} km/h {d['wind_dir']}",
            f"Visibility:    {d['visibility']} km",
            f"UV Index:      {d['uv']}",
            "",
            "Enter to search again. Escape to exit.",
        ]
        return "\n".join(lines)

    def on_focus(self):
        self.state = "menu"
        self.error_msg = ""
        self._build_menu()
        self.speak("Weather. Enter a city to get current conditions.")
        self.window.update_text(self._render_menu())

    def on_key(self, vk):
        if self.state == "input":
            if vk == win32con.VK_ESCAPE:
                self.state = "menu"
                self._build_menu()
                self.speak("Cancelled.")
                self.window.update_text(self._render_menu())
            elif vk == win32con.VK_RETURN:
                city = self.input_buf.strip()
                if city:
                    self.speak(f"Fetching weather for {city}...")
                    self.window.update_text(f"Loading weather for {city}...")
                    self._fetch_weather(city)
            elif vk == win32con.VK_BACK:
                if self.input_buf:
                    self.input_buf = self.input_buf[:-1]
                    self.window.update_text(f"City: {self.input_buf}")
            elif 0x20 <= vk <= 0x7E:
                self.input_buf += chr(vk)
                self.window.update_text(f"City: {self.input_buf}")
            return

        if self.state == "result":
            if vk == win32con.VK_ESCAPE:
                self.exit_app()
            return

        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        elif vk == win32con.VK_BACK:
            self.menu.previous()
            self.window.update_text(self._render_menu())
        elif vk == win32con.VK_SPACE:
            if self.manager.space_used_in_chord:
                return
            self.menu.next()
            self.window.update_text(self._render_menu())
        elif vk == win32con.VK_RETURN:
            self.menu.select()
            self.window.update_text(self._render_menu())
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))
            self.window.update_text(self._render_menu())

    def get_help_text(self):
        return "Weather. Get current weather for any city. Enter a city name to search."
