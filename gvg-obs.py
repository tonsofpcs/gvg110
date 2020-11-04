#!/usr/bin/env python3
#!/usr/bin/env python3
#gvg-obs.py  2020 Eric Adler
#based on gvg.py by lebaston100


import websocket, threading, json, time
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
from tinydb import TinyDB, Query

db = TinyDB('gvg-obs.json')
bttcmd = db.table('buttonCMD')
analogcmd = db.table('analogCMD')

PGMled = [33, 35, 37, 39, 13, 15, 14, 12, 0, 2]
PRVled = [38, 36, 34, 32, 1, 3, 5, 7, 6, 4]
KEYled = [30, 28, 26, 24, 9, 8, 11, 10, 51, 53]

makroKeys = [8, 9, 10, 11, 12, 13, 14, 15, 34, 35]

sceneNames = ["src 1", "src 2", "src 3", "src 4", "src 5", "src 6", "src 7", "src 8", "src 9", "src 10"]
keyNames = ["key 1", "key 2", "key 3", "key 4", "key 5", "key 6", "key 7", "key 8", "key 9", "key 10"]
keyer = "keyA"
toggle = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

clients = []
display = [15, 15, 15, 0, 15]
analog = []

curPGM = 0
lastPGM = 0
curPRV = 0
lastPRV = 0

#Events
def buttonOnEvent(button):
    print(button)
    Search = Query()
    result = bttcmd.search((Search.state == 1) & (Search.button == int(button)))
    if result:
        print(result)
        for line in result:
            print(line["action"])
            action = line["action"]
            action = action.replace("$keyer$", keyer)
            if line["toggle"] >= 0:
                toggleit = int(line["toggle"])
                toggle[toggleit] = not(toggle[toggleit])
                action = action.replace("$toggle$",str(toggle[toggleit]).lower())
            print(line["actionType"])
            if line["actionType"] == "obs-ws":
                print("sending action: " + action)
                ws_client.send(action)
                print("action sent")
            print("post-do action: " + action)
    elif button in makroKeys:
        x = 1

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

#client stuff
def ws_client_on_message(ws, message):
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
            if jsn["scene-name"] == keyer:
                index = 12
                try:
                    index = keyNames.index(jsn["item-name"])
                    state = bool(jsn["item-visible"])
                except:
                    pass
            setDSK(index + 1, state)
        elif jsn["update-type"] == "SceneItemTransformChanged":
            print(jsn)
            if jsn["scene-name"] == keyer:
                index = 12
                try:
                    index = keyNames.index(jsn["item-name"])
                    state = bool(jsn["visible"])
                except:
                    pass
            setDSK(index + 1, state)
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
                sendPanelMSG("a:50:")
                sendPanelMSG("b:52:54:48:49:")
            elif jsn["transition-name"] == "Slide":
                sendPanelMSG("a:52:")
                sendPanelMSG("b:50:54:48:49:")
            elif jsn["transition-name"] == "Stinger":
                sendPanelMSG("a:54:")
                sendPanelMSG("b:50:52:48:49:")
            elif jsn["transition-name"] == "Whoosh":
                sendPanelMSG("a:48:")
                sendPanelMSG("b:50:52:54:49:")
            elif jsn["transition-name"] == "Woosh":
                sendPanelMSG("a:49:")
                sendPanelMSG("b:50:52:54:48:")
        print(jsn)

def ws_client_on_error(ws, error):
    print(error)

def ws_client_on_close(ws):
    print("### ws_client closed ###")

def ws_client_on_open(ws):
    print("### ws_client opened ###")

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
    ws_client = websocket.WebSocketApp("ws://192.168.1.158:4444", on_message = ws_client_on_message, on_error = ws_client_on_error, on_close = ws_client_on_close)
    ws_client.on_open = ws_client_on_open
    threading.Thread(target=client_start).start()
