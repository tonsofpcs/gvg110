#!/usr/bin/env python3
#!/usr/bin/env python3
#gvg-obs.py  2020 Eric Adler
#based on gvg.py by lebaston100


import websocket, threading, json, time, socket
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
from tinydb import TinyDB, Query

db = TinyDB('gvg-bmd.json')
bttcmd = db.table('buttonCMD')
analogcmd = db.table('analogCMD')
configdb = db.table('config')

PGMled = [33, 35, 37, 39, 13, 15, 14, 12, 0, 2]
PRVled = [38, 36, 34, 32, 1, 3, 5, 7, 6, 4]
KEYled = [30, 28, 26, 24, 9, 8, 11, 10, 51, 53]

makroKeys = [8, 9, 10, 11, 12, 13, 14, 15, 34, 35]

toggle = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
maxinvert = 0

clients = []
display = [15, 15, 15, 0, 15]
analog = []

curPGM = 0
lastPGM = 0
curPRV = 0
lastPRV = 0

invertnext = 0

connstat = 0

Search = Query()
print (configdb)


#Events
def buttonOnEvent(button):
    print(button)
    Search = Query()
    result = bttcmd.search((Search.state == 1) & (Search.button == int(button)))
    if result:
        print(result)
        for line in result:
            bmdrequest = line["requestType"]
            bmddata = line["data"]
            if line["actionType"] == "bmd-atem":
                bmdsend(bmdrequest, bmddata)
    elif button in makroKeys:
        x = 1

def buttonOffEvent(button):
    print(button)

def analogEvent(address, value):
    global maxinvert
    if address == 2: #Tbar
        if value < 3:
            sendPanelMSG("b:46:")
            sendPanelMSG("a:47:")
            value = 0
        elif value > 1019:
            sendPanelMSG("a:46:")
            sendPanelMSG("b:47:")
            value = 1023
        else:
            sendPanelMSG("b:46:47:")
        if maxinvert:
            value = (value / 1023)
        else:
            value = 1-((value) / 1023)
        if value == 1:
            action = '{"request-type" : "ReleaseTBar", "message-id" : "3"}'
            maxinvert = not(maxinvert)
        elif value == 0:
            action = '{"request-type" : "ReleaseTBar", "message-id" : "3"}'
        else:
            action = '{"request-type" : "SetTBarPosition", "message-id" : "2", "position" : %s, "release" : false}' % value
        ws_client.send(action)
        #TODO: Code to set t-bar value


def setPRV(i):
    if i < 11:
        s = "b:"
        for index, v in enumerate(PRVled):
            if index != i-1:
                s += str(v)
                s += ":"
        sendPanelMSG("a:%s:" % str(PRVled[i-1]))
        sendPanelMSG(s)

def setPGM(i):
    if i < 11:
        s = "b:"
        for index, v in enumerate(PGMled):
            if index != i-1:
                s += str(v)
                s += ":"
        sendPanelMSG("a:%s:" % str(PGMled[i-1]))
        sendPanelMSG(s)

def setDSK(i, state):
    print("setDSK " + str(i) + ":" + str(state))
    if i < 11:
        if state:
            print("a:%s:" % str(KEYled[i-1]))
            sendPanelMSG("a:%s:" % str(KEYled[i-1]))
        else: 
            print("b:%s:" % str(KEYled[i-1]))
            sendPanelMSG("b:%s:" % str(KEYled[i-1]))


def updateDisplayValue(value):
    lenght = len(str(value))
    value = list(str(value))
    global display
    if lenght == 1:
        display[0] = 15
        display[1] = 15
        display[2] = 15
        display[3] = value[0]
    if lenght == 2:
        display[0] = 15
        display[1] = 15
        display[2] = value[0]
        display[3] = value[1]
    if lenght == 3:
        display[0] = 15
        display[1] = value[0]
        display[2] = value[1]
        display[3] = value[2]
    if lenght == 4:
        for i in range(0, 4):
            display[i] = value[i]
    setDisplay()


def setDisplay():
    s = "d:"
    for v in display:
        s += str(v)
        s += ":"
    sendPanelMSG(s)

def sendPanelMSG(data):
    for client in clients:
        if client[2] == 1:
            client[0].sendMessage(data)

def isSelf(self):
    stat = False
    for client in clients:
        if client[0] == self:
            stat = True
    return stat

#server stuff
class Server(WebSocket):
    def handleMessage(self):
        global display
##      print(self.data)
        split = self.data.split(":")
        print(split)
        if split[0] == "x":
            for client in clients:
                if client[0] == self:
                    copy = client
                    copy[2] = 1
                    clients.remove(client)
                    clients.append(copy)
                    print(client, "is now input")
                    display = [15, 15, 15, 0, 15]
                    setDisplay()
                    setPRV(1)
                    setPGM(1)
        if split[0] == "a":
            del split[0]
            for address in range(0, len(split), 2):
                analogEvent(int(split[address]), int(split[address + 1]))
            #analog
        elif split[0] == "b1":
            del split[0]
            for button in split:
                buttonOnEvent(button)
            #button on
        elif split[0] == "c1":
            del split[0]
            for button in split:
                buttonOffEvent(button)
            #button off
        for client in clients:
                if client[0] != self:
                    client[0].sendMessage(self.data)

    def handleConnected(self):
        global connstat
        print(self.address, 'connected')
        newClient = [self, self.address, 0]
        clients.append(newClient)
        #print(clients)
        if not(connstat):
            threading.Thread(target=client_start).start()

    def handleClose(self):
        for client in clients:
            if client[0] == self:
                clients.remove(client)
                break
        print(self.address, 'disconnected')

#client stuff
def bmdsend(command, data):


def server_start():
    #while True:
    server.serveforever()
    print("server restart")

def client_start():
    #while True:
    ws_client.run_forever() #()
    print("client restart")

if __name__ == "__main__":
    server = SimpleWebSocketServer('', 1234, Server)
    threading.Thread(target=server_start).start()
    threading.Thread(target=client_start).start()
