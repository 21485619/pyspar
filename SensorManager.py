from ds18b20 import DS18B20
from time import sleep
from picamera import PiCamera
import base64


class SensorManager:
    def __init__(self, scheduler, model, tempPeriod, picPeriod):
        self.task = scheduler
        self.spabModel = model
        self.temp_p = tempPeriod
        self.pic_p = picPeriod
        self.temp_sensor = DS18B20()
        self.temps = None
        self.camera = PiCamera()
        self.camera.resolution = (320, 240)
        self.camera.start_preview()
        self.base_64_string = None
        self.pendingImage = False

    def start(self):
        self.task.enter(6, 1, self.get_temp, ())
        self.task.enter(10, 1, self.capture_image, ('image.jpg')) 

    def stop(self):
        self.task.cancel(self.get_temp)
        self.task.cancel(self.capture_image)
    
    #TODO Add temperature to SpabModel
    def get_temp(self):
        self.temps = self.temp_sensor.get_temperature()
        #self.spabModel.
        self.task.enter(self.temp_p, 1, self.get_temp,())

    def capture_image(self, filename):
        self.camera.capture(filename)
        self.pending_image = True
        self.task.enter(self.pic_p, 1, self.capture_image, ('image.jpg'))
        
    def convert(self, filename):
        image = open(filename, 'rb')
        image_read = image.read()
        self.base_64_string = base64.encodebytes(image_read)
        
    def deconvert(self, filename):
        decoded = base64.decodebytes(self.base_64_string)
        image_result = open(filename,'wb')
        image_result.write(decoded)        


def main():
        sensor_manager = SensorManager()
        sensor = sensor_manager.temp_sensor
        
        sensor_manager.capture_image('image.jpg')
        sensor_manager.convert('image.jpg')
        sensor_manager.deconvert('decoded.jpg')

        while True:
            temperature = sensor.get_temperature()
            print(temperature, '°C')
            sleep(1)

if __name__ == '__main__':
    main()

