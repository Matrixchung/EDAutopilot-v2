from utils import *
import transitions
isDebug = True
class gameSession:

    targetX = targetY = navCenter = 0
    isAligned = isFocused = False
    stateList = []
    journal = []
    status = ''
    guiFocus = 'NoFocus'
    shipLoc = ''
    shipTarget = ''

    def __init__(self,gameName=globalWindowName,name=None):
        if name is None: self.name='Session 1'
        else: self.name = name
        self.shmName = 'shm_'+self.name
        if isDebug :
            print("Now Creating SharedMemory Block...")
        try:
            sharedMem,coordArray = createSharedCoordsBlock(name=self.shmName)
            if sharedMem is not None:
                self.shmCoord = sharedMem
                self.shmCoordArray = coordArray
        except:
            traceback.print_exc() # TODO: Implement it with LOGGER API
        if isDebug:
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
        if isDebug:
            print('Image and Event Processes Started')
        self.update()
    
    def update(self): # 从io和图像处理模块读取数据
        self.targetX,self.targetY,self.navCenter,self.isAligned,self.isFocused = self.shmCoordArray
        self.journal = setJournal()
        self.stateList = showAllTrueStatus()
        self.guiFocus = getGuiFocus()
        self.status = self.journal['status']
        self.shipLoc = self.journal['location']
        self.shipTarget = self.journal['target']

    def sendKey(self,key, hold=None, repeat=1, repeat_delay=None, state=None):
        keyStruct = 'KEY',key,hold,repeat,repeat_delay,state
        self.eventQueue.put(keyStruct)
        return key
    
    def sendDelay(self,delay):
        keyStruct = 'DELAY',delay
        self.eventQueue.put(keyStruct)
        return delay

    def align(self,update=False):
        if update : self.update() # 调用一次update，因此align(self)应该在while循环内调用，这里默认为在外部循环中已经update，整个while只需要一次update，减少io
        if self.isAligned == 1 or self.isFocused == 0: return False
        offsetX = abs(self.targetX-self.navCenter)
        offsetY = abs(self.targetY-self.navCenter)
        if offsetX<0.2 and offsetY<0.2: return False # magic number: minimum range for SimpleBlobDetector
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

    def stop(self):
        self.shmCoord.close()
        self.shmCoord.unlink()
        if isDebug:
            print('SharedMemory Block Successfully Closed and Unlinked')
        self.imageProcess.terminate()
        self.eventProcess.terminate()

if __name__ == '__main__': # Test
    session = gameSession()
    align = False
    auto = False
    if isDebug:
        statusImg = np.zeros((300,1200,3),np.uint8)
    while not keyboard.is_pressed('p'):
        session.update()
        # 输入区
        if keyboard.is_pressed('o'): align = True
        if keyboard.is_pressed('home'): auto = True
        # 功能区
        if auto:
            pass
        if align: align = session.align()
        if isDebug:
            cv2.putText(statusImg,'GUIFocus:%s'%session.guiFocus,(10,30),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
            cv2.putText(statusImg,"align:%s"%session.isAligned,(400,30),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
            cv2.putText(statusImg,'state:%s'%session.stateList,(10,60),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
            cv2.putText(statusImg,'Status:%s'%session.status,(10,90),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
            cv2.putText(statusImg,'Loc:%s'%session.shipLoc,(310,90),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
            cv2.putText(statusImg,'Target:%s'%session.shipTarget,(700,90),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
            # cv2.putText(statusImg,'remainJumps:%s'%remainJumps,(10,120),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
            cv2.imshow("status",statusImg)
            statusImg.fill(0)
            cv2.waitKey(1)
    session.stop()

        