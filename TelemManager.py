#!/usr/bin/python3
import json
import collections
import time


class TelemManager:
    def __init__(self, Scheduler, model, Modem, TelemPeriod, SensorManager):
        self.task = Scheduler
        self.spabModel = model
        self.modem = Modem
        self.PollingPeriod = TelemPeriod
        self.sensor_manager = SensorManager
        self.AcceptedCommands = collections.deque(maxlen=10)

    def remoteTelemetry(self):
        #print('remote telemetry')
        # self.spabModel.LastLocation = dict(zip(
        #    ('timestamp', 'latitude', 'longitude', 'temperature', 'salinity'),  ("0", 111, 66) + (0, 0)))
        self.sensor_manager.update_readings()
        body_dict = {
            "msg_type": "data_upload",
            "sourceId": "spar1",
            "timestamp": self.spabModel.LastLocation["timestamp"],
            "latitude": self.spabModel.LastLocation["latitude"],
            "longitude": self.spabModel.LastLocation["longitude"],
            "temperature": self.spabModel.temperature,
            "salinity": self.spabModel.conductivity
            # "img": self.spabModel.latest_image
        }
        body = json.dumps(body_dict)
        length = len(body)
        req = """POST /solarboat/api/data.cgi HTTP/1.1
Host: therevproject.com
Accept: */*
Connection: close
Content-type: application/json
Content-Length: """
        req += str(length) + "\r\n\r\n"
        req += body + "\r\n\r\n"
        print(req)
        self.modem.send(req)
        self.task.enter(self.PollingPeriod, 1, self.requestCommands, ())

    def waypoint_reached_send(self, seq):
        waypoint = self.spabModel.Waypoints[seq]
        body_dict = {
            "msg_type": "waypoint_reached",
            "source_id": "spar1",
            "timestamp": self.spabModel.LastLocation["timestamp"],
            "latitude": waypoint[0],
            "longitude": waypoint[1],
            "temperature": -1,
            "salinity": -2
        }
        body = json.dumps(body_dict)
        length = len(body)
        req = """POST /solarboat/api/data.cgi HTTP/1.1
Host: therevproject.com
Accept: */*
Connection: close
Content-type: application/json
Content-Length: """
        req += str(length) + "\r\n\r\n"
        req += body + "\r\n\r\n"
        print(req)
        self.modem.send(req)

    def requestCommands(self):
        #print('request commands')
        """Requests new commands JSON from control server and registers a callback handler"""
        req = "GET http://therevproject.com/solarboat/api/command.cgi\r\n\r\n"
        print(req)
        self.modem.send(req)
        self.task.enter(self.PollingPeriod, 1, self.remoteTelemetry, ())

    def handleDataUploadResponse(self, uploadResponse):
        # This method should position/sample data being uploaded to the server
        print(uploadResponse)

    def handleCommandList(self, cmdList):
        print(cmdList)
        sorted_list = sorted(cmdList, key=lambda k: k['id'])
        #cmdList.sort(key="id")
        print(sorted_list)
        self.spabModel.pendingWaypoints = [(cmd["latitude"], cmd["longitude"]) for cmd in sorted_list]
        print(self.spabModel.pendingWaypoints)

    def handleCommandComplete(self, cmdCompleteResponse):
        # This method should command complete data being uploaded to the server
        print(cmdCompleteResponse)

    def HandleReceipt(self, sender, earg):
        # print(earg)
        s = earg.decode("utf-8")
        print(s)
        # deal with http headers
        lines = s.splitlines()
        if(lines[0] == "HTTP/1.1 200 OK"):
            s = lines[10]
        # deal with json
        try:
            respContent = json.loads(s)
            if respContent["type"] == "dataUpload":
                self.handleDataUploadResponse(respContent)
            elif respContent["type"] == "cmdList":
                self.handleCommandList(respContent["data"])
            elif respContent == "cmdComplete":
                self.handleCommandComplete(respContent)
        except Exception as e:
            print(str(e))

    def start(self):
        self.task.enter(self.PollingPeriod, 1, self.requestCommands, ())
        self.modem += self.HandleReceipt

    def stop(self):
        self.task.cancel(self.requestCommands)
        # self.task.cancel(self.remoteTelemetry)
        self.modem -= self.HandleReceipt
