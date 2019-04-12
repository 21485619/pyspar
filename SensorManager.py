from ds18b20 import DS18B20
from time import sleep
from picamera import PiCamera
import base64
import sched
import time
import SpabModel
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn


class SensorManager:
    def __init__(self, scheduler, model, tempPeriod, picPeriod, readings):
        self.task = scheduler
        self.spabModel = model
        self.temp_p = tempPeriod
        self.pic_p = picPeriod
        self.readings = readings
        self.temp_sensor = DS18B20()
        self.temps = None
        self.camera = PiCamera()
        self.camera.resolution = (320, 240)
        self.camera.start_preview()
        self.base_64_string = None
        self.pendingImage = False
        self.ads = ADS.ADS1115
        self.chan = AnalogIn(self.ads, ADS.P0)
        self.conductivity_v = None
        self.conductivity = None

    def start(self):
        # self.task.enter(6, 1, self.get_temp, ())
        self.task.enter(10, 1, self.capture_image, argument=('image.jpg',))
        self.task.enter(8, 1, self.get_conductivity, ())

    def stop(self):
        self.task.cancel(self.get_temp)
        self.task.cancel(self.capture_image)

    def get_temp(self):
        # print("get_temp")
        self.temps = self.temp_sensor.get_temperature()
        self.spabModel.temperature = self.temps

        # self.task.enter(self.temp_p, 1, self.get_temp,())

    def capture_image(self, filename):
        print("capture_image")
        self.camera.capture(filename)
        self.pendingImage = True
        self.convert(filename)
        self.spabModel.image = self.base_64_string
        self.task.enter(self.pic_p, 1, self.capture_image, argument=('image.jpg',))

    def convert(self, filename):
        image = open(filename, 'rb')
        image_read = image.read()
        self.base_64_string = base64.encodebytes(image_read)

    def deconvert(self, filename):
        decoded = base64.decodebytes(self.base_64_string)
        image_result = open(filename, 'wb')
        image_result.write(decoded)

    def get_conductivity_v(self):
        volts = []
        for i in range(0, self.readings):
            volts.append(self.chan.voltage)
            time.sleep(0.025)
        volt_sum = 0
        for i in volts:
            volt_sum += i
        average = volt_sum / self.readings
        self.conductivity_v = average

    # TODO Calibrate
    # Return value of conductivity in ms/cm
    def get_conductivity(self):
        self.get_temp()
        self.get_conductivity_v()
        temp = self.temps
        temp_coefficient = 1.0 + 0.0185 * (temp - 25.0)
        cv = self.conductivity_v / 1000 / temp_coefficient
        if cv < 448:
            conductivity = 6.84 * cv - 64.32
        elif cv < 1457:
            conductivity = 6.98 * cv - 127
        else:
            conductivity = 5.3 * cv + 2278
        self.conductivity = conductivity / 1000
        self.spabModel.conductivity = self.conductivity
        self.task.enter(self.temp_p, 1, self.get_conductivity, ())


def main():
    task = sched.scheduler(time.time, time.sleep)
    spabModel = SpabModel.SpabModel()
    sensor_manager = SensorManager(task, spabModel, 5, 30, 4)
    sensor_manager.start()
    task.run(False)

    while True:
        task.run(blocking=False)
        time.sleep(0.001)


if __name__ == '__main__':
    main()

