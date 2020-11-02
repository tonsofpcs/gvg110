#!/usr/bin/env python3
#gvg-carbonite.py  2020 Eric Adler
#based on gvg.py by lebaston100

import websocket, threading, json, time, socket, sys
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
from tinydb import TinyDB, Query

carbonite_host = '192.168.1.43'
carbonite_port = 7788
listen_port = 1234

db = TinyDB('gvg-carbonite.json')
bttcmd = db.table('buttonCMD')
analogcmd = db.table('analogCMD')

PGMbtn = [16, 17, 18, 19, 20, 21, 22, 23, 32, 33]
PVWbtn = [24, 25, 26, 27, 28, 29, 30, 31, 36, 37]
KEYbtn = [8, 9, 10, 11, 12, 13, 14, 15, 34, 35]
BTNLEDmap = [[16, 17, 18, 19, 20, 21, 22, 23, 32, 33, 24, 25, 26, 27, 28, 29, 30, 31, 36, 37, 8, 9, 10, 11, 12, 13, 14, 15, 34, 35],
        [33, 35, 37, 39, 13, 15, 14, 12,  0, 2, 38, 36, 34, 32, 1, 3, 5, 7, 6 , 4, 30, 28, 26, 24, 9, 8, 11, 10, 51, 53]]
PGMled = [33, 35, 37, 39, 13, 15, 14, 12, 0, 2]
PVWled = [38, 36, 34, 32, 1, 3, 5, 7, 6, 4]
KEYled = [30, 28, 26, 24, 9, 8, 11, 10, 51, 53]

clients = []
display = [15, 15, 15, 0, 15]
analog = []

curPGM = 0
lastPGM = 0
curPVW = 0
lastPVW = 0

sockconnected = False
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

#vent stuff
def buttonOnEvent(button):
    print(button)
    Search = Query()
    result = bttcmd.search(Search.button == int(button))
    print(result)
    if result:
        for line in result:
            print(line["action"])
            if ((line["action"][0:6] == "MEAUTO") or (line["action"][0:5] == "MECUT")):
                buslampswitch(curPGM,curPVW)
            sock.send(bytes((line["action"] + '\n'),'ascii'))
            print("socket sent")
    #elif button in makroKeys:
    #    x = 1
    #    #Makros
    try: 
        val = BTNLEDmap[0].index(int(button))
        buslampone(BTNLEDmap[1][val])
        print("current " + str(curPGM) + str(curPVW))
    except:
        pass


def buslampone(led):
    global curPGM
    global curPVW
    try:
        val = PGMled.index(led)
        sendPanelMSG("b:" + ':'.join(map(str,PGMled)) + ":")
        sendPanelMSG("a:" + str(led) + ":")
        curPGM = led
        print("cur PGM : " + str(curPGM))
        print("cur PVW : " + str(curPVW))
    except:
        pass
    try:
        val = PVWled.index(led)
        sendPanelMSG("b:" + ':'.join(map(str,PVWled)) + ":")
        sendPanelMSG("a:" + str(led) + ":")
        curPVW = led
        print("cur PGM : " + str(curPGM))
        print("cur PVW : " + str(curPVW))
    except:
        pass
    try:
        val = KEYled.index(led)
        sendPanelMSG("b:" + ':'.join(map(str,KEYled)) + ":")
        sendPanelMSG("a:" + str(led) + ":")
    except:
        pass

def buslampswitch(PGMcur,PVWcur):
    global curPGM
    global curPVW
    print(str(PGMcur) + " switch " + str(PVWcur))
    try:
        val = PGMled.index(PGMcur)
        sendPanelMSG("b:" + ':'.join(map(str,PVWled)) + ":")
        sendPanelMSG("a:" + str(PVWled[val]) + ":")
        curPVW = PVWled[val]
    except:
        pass
    try:
        val = PVWled.index(PVWcur)
        sendPanelMSG("b:" + ':'.join(map(str,PGMled)) + ":")
        sendPanelMSG("a:" + str(PGMled[val]) + ":")
        curPGM = PGMled[val]
    except:
        pass
    print(str(curPGM) + " now " + str(curPVW))

    
def buttonOffEvent(button):
    print(button)

def analogEvent(address, value):
    print(address, value)
    if address == 2: #Tbar
        if value < 3:
            sendPanelMSG("b:46:")
            sendPanelMSG("a:47:")
        elif value > 1019:
            sendPanelMSG("a:46:")
            sendPanelMSG("b:47:")
        else:
            sendPanelMSG("b:46:47:")
    
def setKEY(i):
    if i < 11:
        s = "b:"
        for index, v in enumerate(KEYled):
            if index != i-1:
                s += str(v)
                s += ":"
        sendPanelMSG("a:%s:" % str(KEYled[i-1])) 
        sendPanelMSG(s)
    
def setPVW(i):
    if i < 11:
        s = "b:"
        for index, v in enumerate(PVWled):
            if index != i-1:
                s += str(v)
                s += ":"        
        sendPanelMSG("a:%s:" % str(PVWled[i-1]))
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
                    setPVW(1)
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
        for client in clients:
            if client[0] == self:
                clients.remove(client)
                break
        print(self.address, 'disconnected')

def server_start():
    #while True:
    server.serveforever()
    print("server restart")

def client_start():
    print('connect %s : %s' % server_address, file=sys.stderr)
    sock.connect(server_address)
    time.sleep(2)
    #result = sock.send(bytes("SEND MESSAGE", 'ascii'))
    #print("result " + str(result))
    #    data = sock.recv(16)
    #    print(data, end = '')
    print("client restart")

if __name__ == "__main__":
    server = SimpleWebSocketServer('', listen_port, Server)
    threading.Thread(target=server_start).start()
    server_address = (carbonite_host, carbonite_port)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #sock.bind(server_address)
    threading.Thread(target=client_start).start()

    #TODO: SET UP TCP CLIENT TO SEND ROSSTALK COMMANDS

