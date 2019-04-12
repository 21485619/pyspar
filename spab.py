#!/usr/bin/python3 -u
import sys
import signal
import os
import sched
import time
from pymavlink import mavutil
import F2414Modem
from optparse import OptionParser
import collections
import TelemManager
import MavlinkManager
import SpabModel


task = sched.scheduler(time.time, time.sleep)
telemPeriod = 30   # seconds
# circular buffer to limit memory use
Locations = collections.deque(maxlen=10)
Delegates = {}
Waypoints = []


def read_loop(m):
    while True:
        task.run(blocking=False)
        msg = m.recv_match(blocking=False)
        if not msg:
            continue
        msg_type = msg.get_type()
        try:
            Delegates[msg_type](msg)
        except KeyError:
            pass
        # careful with delay, too long will miss msgs
        time.sleep(0.001)


def catch(sig, frame):
    print("\r")
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1)


def main():
    print("starting")
    parser = OptionParser("spab.py [options]")
    parser.add_option("--baudrate", dest="baudrate", type='int',
                      help='master port baud rate', default=57600)
    parser.add_option("--device", dest="device",
                      default=None, help="serial device")
    parser.add_option("--modem", dest="mport", default=None,
                      help="modem serial port")
    parser.add_option("--rate", dest="rate", default=4,
                      type='int', help='requested stream rate')
    parser.add_option("--source-system", dest="SOURCE_SYSTEM", type='int',
                      default=255, help="MAVLink source system for this GCS")
    parser.add_option("--showmessages", dest="showmessages",
                      action='store_true', help="show incoming messages", default=False)
    parser.add_option("--logfile", dest="log",
                      default=None, help="name of logfile")
    (opts, args) = parser.parse_args()
    if opts.device is None or opts.mport is None:
        print("You must specify a mavlink device and a modem device")
        sys.exit(1)

    signal.signal(signal.SIGINT, catch)

    # init objects
    try:
        master = mavutil.mavlink_connection(opts.device, baud=opts.baudrate)
        modem = F2414Modem.F2414Modem(opts.mport, baudrate=opts.baudrate)
        spabModel = SpabModel.SpabModel()
        telemManager = TelemManager.TelemManager(
            task, spabModel, modem, telemPeriod)
        mavlinkManager = MavlinkManager.MavlinkManager(
            task, spabModel, telemPeriod, master)
    except:
        print('failed to find devices')
        sys.exit(1)
    if opts.log is not None:
        logFile = open(opts.log, "a")
        sys.stderr = logFile
        sys.stdout = logFile
    print("====PYSPAB====\r")
    # init delegates
    global Delegates
    Delegates = {
        "HEARTBEAT": mavlinkManager.handle_heartbeat,
        "VFR_HUD": mavlinkManager.handle_hud,
        "ATTITUDE": mavlinkManager.handle_attitude,
        "GLOBAL_POSITION_INT": mavlinkManager.handle_gps_filtered,
        "MISSION_REQUEST": mavlinkManager.handle_mission_request,
        "MISSION_ACK": mavlinkManager.handle_mission_ack,
        "RC_CHANNELS_RAW": mavlinkManager.handle_rc_raw,
        "BAD_DATA": mavlinkManager.handle_bad_data,
        "MISSION_COUNT": mavlinkManager.handle_mission_count,
        "MISSION_ITEM": mavlinkManager.handle_mission_item
        # "MISSION_CURRENT": mavlinkManager.handle_mission_current
    }

    # set to run
    master.wait_heartbeat()
    master.mav.request_data_stream_send(master.target_system, master.target_component,
                                        mavutil.mavlink.MAV_DATA_STREAM_ALL, opts.rate, 1)
    master.mav.set_mode_send(master.target_system, 216, 216)
    telemManager.start()
    mavlinkManager.start()
    task.run(False)
    read_loop(master)


if __name__ == '__main__':
    main()
