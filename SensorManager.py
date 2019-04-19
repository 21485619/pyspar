from ds18b20 import DS18B20
from picamera import PiCamera
import base64
import sched
import time
import SpabModel
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import board
import busio
import statistics


class SensorManager:
    def __init__(self, scheduler, model, temp_period, pic_period, readings):
        self.task = scheduler
        self.spabModel = model
        self.temp_p = temp_period
        self.pic_p = pic_period
        self.readings = readings
        self.temp_sensor = DS18B20()
        self.camera = PiCamera()
        self.camera.resolution = (320, 240)
        self.camera.start_preview()

        i2c = busio.I2C(board.SCL, board.SDA)
        self.ads = ADS.ADS1115(i2c)
        self.chan = AnalogIn(self.ads, ADS.P0)

    def start(self):
        # self.task.enter(6, 1, self.get_temp, ())
        self.task.enter(10, 1, self.capture_image, ())
        self.task.enter(8, 1, self.update_readings, ())

    def stop(self):
        self.task.cancel(self.get_temp)
        self.task.cancel(self.capture_image)
        
    def update_readings(self):
        temp = self.get_temp()
        cv = self.get_conductivity_v()
        self.get_conductivity(temp, cv)
        print("Readings updated")

    def get_temp(self):
        # print("get_temp")
        temp = self.temp_sensor.get_temperature()
        self.spabModel.temperature = temp
        # self.task.enter(self.temp_p, 1, self.get_temp,())
        return temp

    def capture_image(self):
        print("capture_image")
        filename = "image_" + str(self.spabModel.last_pic_num) + ".jpg"
        self.camera.capture(filename)
        self.spabModel.latest_image = self.convert(filename)
        if self.spabModel.last_pic_num < 10000:
            self.spabModel.last_pic_num += 1
        else:
            self.spabModel.last_pic_num = 0
        self.task.enter(self.pic_p, 1, self.capture_image, ())

    @staticmethod
    def convert(filename):
        image = open(filename, 'rb')
        image_read = image.read()
        return base64.encodebytes(image_read)
    
    @staticmethod
    def deconvert(base_64_string, filename):
        decoded = base64.decodebytes(base_64_string)
        image_result = open(filename, 'wb')
        image_result.write(decoded)

    def get_conductivity_v(self):
        volts = []
        for i in range(0, self.readings):
            volts.append(self.chan.voltage)
            time.sleep(0.025)
        if volts:
            return statistics.median(volts)
        else:
            return 0

    # TODO Calibrate
    # Return value of conductivity in ms/cm
    def get_conductivity(self, temp, cv):
        temp_coefficient = 1.0 + 0.0185 * (temp - 25.0)
        volt_coefficient = cv / 1000 / temp_coefficient
        if volt_coefficient < 150:
            print("No solution")
            conductivity = 0
        elif volt_coefficient > 3300:
            print("Out of range")
            conductivity = -1
        elif volt_coefficient < 448:
            conductivity = 6.84 * volt_coefficient - 64.32
        elif volt_coefficient < 1457:
            conductivity = 6.98 * volt_coefficient - 127
        else:
            conductivity = 5.3 * volt_coefficient + 2278
        self.spabModel.conductivity = conductivity / 1000
        #self.task.enter(self.temp_p, 1, self.get_conductivity, ())


def main():
    task = sched.scheduler(time.time, time.sleep)
    spabModel = SpabModel.SpabModel()
    sensor_manager = SensorManager(task, spabModel, 5, 10, 4)
    sensor_manager.start()
    task.run(False)

    while True:
        task.run(blocking=False)
        sensor_manager.update_readings()
        print(spabModel.temperature)
        time.sleep(1)


if __name__ == '__main__':
    main()

