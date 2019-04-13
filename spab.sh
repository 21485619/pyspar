#!/bin/sh
echo "Shell script starting"
until (/home/pi/pyspar/spab.py --device /dev/ttyACM0 --modem /dev/ttyUSB0 --baudrate 115200 >> /tmp/spab.log); do
	echo "Server 'spab.py' crashed with exit code $?. Respawning.."
	sleep 5
done
