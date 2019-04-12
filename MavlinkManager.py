#!/usr/bin/python3
import sys
from pymavlink import mavutil


class MavlinkManager:
    def __init__(self, Scheduler, model, PollingPeriod, Master):
        self.task = Scheduler
        self.spabModel = model    # circular buffer to limit memory use
        self.PollingPeriod = PollingPeriod
        self.master = Master
        self.Seq = 0
        self.Count = 0

    def missionSender(self):
        if self.spabModel.pendingWaypoints:
            self.start_waypoint_send(len(self.spabModel.pendingWaypoints))
        self.task.enter(5, 1, self.missionSender, ())

    def start_waypoint_send(self, waypoint_count):
        print("start_waypoint_send")
        print(self.master.target_system,
              mavutil.mavlink.MAV_COMP_ID_MISSIONPLANNER, waypoint_count)
        self.master.mav.mission_count_send(
            self.master.target_system, mavutil.mavlink.MAV_COMP_ID_MISSIONPLANNER, 1+len(self.spabModel.pendingWaypoints))

    def getWaypoints(self):
        self.master.mav.mission_request_list_send(
            self.master.target_system, mavutil.mavlink.MAV_COMP_ID_MISSIONPLANNER)
        self.task.enter(20, 1, self.getWaypoints, ())

    def start(self):
        self.task.enter(self.PollingPeriod, 1, self.missionSender, ())
        self.task.enter(5, 1, self.getWaypoints, ())

    def handle_bad_data(self, msg):
        pass
        # if mavutil.all_printable(msg.data):
        #     sys.stderr.write(msg.data)
        #     sys.stderr.flush()

    def handle_heartbeat(self, msg):
        #print("handle_heartbeat")
        self.spabModel.mode = mavutil.mode_string_v10(msg)
        self.spabModel.is_armed = msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
        self.spabModel.is_enabled = msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_GUIDED_ENABLED

    def handle_rc_raw(self, msg):
        #print("handle_rc_raw")
        self.spabModel.channels = (msg.chan1_raw, msg.chan2_raw,
                                   msg.chan3_raw, msg.chan4_raw,
                                   msg.chan5_raw, msg.chan6_raw,
                                   msg.chan7_raw, msg.chan8_raw)

    def handle_hud(self, msg):
        #print("handle_hud")
        self.spabModel.hud_data = (msg.airspeed, msg.groundspeed,
                                   msg.heading, msg.throttle,
                                   msg.alt, msg.climb)

    def handle_attitude(self, msg):
        #print("handle_attitude")
        self.spabModel.attitude_data = (msg.roll, msg.pitch,
                                        msg.yaw, msg.rollspeed,
                                        msg.pitchspeed, msg.yawspeed)

    def handle_gps_filtered(self, msg):
        #print("handle_gps_filtered")
        gps_data = (msg.time_boot_ms, float(msg.lat)/10**7,
                    float(msg.lon)/(10**7), msg.alt,
                    msg.relative_alt, msg.vx, msg.vz, msg.hdg)
        self.spabModel.LastLocation = dict(zip(
            ('timestamp', 'latitude', 'longitude', 'temperature', 'salinity'), gps_data[0:3]+(0, 0)))

    def handle_mission_ack(self, msg):
        #print("handle_mission_ack")
        print(msg)
        if msg.type != mavutil.mavlink.MAV_MISSION_ACCEPTED:
            print("mission upload failed")
        else:
            print("mission upload success")
            self.master.mav.mission_current_send(1)  # start misson at MavPt 1
            self.master.mav.command_long_send(self.master.target_system, mavutil.mavlink.MAV_COMP_ID_ALL,
                                              mavutil.mavlink.MAV_CMD_DO_SET_MODE, mavutil.mavlink.MAV_MODE_GUIDED_ARMED, 0, 0, 0, 0, 0, 0, 0)
            self.spabModel.pendingWaypoints.clear()
            self.Count = 0
            self.Seq = 0

    def handle_mission_count(self, msg):
        self.Count = msg.count
        self.Seq = 0
        #print(str(self.Count) + " waypoints")
        self.master.mav.mission_request_send(
            self.master.target_system, mavutil.mavlink.MAV_COMP_ID_ALL, self.Seq)

    def handle_mission_item(self, msg):
        print("WP " + str(msg.seq) + " " + str(msg.x) + " " + str(msg.y))
        if(self.Seq != self.Count):
            if(self.Seq == 0):
                self.spabModel.Home = (msg.x, msg.y)
            else:
                self.spabModel.Waypoints.append((msg.x, msg.y))
            self.master.mav.mission_request_send(
                self.master.target_system, mavutil.mavlink.MAV_COMP_ID_ALL, self.Seq)
            self.Seq += 1
        else:
            self.master.mav.mission_ack_send(
                self.master.target_system, mavutil.mavlink.MAV_COMP_ID_ALL, mavutil.mavlink.MAV_MISSION_ACCEPTED)

    def handle_mission_current(self, msg):
        print("starting at WP " + str(msg.seq))

    def handle_mission_request(self, msg):
        print(msg)
        print("appending waypoints")
        print(msg.seq)
        if msg.seq == 0:
            waypoint = self.spabModel.Home
        else:
            waypoint = self.spabModel.pendingWaypoints[msg.seq-1]
        print(waypoint)
        self.master.mav.mission_item_send(self.master.target_system,
                                          mavutil.mavlink.MAV_COMP_ID_ALL,
                                          msg.seq,
                                          mavutil.mavlink.MAV_FRAME_GLOBAL,
                                          mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 1, 1,
                                          1.0, 15.0, 0.0,
                                          0.0, waypoint[0], waypoint[1], 0)
        pass  # eof
