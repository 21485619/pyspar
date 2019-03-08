#!/usr/bin/python3
import json
import collections


class TelemManager:
    def __init__(self, Scheduler, model, Modem, TelemPeriod, SensorManager):
        self.task = Scheduler
        self.spabModel = model
        self.modem = Modem
        self.PollingPeriod = TelemPeriod
        self.sensor_manager = SensorManager
        self.AcceptedCommands = collections.deque(maxlen=10)
       
    def remoteTelemetry(self):
        if self.sensor_manager.pendingImage:
            self.image_telem()
            self.sensor_manager.pendingImage = False
        else:
            self.req_count = 0
            self.standard_telem()
        print('remote telemetry')
        
    def standard_telem(self)   
        body = json.dumps(self.spabModel.LastLocation)
        length = len(body)

        req = """POST /spab/data.cgi HTTP/1.1
Host: therevproject.com
Accept: */*
Connection: close
Content-type: application/json
Content-Length: """
        req += str(length) + "\n\n"
        req += body + "\r\n\r\n"
        print(req)
        self.modem.send(req)
        self.task.enter(self.PollingPeriod, 1, self.requestCommands, ())


    def image_telem(self):
        body = json.dumps(self.spabModel.LastLocation)
        length = len(body)

        req = """POST /spab/data.cgi HTTP/1.1
Host: therevproject.com
Accept: */*
Connection: close
Content-type: application/json
Content-Length: """
        req += str(length) + "\n\n"
        req += body + "\r\n\r\n"
        print(req)

        self.modem.send(req)
        self.task.enter(self.PollingPeriod, 1, self.requestCommands, ())


    def requestCommands(self):
        print('request commands')
        """Requests new commands JSON from control server and registers a callback handler"""
        req = "GET http://therevproject.com/spab/requestCommands.cgi\r\n\r\n"
        self.modem.send(req)
        self.task.enter(self.PollingPeriod, 1, self.remoteTelemetry, ())

    def HandleTelemAck(self, json):
        print(json[0]["message"])

    def HandleCommand(self, cmdList):
        print('handling commands')
        print(cmdList)
        for elem in cmdList:
            if(elem["taskId"] in self.AcceptedCommands):
                continue
            print(elem["action"])
            self.AcceptedCommands.append(elem["taskId"])
            self.spabModel.pendingWaypoints.append((float(elem["latitude"]), float(elem["longitude"])))
        print(self.spabModel.Waypoints)

    def HandleReceipt(self, sender, earg):
        s = earg.decode("utf-8")
        print(s)
        # deal with http headers
        lines = s.splitlines()
        if(lines[0] == "HTTP/1.1 200 OK"):
            s = lines[10]
        # deal with json
        try:
            data = json.loads(s)
            print(str(data))
            if(data[0]["type"] == "telemAck"):
                print("received telemAck")
                self.HandleTelemAck(data[1:])
            elif(data[0]["type"] == "command"):
                print("received command")
                self.HandleCommand(data[1:])
        except Exception as e:
            print(str(e))

    def start(self):
        self.task.enter(self.PollingPeriod, 1, self.requestCommands, ())
        self.modem += self.HandleReceipt

    def stop(self):
        self.task.cancel(self.requestCommands)
        # self.task.cancel(self.remoteTelemetry)
        self.modem -= self.HandleReceipt
