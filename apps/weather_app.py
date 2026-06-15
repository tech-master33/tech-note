import urllib.request
import json
import win32con
from core.app_base import SoftApp


class WeatherApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.state = "menu"
        self.menu_cursor = 0
        self.menu_items = ["Enter City", "Last Result", "Exit"]
        self.city = ""
        self.input_buf = ""
        self.weather_data = None
        self.error_msg = ""

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
                self.state = "result"
                self.speak(f"Weather in {self.weather_data['city']}: {self.weather_data['temp_c']} degrees Celsius, {self.weather_data['desc']}.")
        except Exception as e:
            self.error_msg = f"Failed to get weather: {str(e)}"
            self.speak(self.error_msg)
            self.state = "menu"

    def _render(self):
        if self.state == "menu":
            lines = ["Weather", ""]
            if self.error_msg:
                lines.append(self.error_msg)
                lines.append("")
            for i, item in enumerate(self.menu_items):
                prefix = ">" if i == self.menu_cursor else " "
                lines.append(f"{prefix} {item}")
            return "\n".join(lines)

        if self.state == "input":
            lines = ["Enter City", "", f"City: {self.input_buf}_", "", "Type city name. Enter to search. Escape to cancel."]
            return "\n".join(lines)

        if self.state == "result" and self.weather_data:
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

        return "Weather"

    def on_focus(self):
        self.state = "menu"
        self.menu_cursor = 0
        self.error_msg = ""
        self.speak("Weather. Enter a city to get current conditions.")
        self.window.update_text(self._render())

    def on_key(self, vk):
        if self.state == "input":
            if vk == win32con.VK_ESCAPE:
                self.state = "menu"
                self.speak("Cancelled.")
                self.window.update_text(self._render())
            elif vk == win32con.VK_RETURN:
                city = self.input_buf.strip()
                if city:
                    self.speak(f"Fetching weather for {city}...")
                    self.window.update_text(f"Loading weather for {city}...")
                    self._fetch_weather(city)
                    self.window.update_text(self._render())
            elif vk == win32con.VK_BACK:
                if self.input_buf:
                    self.input_buf = self.input_buf[:-1]
                    self.window.update_text(self._render())
            elif 0x20 <= vk <= 0x7E:
                self.input_buf += chr(vk)
                self.window.update_text(self._render())
            return

        if self.state == "result":
            if vk == win32con.VK_ESCAPE:
                self.exit_app()
            elif vk == win32con.VK_RETURN:
                self.state = "menu"
                self.menu_cursor = 0
                self.window.update_text(self._render())
            return

        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        if vk == win32con.VK_UP:
            self.menu_cursor = (self.menu_cursor - 1) % len(self.menu_items)
        elif vk == win32con.VK_DOWN:
            self.menu_cursor = (self.menu_cursor + 1) % len(self.menu_items)
        elif vk == win32con.VK_RETURN:
            if self.menu_cursor == 0:
                self.state = "input"
                self.input_buf = ""
                self.speak("Enter city name.")
            elif self.menu_cursor == 1:
                if self.weather_data:
                    self.state = "result"
                    self.speak(f"Weather in {self.weather_data['city']}.")
                else:
                    self.speak("No previous result.")
            elif self.menu_cursor == 2:
                self.exit_app()
                return

        self.window.update_text(self._render())

    def get_help_text():
        return "Weather. Get current weather for any city. Enter a city name to search."
