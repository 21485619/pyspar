import serial
import time
import threading
import os

class F2414Modem:

    def send(self, data):
        """ Send string to remote server """
        self.sport.write(b'don')
        time.sleep(1)
        self.sport.write(bytearray(data, encoding='utf-8'))

    def subscribe(self, handler):
        """ Subscribe to dataReceived with F2414Modem += eventHandler """
        self.handlers.append(handler)
        return self

    def unsubscribe(self, handler):
        """ Unsubscribe to dataReceived with F2414Modem -= eventHandler """
        self.handlers.remove(handler)
        return self

    def __DataReceived(self, sender, earg=None):
        for handler in self.handlers:
            handler(sender, earg)

    def __monitor(self):
       while not self.die:
           data = self.sport.read(self.blocksize)
           if data is not b'':
               self.__DataReceived(self, earg=data)

    def __init__(self, port, baudrate):
        """ Create the monitor by specifying serial port and baudrate """
        ser = serial.Serial(port)
        self.die = False
        self.blocksize = 1024
        ser.baudrate = 115200
        ser.timeout = 1
        self.sport = ser
        self.handlers = []
        self.thread = threading.Thread(group=None, target=self.__monitor, name='mon', args=())
        self.thread.start()

    def __del__(self):
        self.die = True
        
    __iadd__ = subscribe
    __isub__ = unsubscribe
    __call__ = __DataReceived
