#!/usr/bin/env python3
#!/usr/bin/env python3
#gvg-bmd.py  2020 Eric Adler
#based on gvg.py by lebaston100


import websocket, threading, json, time, socket, datetime
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

obshost = configdb.all()[0].get("obshost")
obsport = configdb.all()[0].get("obsport")

bmdhost = configdb.all()[0].get("bmdhost")
bmdport = int(configdb.all()[0].get("bmdport"))
bmdclient_connected = 0
bmdinitialize = 0 #0 = nothing, 1 = sent, 2+ = online
bmdsessionid = b"\xD4\x31"
bmdremoteid = b"\x00\x00"
bmdpacketid = 255
bmdwaiting = 0
bmdinit = [0]*8
bmdlastsend = datetime.datetime

headercommands = {
    "0": 0,
    "SYN": 1,
    "HELLO": 2,
    "RESEND": 4,
    "REQUEST": 8,
    "ACK": 16,
    "inc": 26
}

def orlist(list1, list2):
    return [l1 | l2 for l1,l2 in zip(list1,list2)]

def andlist(list1, list2):
    return [l1 & l2 for l1,l2 in zip(list1,list2)]

def xorlist(list1, list2):
    return [l1 ^ l2 for l1,l2 in zip(list1,list2)]

def orbin(bin1, bin2):
    result = bytearray(bin1)
    for i, b in enumerate(bin2):
        result[i] |= b
    return bytes(result)

def andbin(bin1, bin2):
    result = bytearray(bin1)
    for i, b in enumerate(bin2):
        print(i, result[i], b)
        result[i] &= b
    return bytes(result)

def xorbin(bin1, bin2):
    result = bytearray(bin1)
    for i, b in enumerate(bin2):
        result[i] ^= b
    return bytes(result)

#Events
def buttonOnEvent(button):
    print("ButtonOnEvent")
    print(button)
    Search = Query()
    result = bttcmd.search((Search.state == 1) & (Search.button == int(button)))
    if result:
        print(result)
        for line in result:
            bmdrequest = (bytes(line["requestType"],'ascii'))
            print("bmdrequest:" , bmdrequest)
            bmddatalen = line["length"]
            print("bmddatalen:", bmddatalen)
            bmddata = line["data"].to_bytes(bmddatalen, byteorder='big')
            if line["actionType"] == "bmd-atem":
                bmdpush(bmdrequest, bmddata)
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
def bmdconnect():
    global bmdlastsend
    header = bmdheader(20, "HELLO", 0)
    data = b"\x00\x00\x00\x00\x00\x00\x00\x00\x3a\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00"
    bmdlastsend = datetime.datetime.now()
    sendmsg = header + data
    bmdsend(sendmsg)

def bmdrun():
    global bmdclient_connected
    global bmdwaiting
    global bmdlastsend
    global bmdinitialize

    if not(bmdclient_connected):
        bmdconnect()
    
    if not(bmdinitialize > 1) and not(bmdwaiting):
        for counter in range(64):
            if not(bmdinit[int(counter/8)]):
                sendmsg = bmdheader(12,"REQUEST",0) + b"\x00\x00\x00\x00\x00" + counter.to_bytes(2, byteorder='big') + b"\x01\x01\x01\x01\x01"
                bmdsend(sendmsg)
                bmdwaiting = 1
        if not(bmdwaiting):
            bmdinitialize = 2
            print("BMD Initialized")
    
    if ((datetime.datetime.now() - bmdlastsend).microseconds > 5000000): #5s past
        print("BMD Timed out")
        bmdconnect()

def bmd_listen():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', 51050))
    while True:
        data, addr = sock.recvfrom(1024)
        bmdreceive(data)

def bmdreceive(data):
    global bmdsessionid
    global bmdremoteid

    bmdsessionid = data[2:4]
    bmdremoteid = data[10:12]
    if len(data) > 12:
        data = data[12:]
        #while len(data) >= 8:
        dataitem = data[:8]
        data = data[8:]
        commandlength = int(dataitem[0:2])
        command = dataitem[4:8] + b"\x00"
        bmdcommand(command)

def bmdcommand(command):
    #TODO: Handle HELLO packet responses and some other things.  Maybe update the timeouts on receive too?
    if (command[0] == bmdheader.get("HELLO")):
        bmdpush("ACK","\x00\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00")
    print("Received command ", command)

def bmdheader(datalength, command, remoteid):
    #return b"\x08\x18\x80\x02\x00\x00\x00\x00\x00\x00\x2b\xcb\x00\x0c\x00\x00"
    print("bmdheader")
    global bmdsessionid
    global bmdpacketid
    global bmdremoteid

    command = headercommands.get(command)
    print("bmdheader: command = ", command)
    testcmd = command.to_bytes(1, byteorder='big')
    print("bmdheader: testcmd = ", testcmd)
    
    commandshift = command * 2048

    if (andbin(headercommands.get("inc").to_bytes(1, byteorder='big'), testcmd) == b"\x00"):
        bmdpacketid += 1
        print("bmdheader: packetid = ", bmdpacketid)
        if(bmdpacketid > 255): bmdpacketid = 0
        header = orbin(andbin(datalength.to_bytes(2, byteorder='big'), b"\x07\x00"), commandshift.to_bytes(2, byteorder='big')) + bmdsessionid + bmdremoteid + bytes(4) + bmdpacketid.to_bytes(2, byteorder='big')
    else:
        print("bmdheader: packetid = ", bmdpacketid)
        header = orbin(andbin(datalength.to_bytes(2, byteorder='big'), b"\x07\x00"), commandshift.to_bytes(2, byteorder='big')) + bmdsessionid + bmdremoteid + bytes(6)
    print("bmdheader: result:", header)

    return header

def bmdsend(message):
    print("bmdsend:", message)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', 51050))
    sock.sendto(message, (bmdhost, bmdport))

def bmdpush(command, data):
    print("bmdpush")
    header = bmdheader(len(data),"0",0)
    print("Header: ", header)
    sendmsg = header + command + data
    bmdsend(sendmsg)
    
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
    threading.Thread(target=bmd_listen).start()
    bmdrun()