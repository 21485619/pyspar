#!/usr/bin/python3
import sys
from pymavlink import mavutil
import time
from multiprocessing import Process

class MavlinkManager:
    def __init__(self, Scheduler, model, PollingPeriod, Master, telem_manager):
        self.task = Scheduler
        self.spabModel = model    # circular buffer to limit memory use
        self.PollingPeriod = PollingPeriod
        self.master = Master
        self.telem_manager = telem_manager
        self.Seq = 0
        self.Count = 0
        self.last_msg = None
        self.ack = False
        self.last_ack = None

    def missionSender(self):
        different = False
        if len(self.spabModel.Waypoints) != len(self.spabModel.pendingWaypoints):
            different = True
        else:
            for old, new in zip(self.spabModel.Waypoints, self.spabModel.pendingWaypoints):
                #print(old, new)
                if not new[0] or new[1]:
                    continue
                if abs(old[0] - new[0]) > 0.00001 or abs(old[1] - new[1]) > 0.00001:
                    different = True
        if different:
            print("new: ", self.spabModel.pendingWaypoints)
            print("existing: ", self.spabModel.Waypoints)
            print("Different")
            self.clear_missions()
            self.start_waypoint_send(len(self.spabModel.pendingWaypoints))
        self.task.enter(5, 1, self.missionSender, ())

    def start_waypoint_send(self, waypoint_count):
        print("start_waypoint_send")
        #print(self.master.target_system,
        #     mavutil.mavlink.MAV_COMP_ID_MISSIONPLANNER, waypoint_count)
        try:
            self.master.mav.mission_count_send(
                self.master.target_system, mavutil.mavlink.MAV_COMP_ID_MISSIONPLANNER, waypoint_count)
        except:
            print("mavutil send failure, re-attempting")
            self.start_waypoint_send(waypoint_count)

    def getWaypoints(self):
        try:
            self.master.mav.mission_request_list_send(
                self.master.target_system, mavutil.mavlink.MAV_COMP_ID_MISSIONPLANNER)
        except:
            print("mavutil send failure, re-attempting")
            self.getWaypoints()
            return
        self.task.enter(20, 1, self.getWaypoints, ())

    def clear_missions(self):
        try:
            self.master.mav.mission_clear_all_send(self.master.target_system, mavutil.mavlink.MAV_COMP_ID_MISSIONPLANNER)
        except:
            print("mavutil send failure, re-attempting")
            self.clear_missions()
            return
        self.last_msg = "clear_missions"

    def update_home(self):
        try:
            self.master.mav.set_home_position_send(
                self.master.target_system, self.spabModel.newHome(0), self.spabModel.newHome(1),
                0, 0, 0, 0, 0, 0, 0, 0)
        except:
            print("mavutil send failure, re-attempting")
            self.update_home()


    def start(self):
        self.task.enter(self.PollingPeriod, 1, self.missionSender, ())
        self.task.enter(5, 1, self.getWaypoints, ())
        self.clear_missions()

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
        gps_data = (float(msg.lat)/10**7,
                    float(msg.lon)/(10**7), msg.alt,
                    msg.relative_alt, msg.vx, msg.vz, msg.hdg)
        if gps_data[0] != 0 and gps_data[1] != 0:
            self.spabModel.LastLocation['latitude'] = gps_data[0]
            self.spabModel.LastLocation['longitude'] = gps_data[1]

    def handle_mission_item_reached(self, msg):
        print("Waypoint reached")
        self.telem_manager.waypoint_reached_send(msg.seq)


    def handle_mission_ack(self, msg):
        print("handle_mission_ack")
        self.last_ack = msg
        #print(msg)
        # if self.last_msg == "clear_missions":
        #     if msg.type != mavutil.mavlink.MAV_MISSION_ACCEPTED:
        #         print("mission clear failed")
        #         #self.clear_missions()
        #     else:
        #         print("mission clear success")
        #         self.ack = True
        # elif self.last_msg == "upload_missions":
        if msg.type != mavutil.mavlink.MAV_MISSION_ACCEPTED:
            print("mission upload failed")
        else:
            print("mission upload success")
            try:
                self.master.mav.mission_current_send(1)  # start misson at MavPt 1
                self.master.mav.command_long_send(self.master.target_system, mavutil.mavlink.MAV_COMP_ID_ALL,
                                                  mavutil.mavlink.MAV_CMD_DO_SET_MODE, mavutil.mavlink.MAV_MODE_GUIDED_ARMED, 0, 0, 0, 0, 0, 0, 0)
            except:
                print("mavutil send failure, re-attempting")
                self.handle_mission_ack(msg)
                return
            self.Count = 0
            self.Seq = 0
            self.ack = True

    def handle_mission_count(self, msg):
        #print("mission_count")
        self.Count = msg.count
        self.Seq = 0
        #print(str(self.Count) + " waypoints")
        try:
            self.master.mav.mission_request_send(
                self.master.target_system, mavutil.mavlink.MAV_COMP_ID_ALL, self.Seq)
        except:
            print("mavutil send failure, re-attempting")
            self.handle_mission_ack(msg)

    def handle_mission_item(self, msg):
        #print("mission_item")
        print("WP " + str(msg.seq) + " " + str(msg.x) + " " + str(msg.y))
        if self.Seq <= self.Count + 1:
            if msg.seq == 0:
                self.spabModel.currentHome = (msg.x, msg.y)
                #print("Home: ", self.spabModel.currentHome)
            else:
                print(msg.seq, len(self.spabModel.Waypoints))
                if msg.seq <= len(self.spabModel.Waypoints):
                    self.spabModel.Waypoints[msg.seq - 1] = (msg.x, msg.y)
                else:
                    self.spabModel.Waypoints.append((msg.x, msg.y))
            try:
                self.master.mav.mission_request_send(
                    self.master.target_system, mavutil.mavlink.MAV_COMP_ID_ALL, self.Seq)
            except:
                print("mavutil send failure, re-attempting")
                self.handle_mission_item(msg)
                return
            self.Seq += 1
        else:
            try:
                self.master.mav.mission_ack_send(
                    self.master.target_system, mavutil.mavlink.MAV_COMP_ID_ALL, mavutil.mavlink.MAV_MISSION_ACCEPTED)
            except:
                print("mavutil send failure, re-attempting")
                self.handle_mission_item(msg)
                return
            print("Spab Waypoints:")
            print(self.spabModel.Waypoints)

    def handle_mission_current(self, msg):
        print("starting at WP " + str(msg.seq))

    def handle_mission_request(self, msg):
        #print(msg)
        print("appending waypoints")
        if msg.seq == 0:
            if not self.spabModel.newHome:
                self.spabModel.newHome = self.spabModel.currentHome
            print("current home:", self.spabModel.currentHome)
            print("new home:", self.spabModel.newHome)
            waypoint = self.spabModel.newHome
        else:
            waypoint = self.spabModel.pendingWaypoints[msg.seq-1]
        print(waypoint)
        if waypoint:
            try:
                self.master.mav.mission_item_send(self.master.target_system,
                                                  mavutil.mavlink.MAV_COMP_ID_ALL,
                                                  msg.seq,
                                                  mavutil.mavlink.MAV_FRAME_GLOBAL,
                                                  mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 1, 1,
                                                  1.0, 15.0, 0.0,
                                                  0.0, waypoint[0], waypoint[1], 0)
            except:
                print("mavutil send failure, re-attempting")
                self.handle_mission_request(msg)
                return
        pass  # eof
    
    def handle_system_time(self, msg):
        gpsTime = int(msg.time_unix_usec)
        print(msg, gpsTime)
        self.spabModel.LastLocation["timestamp"] = gpsTime