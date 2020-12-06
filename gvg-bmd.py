#!/usr/bin/env python3
#!/usr/bin/env python3
#gvg-bmd.py  2020 Eric Adler
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

bmdhost = configdb.all()[0].get("bmdhost")
bmdport = int(configdb.all()[0].get("bmdport"))
obshost = configdb.all()[0].get("obshost")
obsport = configdb.all()[0].get("obsport")


#Events
def buttonOnEvent(button):
    print("ButtonOnEvent")
    print(button)
    Search = Query()
    result = bttcmd.search((Search.state == 1) & (Search.button == int(button)))
    if result:
        print(result)
        for line in result:
            bmdrequest = bytes(line["requestType"],'ascii')
            bmddatalen = line["length"]
            bmddata = line["data"].to_bytes(bmddatalen)
            print("BMD Data: %s" % bmddata)
            if line["actionType"] == "bmd-atem":
                bmdsend(bmdrequest, bmddata)
    elif button in makroKeys:
        x = 1

def buttonOffEvent(button):
    print("ButtonOffEvent")
    print(button)

def analogEvent(address, value):
    print("analogEvent")
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
        #TODO: Code to set t-bar value
    print("a")


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
    print("updateDisplayValue")
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
    print("setDisplay")
    s = "d:"
    for v in display:
        s += str(v)
        s += ":"
    sendPanelMSG(s)

def sendPanelMSG(data):
    print("sendPanelMSG")
    for client in clients:
        if client[2] == 1:
            client[0].sendMessage(data)

def isSelf(self):
    print("isSelf")
    stat = False
    for client in clients:
        if client[0] == self:
            stat = True
    return stat

#server stuff
class Server(WebSocket):
    def handleMessage(self):
        print("handleMessage")
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
        print(self.address, 'connected')
        newClient = [self, self.address, 0]
        clients.append(newClient)
        #print(clients)

    def handleClose(self):
        print("handleClose")
        for client in clients:
            if client[0] == self:
                clients.remove(client)
                break
        print(self.address, 'disconnected')

#client stuff
def bmdsend(command, data):
    print("bmdsend")
    sendmsg = command + data
    print(sendmsg)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(sendmsg, (bmdhost, bmdport))

def ws_client_on_message(ws, message):
    print("ws_client_on_message")
    jsn = json.loads(message)
    if "update-type" in jsn:
        if jsn["update-type"] == "PreviewSceneChanged":
            index = 12
            try:
                index = sceneNames.index(jsn["scene-name"])
            except:
                pass
            setPRV(index + 1)
        elif jsn["update-type"] == "SceneItemVisibilityChanged":
            print(jsn)
            if (jsn["scene-name"] == keyer) or (jsn["scene-name"] == keyer2):
                index = 12
                try:
                    index = keyNames.index(jsn["item-name"])
                    state = bool(jsn["item-visible"])
                except:
                    pass
            setDSK(index + 1, state)
        # elif jsn["update-type"] == "SceneItemTransformChanged":
        #     print(jsn)
        #     if jsn["scene-name"] == keyer:
        #         index = 12
        #         try:
        #             index = keyNames.index(jsn["item-name"])
        #             state = bool(jsn["visible"])
        #         except:
        #             pass
        #     setDSK(index + 1, state)
        elif jsn["update-type"] == "SwitchScenes":
            index = 12
            try:
                index = sceneNames.index(jsn["scene-name"])
            except:
                pass
            updateDisplayValue(index + 1)
            setPGM(index + 1)
        elif jsn["update-type"] == "SwitchTransition":
            if jsn["transition-name"] == "Cut":
                sendPanelMSG("b:50:52:54:48:49:")
            elif jsn["transition-name"] == "Fade":
                sendPanelMSG("a:54:")
                sendPanelMSG("b:50:52:48:49:")
            elif jsn["transition-name"] == "Slide":
                sendPanelMSG("a:52:")
                sendPanelMSG("b:50:54:48:49:")
            elif jsn["transition-name"] == "Stinger":
                sendPanelMSG("a:48:50:")
                sendPanelMSG("b:52:49:54:")
            elif jsn["transition-name"] == "Woosh":
                sendPanelMSG("a:49:50:")
                sendPanelMSG("b:52:54:48:")
        print(jsn)

def server_start():
    print("server start")
    #while True:
    server.serveforever()
    print("server restart")

if __name__ == "__main__":
    server = SimpleWebSocketServer('', 1234, Server)
    threading.Thread(target=server_start).start()
