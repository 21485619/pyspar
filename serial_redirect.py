#!/bin/python3
import serial
import threading
import os
import time
import signal

portA = "/dev/ttyUSB0"
portB = "/dev/ttyUSB1"
baudrate = 57600
timeout = 1
blocksize = 1024
die = False

serA = serial.Serial(portA, baudrate)
serB = serial.Serial(portB, baudrate)
serA.name = 'A'
serB.name = 'B'
serA.timeout = serB.timout = timeout


def shuttle(from_port, to_port):
    while not die:
        data = from_port.read(1024)
        if data is not '':
            print(from_port.name + " > " + to_port.name + ": " + data)
        to_port.write(data)


def catch(sig, frame):
    print("Exiting...")
    os._exit(0)


threadA = threading.Thread(group=None, target=shuttle, name='a2b', args=(serA, serB))
threadB = threading.Thread(group=None, target=shuttle, name='b2a', args=(serB, serA))


threadA.start()
threadB.start()

signal.signal(signal.SIGINT, catch)


while(True):
    time.sleep(1)
