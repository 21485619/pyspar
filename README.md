# PYSPAB
Python based manager for the UWA Solar Powered Autonomous Boat (SPAB). This scripts acts as a middle layer between the standard Mavlink communication of the ardupilot firmware and a 3G modem used to accesss a commanding REST API.

# setting up raspberry pi
## pip3
`sudo apt-get update && sudo apt-get install python3-pip`
if not already installed, pip3 is recommended.

## hardware UART
The hardware uart on the raspberry pi 3 family is attached to a bluetooth module. Bluetooth isn't really needed so we can redirect the hardware UART to the GPIO pins for more reliable communication.

Add `dtoverlay=pi3-disable-bt` and `enable_uart=1` to the end of /boot/config.txt. Additionally run `sudo systemctl disable hciuart` in order to disable to bluetooth module. Otherwise it will continue to attempt to configure the bluetooth modem on the UART.

## disable linux console on GPIO pins
By default the linux console is attached to the GPIO pins. This will prevent the UART from being used for other things. To disable this remove `console=serial0,115200` from `/boot/cmdline.txt`

## Change 1-wire pin
By default, the  1-wire interface is on GPIO pin 4, but this pin is also used by the camera. To fix this, add the line `dtoverlay=w1-gpio,gpiopin=27` to the end of /boot/config.txt.

## Running at startup
In order to run immediately at startup and to maintain reliability a shell script (spab.sh) is used. If the python process dies, the shell script will restart the process.

Run `crontab -e` follow the prompts and insert the task `@reboot /home/pi/spab.sh`. This will cause cron to start the watchdog script when the pi reboots.

The shell script redirects output to `/tmp/spab.log`. If you need to read the output for any purpose `tail -f /tmp/spab.log`.
