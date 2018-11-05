from ds18b20 import DS18B20
from time import sleep


class SensorManager:
    def __init__(self):
        self.temp_sensor = DS18B20()
        self.temps = self.temp_sensor.get_temperature()

    def get_temp(self):
        self.temps = self.temp_sensor.get_temperature()
        return self.temps

def main():
        sensor = DS18B20()
        while True:
            temperature = sensor.get_temperature()
            print(temperature, '°C')
            sleep(1)

if __name__ == '__main__':
    main()

