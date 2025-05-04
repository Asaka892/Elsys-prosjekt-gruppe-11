from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Rectangle
from kivy.clock import Clock
import time
import random
from datetime import datetime, timedelta
from backend import control_relay


# Simulert sensor-data

# Dummy værdata
def get_weather():
    return "Sol  og lett bris"

class SourceDiagram(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.source = "Solcelle"
        self.labels = []
        Clock.schedule_interval(self.update_diagram, 2)

    def set_source(self, source):
        self.source = source

    def update_diagram(self, dt):
        self.canvas.clear()
        for label in self.labels:
            self.remove_widget(label)
        self.labels.clear()

        with self.canvas:
            Color(0, 0, 0, 1)
            Rectangle(pos=self.pos, size=self.size)

            width = self.width
            height = self.height
            box_width = 100
            box_height = 100
            spacing = (width - 3 * box_width) / 4

            y = height / 2 - box_height / 2
            x1 = spacing
            x2 = x1 + box_width + spacing
            x3 = x2 + box_width + spacing

            Color(0, 1, 0, 1)
            Rectangle(pos=(x1, y), size=(box_width, box_height))
            self.draw_label("Solcelle", x1, y + box_height + 5)

            Color(0.5, 0.5, 0.5, 1)
            Rectangle(pos=(x2, y), size=(box_width, box_height))
            self.draw_label("Batteri", x2, y + box_height + 5)

            Color(1, 0, 0, 1)
            Rectangle(pos=(x3, y), size=(box_width, box_height))
            self.draw_label("Generator", x3, y + box_height + 5)

            if "Solcelle" in self.source:
                Color(0, 1, 0, 1)
                Line(points=[x1 + box_width, y + box_height / 2, x2, y + box_height / 2], width=3)
            else:
                Color(1, 0, 0, 1)
                Line(points=[x3, y + box_height / 2, x2 + box_width, y + box_height / 2], width=3)

    def draw_label(self, text, x, y):
        label = Label(text=text, font_size='16sp', color=(1, 1, 1, 1), size_hint=(None, None), size=(100, 30), pos=(x, y))
        self.labels.append(label)
        self.add_widget(label)

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        self.energy_wh = 0
        self.last_update_time = time.time()

        # Endret her: klokkeslett og vær til venstre
        top_info = BoxLayout(orientation='horizontal', size_hint=(1, 0.1))
        left_box = BoxLayout(orientation='vertical', size_hint=(None, 1), width=200)

        self.clock_label = Label(text="Tid: --:--:--", font_size='18sp', halign='left', valign='top')
        self.weather_label = Label(text="Været i dag: ...", font_size='16sp', halign='left', valign='top')

        left_box.add_widget(self.clock_label)
        left_box.add_widget(self.weather_label)

        top_info.add_widget(left_box)
        layout.add_widget(top_info)

        self.source_diagram = SourceDiagram(size_hint=(1, 0.3))
        layout.add_widget(self.source_diagram)

        self.labels = {
            'solar_voltage': Label(text="Solspenning: ... V", font_size='20sp'),
            'solar_current': Label(text="Solstrøm: ... mA", font_size='20sp'),
            'solar_power': Label(text="Soleffekt: ... W", font_size='20sp'),
            'battery_voltage': Label(text="Batteri: ... V", font_size='20sp'),
            'status': Label(text="Status: ...", font_size='20sp'),
            'energy': Label(text="Energi produsert i dag: 0.00 Wh", font_size='20sp')
        }

        for label in self.labels.values():
            layout.add_widget(label)

        self.graph_button = Button(text="Vis graf", size_hint=(None, None), size=(150, 50), pos_hint={'right': 1, 'y': 0})
        self.graph_button.bind(on_press=self.go_to_graph)
        layout.add_widget(self.graph_button)

        self.add_widget(layout)
        Clock.schedule_interval(self.update_data, 2)
        Clock.schedule_interval(self.update_clock, 1)

    def update_clock(self, dt):
        now = datetime.now()
        self.clock_label.text = now.strftime("Tid: %H:%M:%S")
        self.weather_label.text = f"Været i dag: {get_weather()}"

    def update_data(self, dt):
        now = time.time()
        delta_time = now - self.last_update_time
        self.last_update_time = now

        data = control_relay()
        power_w = data['solar_power']
        self.energy_wh += (power_w * delta_time) / 3600.0

        self.labels['solar_voltage'].text = f"Solspenning: {data['solar_voltage']} V"
        self.labels['solar_current'].text = f"Solstrøm: {data['solar_current']} mA"
        self.labels['solar_power'].text = f"Soleffekt: {data['solar_power']} W"
        self.labels['battery_voltage'].text = f"Batteri: {data['battery_voltage']} V"
        self.labels['status'].text = f"Status: {data['status']}"
        self.labels['energy'].text = f"Energi i dag: {self.energy_wh:.2f} Wh"

        self.source_diagram.set_source(data['status'])

    def go_to_graph(self, instance):
        self.manager.current = 'graph'

class GraphWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.times = []
        self.values = []
        self.tick_labels = []
        self.start_time = time.time()
        self.start_datetime = datetime.now()
        Clock.schedule_interval(self.update_data, 2)
        Clock.schedule_interval(self.redraw, 2)

    def update_data(self, dt):
        t = time.time() - self.start_time
        value = control_relay()["solar_power"]
        self.times.append(t)
        self.values.append(value)
        if len(self.times) > 100000:
            self.times = self.times[-10000:]
            self.values = self.values[-10000:]

    def redraw(self, dt):
        self.canvas.clear()

        for lbl in self.tick_labels:
            self.remove_widget(lbl)
        self.tick_labels.clear()

        with self.canvas:
            Color(0.1, 0.1, 0.1, 1)
            Rectangle(pos=self.pos, size=self.size)

            Color(1, 1, 1, 1)
            Line(points=[60, 120, self.width - 20, 120], width=1.5)
            Line(points=[60, 120, 60, self.height - 20], width=1.5)

            if len(self.times) < 2:
                return

            x_min, x_max = self.times[0], self.times[-1]
            x_range = max(x_max - x_min, 1)
            y_max = max(self.values)
            y_range = max(y_max, 1)

            for i in range(6):
                t = x_min + (x_range / 5) * i
                x = 60 + ((t - x_min) / x_range) * (self.width - 80)
                Line(points=[x, 115, x, 125], width=1)
                current_time = self.start_datetime + timedelta(seconds=t)
                lbl = Label(text=current_time.strftime("%H:%M:%S"), font_size='12sp', pos=(x - 30, 95),
                            size_hint=(None, None), size=(60, 20))
                self.add_widget(lbl)
                self.tick_labels.append(lbl)

            for i in range(6):
                val = (y_max / 5) * i
                y = 120 + (val / y_range) * (self.height - 140)
                Line(points=[55, y, 65, y], width=1)
                lbl = Label(text=f"{val:.1f}W", font_size='12sp', pos=(5, y - 10),
                            size_hint=(None, None), size=(50, 20))
                self.add_widget(lbl)
                self.tick_labels.append(lbl)

            for i in range(len(self.times) - 1):
                Color(0.2, 0.6, 1, 1)
                x1 = 60 + ((self.times[i] - x_min) / x_range) * (self.width - 80)
                x2 = 60 + ((self.times[i + 1] - x_min) / x_range) * (self.width - 80)
                y1 = 120 + (self.values[i] / y_range) * (self.height - 140)
                y2 = 120 + (self.values[i + 1] / y_range) * (self.height - 140)
                Line(points=[x1, y1, x2, y2], width=2)

class GraphScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        self.graph = GraphWidget(size_hint=(1, 0.9))
        layout.add_widget(self.graph)

        self.back_button = Button(text="Tilbake", size_hint=(None, None), size=(150, 50), pos_hint={'right': 1, 'y': 0})
        self.back_button.bind(on_press=self.go_back)
        layout.add_widget(self.back_button)

        self.add_widget(layout)

    def go_back(self, instance):
        self.manager.current = 'main'

class SolarApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(GraphScreen(name='graph'))
        return sm

if __name__ == '__main__':
    SolarApp().run()f