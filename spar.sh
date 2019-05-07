#!/bin/sh
echo "Shell script starting"
until (python3 /home/pi/pyspar/spar.py --device /dev/ttyACM0 --modem /dev/ttyUSB0 --baudrate 115200 >> /tmp/spar.log); do
	echo "Server 'spar.py' crashed with exit code $?. Respawning.."
	sleep 5
done
