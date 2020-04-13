#!/usr/bin/env python3

# Websockets server for GVG110 Etherenet Control Panel Testing
# Bsaed on WS server example at <https://websockets.readthedocs.io/en/stable/intro.html>
# For use with GVG110 control panel modified according to lebaston100's instructions
# and running the code at <https://github.com/lebaston100/GVG110panelMod/>

import asyncio
import websockets

async def hello(websocket, path):
    #uncomment this block to turn lamps on at boot for testing.
    #Enter the lamp IDs on the next line after "a:", separated by and terminated by :
    #lightson = "a:55:53:"
    #await websocket.send(lightson)
    #print(f"> {lightson}")

    helptext = "d:12:11:13:14:15:" #"H E L P" for LED display setting
    await websocket.send(helptext) #Set the LED display at start
    print(f"> {helptext}")

    while True:
        key = await websocket.recv()             #receive key and change information
        print(f"< {key}")                        #display the received information locally
        keyarray = key.split (":")               #split information by seperator, :
        if len(keyarray) > 1:                    #if there are any paramaters received
            keychar = ":".join(keyarray[1])      #select the first parameter and split it by :
            disp = "d:" + keychar + ":15:15:15:" #add blanks after it so we blank out any existing data
            await websocket.send(disp)           #and display it on the LED display
            print(f"> {disp}")                   #display the information sent locally

start_server = websockets.serve(hello, "0.0.0.0", 4242)   #listen on all interfaces on port 4242

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
