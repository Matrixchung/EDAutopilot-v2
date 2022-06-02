import time
from dataclasses import dataclass
from collections import Counter
from utils.utils import sendHexKey,getKeys,Journal,ALIGN_DEAD_ZONE,ALIGN_KEY_DELAY,ALIGN_TRIMM_DELAY
@dataclass
class ScriptInputMsg:
    isAligned: bool
    isFocused: bool
    stateList: list
    journal: Journal
    guiFocus: str
    targetX: int
    targetY: int
    navCenter: int
    windowLeftX: int
    windowTopY: int
class ScriptSession: # will be initialized in ScriptThread
    # _inSignal = Signal(object)
    # _outSignal = Signal(object)
    targetX = targetY = navCenter = 0
    isAligned = isFocused = False
    stateList = []
    journal = []
    missions = []
    guiFocus = 'NoFocus'
    status = ''
    shipLoc = ''
    shipTarget = ''
    windowCoord = (0,0)
    def __init__(self,logger=None,keysDict:dict=None):
        self.logger = logger
        self.keysDict = keysDict
    def _update(self,data:ScriptInputMsg):
        self.isAligned = data.isAligned
        self.isFocused = data.isFocused
        self.stateList = data.stateList
        self.journal = data.journal
        self.guiFocus = data.guiFocus
        self.targetX = data.targetX
        self.targetY = data.targetY
        self.navCenter = data.navCenter
        self.windowCoord = (data.windowLeftX,data.windowTopY)
        self.status = self.journal.status
        self.shipLoc = self.journal.nav.location
        self.shipTarget = self.journal.nav.target
        self.missions = self.journal.missions
    
    def sendKey(self, key, hold=None, repeat=1, repeat_delay=None, state=None):
        sendHexKey(self.keysDict,key,hold=hold,repeat=repeat,repeat_delay=repeat_delay,state=state)
    def sleep(self,delay):
        time.sleep(delay)
    def align(self) -> bool : # return False if already aligned
        if self.targetX == -1 or self.targetY == -1 : return True # 
        if self.isAligned == 1 or self.isFocused == 0: return False
        offsetX = abs(self.targetX-self.navCenter)
        offsetY = abs(self.targetY-self.navCenter)
        # if offsetX<0.2 and offsetY<0.2: return False # magic number: minimum range for SimpleBlobDetector
        trimX = trimY = 0.0
        if offsetX<3: trimX = ALIGN_TRIMM_DELAY
        if offsetY<3: trimY = ALIGN_TRIMM_DELAY
        if offsetY>ALIGN_DEAD_ZONE:
            if self.targetY<self.navCenter: self.sendKey('PitchUpButton',hold=ALIGN_KEY_DELAY-trimY)
            else : self.sendKey('PitchDownButton',hold=ALIGN_KEY_DELAY-trimY)
        elif offsetX>ALIGN_DEAD_ZONE: # align Y-Axis first
            if self.targetX>self.navCenter: self.sendKey('YawRightButton',hold=ALIGN_KEY_DELAY-trimX)
            else : self.sendKey('YawLeftButton',hold=ALIGN_KEY_DELAY-trimX)
        return True
    def sunAvoiding(self,fwdDelay=18,turnDelay=12):
        self.sendKey('SpeedZero')
        self.sleep(2)
        self.sendKey('PitchUpButton',hold=turnDelay)
        self.sendKey('Speed100')
        self.sleep(fwdDelay)
        self.sendKey('SpeedZero')
    ## Navigation
    def getRouteFromTo(self,start:str,to:str) -> list:
        pass
    def setRoute(self,dest:str) -> bool:
        pass
    def startRoute(self) -> bool: # start a new RouteAssist thread (using statemachine for multi-star route)
        pass
    def jump(self,estimatedTarget=None) -> bool: # if current target != estimated target then the jumping won't be performed
        pass
    def isEnRoute(self) -> bool:
        pass
    def stopRoute(self,force=False) -> bool:
        pass
    def getRouteDetails(self) -> dict:
        pass
    ## PIP Managements
    def pipReset(self):
        self.sendKey('PipDown')
    def pipSet(self,system,engine,weapon) -> bool:
        """
        patterns: 

        4-2-0 (4 twice, 2 once, 4 once)

        4-1-1 (4 twice)

        3-0-3 (each 3 twice)

        3-1.5-1.5 (3 once)

        3.5-2-0.5 (3.5 twice, 2 once)

        2.5-2.5-1 (each 2.5 press once)

        """
        if engine+system+weapon!=6 : return False # Illegal argument
        self.pipReset()
        pipDict = {"PipLeft": system, "PipUp": engine, "PipRight": weapon}
        c = Counter(pipDict.values())
        if c == Counter([4,2,0]): # pattern 1
            key_4 = getKeys(pipDict,4)[0] # key that need to be clicked 3 times
            self.sendKey(key_4,repeat=2)
            self.sendKey(getKeys(pipDict,2)[0])
            self.sendKey(key_4)
        elif c == Counter([4,1,1]): # pattern 2
            self.sendKey(getKeys(pipDict,4)[0],repeat=2)
        elif c == Counter([3,0,3]): # pattern 3
            for key in getKeys(pipDict,3): self.sendKey(key,repeat=2)
        elif c == Counter([3,1.5,1.5]): # pattern 4
            self.sendKey(getKeys(pipDict,3)[0])
        elif c == Counter([3.5,2,0.5]): # pattern 5
            self.sendKey(getKeys(pipDict,3.5)[0],repeat=2)
            self.sendKey(getKeys(pipDict,2)[0])
        elif c == Counter([2.5,2.5,1]): # pattern 6
            for key in getKeys(pipDict,2.5): self.sendKey(key)
        else: return False
        return True