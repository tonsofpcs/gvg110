# gvg110
GVG110 Control Panel Testing

Current status:  GVG 110 controls OBS over ethernet through a third-party system.  LEDs track the "on-air" and preview sources.  


Notes and scripts that I've used for GVG110 Control panel computer interfacing and testing.

I've modified my control panel mostly based upon <http://www.lefflerpost.com.au/ATEM/gvg110%20panel%20mods.pdf>

I've connected an arduino and installed code on it from <https://github.com/lebaston100/GVG110panelMod/>

My control panel has known issues with the T-bar and with just this configuration described above, in testing, I intermittently receive key details on the websocket server (websockettest.py) but regularly received the key press / unpress commands without key details.  
After discussiong with lebaston100 and investigating I found a code issue.  I believe the changes in Arduino compiler have made it such that for loop initialization of variables is skipped unless a value is assigned or perhaps there's some change in how memory is mapped when variables are defined.  
In either case, setting the for loops to start with (int i=0; instead of (int i; makes it all happy.  
Fixed code was posted as a pull request against the original and merged in.  
