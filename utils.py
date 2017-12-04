### Utilitary Functions/Classes

import time
from enum import Enum

DEBUG_SET = []
simlog = open("simlog" + time.strftime("%H%M%S") + ".log", "w")

def dprint(*text, objn=0):
    if(objn is 0 or objn in DEBUG_SET):
        print("[", time.strftime("%H:%M:%S"),"]:", end="", file=simlog)
        for t in text:
            print("", t, end="", file=simlog)
        print("", file=simlog)

# Enums:

class Event_Type(Enum):
    TG_SentPacket = 1           #
    AN_Started = 2              #
    AN_Ended = 3                #
    ANT_SentPacket = 4          #
    DBA_SentGrant = 5
    DBA_Killed = 6
    DBA_DiscardedRequest = 7
    DBA_Created_VPON = 8
    PN_ReceivedObject = 9
    SPLT_ReceivedObject = 10
    ONU_SentRequest = 11

class End_Sim(Enum):
    ByRequestCount = 1
    ByTimeCount = 2
    ByGrantCount = 3