from utils import *
class gameSession:
    isDebug = False
    targetX = targetY = navCenter = 0
    isAligned = isFocused = False
    stateList = []
    journal = []
    missionList = []
    guiFocus = 'NoFocus'
    status = ''
    shipLoc = ''
    shipTarget = ''

    def __init__(self,gameName=globalWindowName,name=None,debug=False):
        if name is None: self.name='Session 1'
        else: self.name = name
        self.shmName = 'shm_'+self.name
        self.isDebug = debug
        if self.isDebug :
            print("Now Creating SharedMemory Block...")
        try:
            sharedMem,coordArray = createSharedCoordsBlock(name=self.shmName)
            if sharedMem is not None:
                self.shmCoord = sharedMem
                self.shmCoordArray = coordArray
        except:
            traceback.print_exc() # TODO: Implement it with LOGGER API
        if self.isDebug:
            print('SharedMemory Block Created:',self.shmCoord.name)
        try:
            self.eventQueue = Queue(maxsize=1)
            self.eventProcess = Process(target=eventsHandler,args=(self.eventQueue,))
            self.imageProcess = Process(target=imageProcessing,args=(self.shmCoord.name,))
            self.eventProcess.daemon = True
            self.imageProcess.daemon = True
            self.imageProcess.start()
            self.eventProcess.start()
        except:
            traceback.print_exc()
        if self.isDebug:
            print('Image and Event Processes Started')
        self.update()
    
    def update(self, full=True): # 从io和图像处理模块读取数据
        self.targetX,self.targetY,self.navCenter,self.isAligned,self.isFocused = self.shmCoordArray
        if full: # do full update
            self.journal = setJournal()
            self.stateList = showAllTrueStatus()
            self.guiFocus = getGuiFocus()
            self.status = self.journal['status']
            self.shipLoc = self.journal['location']
            self.shipTarget = self.journal['target']
            self.missionList = self.journal['missions']

    def sendKey(self,key, hold=None, repeat=1, repeat_delay=None, state=None, block=False):
        keyStruct = 'KEY',key,hold,repeat,repeat_delay,state
        self.eventQueue.put(keyStruct)
        if block and hold is not None: 
            self.sleep(hold)
            self.update()
        return key
    
    def sendDelay(self,delay,block=False):
        keyStruct = 'DELAY',delay
        self.eventQueue.put(keyStruct)
        if block: 
            self.sleep(delay)
            self.update()
        return delay
    
    def sleep(self, delay, updateDelay=SLEEP_UPDATE_DELAY):
        nowTime = time.time()
        endTime = nowTime+delay
        updateTime = nowTime+updateDelay
        keyStruct = 'DELAY',delay
        self.eventQueue.put(keyStruct)
        while nowTime<endTime: # new "blockless update" sleep method
            nowTime = time.time()
            if nowTime>=updateTime: # should update
                self.update()
                updateTime += updateDelay
        self.update()

    def align(self,update=False): # 基本只靠 Template Matching
        if update: self.update() # 调用一次update，因此align(self)应该在while循环内调用，这里默认为在外部循环中已经update，整个while只需要一次update，减少io
        if self.targetX == -1 or self.targetY == -1 : return True # 有时候会停着不动= =
        if self.isAligned == 1 or self.isFocused == 0: return False
        offsetX = abs(self.targetX-self.navCenter)
        offsetY = abs(self.targetY-self.navCenter)
        # if offsetX<0.2 and offsetY<0.2: return False # magic number: minimum range for SimpleBlobDetector
        if self.eventQueue.empty():
            trimX = trimY = 0.0
            if offsetX<3: trimX = ALIGN_TRIMM_DELAY
            if offsetY<3: trimY = ALIGN_TRIMM_DELAY
            if offsetY>ALIGN_DEAD_ZONE:
                if self.targetY<self.navCenter: self.sendKey('PitchUpButton',hold=KEY_DEFAULT_DELAY-trimY)
                else : self.sendKey('PitchDownButton',hold=KEY_DEFAULT_DELAY-trimY)
            elif offsetX>ALIGN_DEAD_ZONE: # elif 使得在两轴坐标都大于死区时先校准Y轴（Python的Pitch轴俯仰较为灵敏）
                if self.targetX>self.navCenter: self.sendKey('YawRightButton',hold=KEY_DEFAULT_DELAY-trimX)
                else : self.sendKey('YawLeftButton',hold=KEY_DEFAULT_DELAY-trimX)
        return True

    def sunAvoiding(self,fwdDelay=18,turnDelay=12): # Only do it once in a loop!
        self.sendKey('SpeedZero')
        self.sendDelay(2,block=True)
        self.sendKey('PitchUpButton',hold=turnDelay,block=True)
        self.sendKey('Speed100')
        self.sendDelay(fwdDelay,block=True)
        self.sendKey('SpeedZero')
        return False
    
    def stop(self):
        self.shmCoord.close()
        self.shmCoord.unlink()
        if self.isDebug:
            print('SharedMemory Block Successfully Closed and Unlinked')
        self.imageProcess.terminate()
        self.eventProcess.terminate()
