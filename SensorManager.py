from ds18b20 import DS18B20


class SensorManager:
    def __init__(self):
        self.temp_sensor = DS18B20()
        self.temps = self.temp_sensor.get_temperature()

    def get_temp(self):
        self.temps = self.temp_sensor.get_temperature()
        return self.temps