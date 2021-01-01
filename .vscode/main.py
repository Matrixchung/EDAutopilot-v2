from utils import *
pyautogui.PAUSE = 1
pyautogui.FAILSAFE = True
compassX = compassY = compassRadius = 0
targetX = targetY = targetDrawRadius = 0
outsideOffsetY = 0
autoAlign = False
alignment = False

capturingQueue = JoinableQueue(maxsize=3)
eventsQueue=Queue(maxsize=2)

## State Machine
class shipState(object):
    def on_enter_sunavoiding(self):
        sendKey(eventsQueue,'SpeedZero')
        sendKey(eventsQueue,'PitchUpButton',repeat=13)
    def on_enter_hyperspace(self):
        sendKey(eventsQueue,'SpeedZero') # Auto dethrottle
model = shipState()
states=[
    'initial',
    'normal',
    'supercruise',
    'hyperspace',
    'docking',
    'docked',
    'undocking',
    'sunavoiding'
]
transitions= [
    {'trigger': 'startInSpace','source':'initial','dest':'normal'},
    {'trigger': 'startInDock','source':'initial','dest':'docked'},
    {'trigger': 'quit','source':'*','dest':'initial'},
    {'trigger': 'normalToSc','source':'normal','dest':'supercruise'},
    {'trigger': 'normalToDock','source':'normal','dest':'docking'},
    {'trigger': 'dockComplete','source':'docking','dest':'docked'},
    {'trigger': 'undock','source':'docked','dest':'undocking'},
    {'trigger': 'scToNormal','source':'supercruise','dest':'normal'},
    {'trigger': 'jump','source':['supercruise','normal'],'dest':'hyperspace'},
    {'trigger': 'sunAvoid','source':'supercruise','dest':'sunavoiding'},
    {'trigger': 'jumpComplete','source':'hyperspace','dest':'supercruise'}
]
machine = Machine(model=model, states=states, transitions=transitions, initial='initial')

if __name__ == "__main__":
    # cv2.namedWindow('hsv')
    # cv2.createTrackbar('lowH','hsv',0,179,callback)
    # cv2.createTrackbar('lowS','hsv',0,254,callback)
    # cv2.createTrackbar('lowV','hsv',0,254,callback)

    # cv2.createTrackbar('upH','hsv',0,179,callback)
    # cv2.createTrackbar('upS','hsv',0,254,callback)
    # cv2.createTrackbar('upV','hsv',0,254,callback)
    c1=Process(target=eventsHandler,args=(eventsQueue,)) # Initialize Events Handler
    c2=Process(target=screenCapture,args=(capturingQueue,))
    c1.daemon=True
    c2.daemon=True
    c2.start()
    c1.start()
    destCircleImg = cv2.imread("templates/dest_circle.png",0)
    navCircleImg = cv2.imread("templates/1.png",0)
    isFocused = False

    while True: 
        (gameCoord,img,isFocused)=capturingQueue.get() # Async Capturing
        gameResolution = gameCoord[2],gameCoord[3]
        gameCenterActual = gameCoord[0]+gameCoord[2]/2,gameCoord[1]+gameCoord[3]/2 # 绝对中点 用于鼠标操作
        gameCenterRel = gameCoord[2]/2,gameCoord[3]/2 # 相对中点
        outsideOffsetY = (gameCoord[3]/3)*2
        cv2OriginImg = cv2.cvtColor(np.asarray(img),cv2.COLOR_RGB2BGR)
        cv2ShowImg = cv2OriginImg.copy() # ShowImg for Overlay
        cv2img = cv2.cvtColor(cv2OriginImg,cv2.COLOR_BGR2GRAY)
        centerImg = cv2img[int(gameCenterRel[1]-180):int(gameCenterRel[1]+180),int(gameCenterRel[0]-220):int(gameCenterRel[0]+220)]
        compassImg = cv2img[int(gameResolution[1]/1.63):int(gameResolution[1]/1.06),int(gameResolution[0]/4.04):int(gameResolution[0]/2.02)] # Magic Number: size for compass img
        
        compassOriginImg = cv2OriginImg[int(gameResolution[1]/1.63):int(gameResolution[1]/1.06),int(gameResolution[0]/4.04):int(gameResolution[0]/2.02)]
        compassHsv = cv2.cvtColor(compassOriginImg,cv2.COLOR_BGR2HSV)
        compassShowImg = compassOriginImg.copy() # 叠加彩色圆形的指南针图像
        
        # hsvLower = np.array([0,0,57])
        # hsvUpper = np.array([179,55,254]) # Filter White
        hsvLower = np.array([100,43,46])
        hsvUpper = np.array([124,254,254]) # Filter UI
        compassHsv = cv2.inRange(compassHsv,hsvLower,hsvUpper)
        # hsvSunFilterLow = np.array([13,43,46])
        # hsvSunFilterUp = np.array([71,254,254])
        # outsideImg = cv2OriginImg[60:int(outsideOffsetY),:]
        # outsideHsv = cv2.cvtColor(outsideImg,cv2.COLOR_BGR2HSV)
        # outsideHsv = cv2.inRange(outsideHsv,hsvSunFilterLow,hsvSunFilterUp)
        # outsideImg = filterColorInMask(outsideImg,outsideHsv,dimensions=3)
        # compassShowImg = filterColorInMask(compassShowImg,compassHsv,highlight=True,dimensions=3)
        
        (targetX,targetY),navCenter,compassShowImg,navShowImg = getNavPointsByCompass(compassImg,compassShowImg,compassHsv)

        if checkAlignWithTemplate(centerImg,destCircleImg) is True: alignment = True
        else: alignment = False

        if targetX != -1 and targetY !=-1 and navCenter !=-1 and isFocused:
            offsetX = abs(targetX-navCenter)
            offsetY = abs(targetY-navCenter)
            if autoAlign is True and (offsetX>alignDeadZone or offsetY>alignDeadZone): 
                alignWithPos(eventsQueue,navCenter,targetX,targetY,offsetX=offsetX,offsetY=offsetY)
            if autoAlign is True and offsetX<alignDeadZone and offsetY<alignDeadZone and alignment is True: # Align completed
                autoAlign = False

                # Final Align by template matching
                # cv2.putText(compassShowImg,"Final Aligning",(10,120),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
                # finalAlignWithTemplate(eventsQueue,centerImg,destCircleImg)
        
        setStatusToStatesMachine(model)
        cv2.putText(compassShowImg,"autoAlign:%s"%autoAlign,(10,80),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
        cv2.putText(compassShowImg,"alignment:%s"%alignment,(10,105),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
        cv2.putText(cv2ShowImg,'stateModel:%s'%model.state,(10,60),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
        cv2.putText(cv2ShowImg,'state:%s'%showAllTrueStatus(),(10,90),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))

        if isFocused is False: cv2.putText(cv2ShowImg,'Lost Focus',(int(gameCenterRel[1]),60),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
        else:
            if keyboard.is_pressed('l'): # Sun Avoiding
                # cv2.imwrite("1.png",compassImg)
                sendKey(eventsQueue,'PitchUpButton',repeat=13)
        
            if keyboard.is_pressed('o'): # Toggle AutoAlign
                # pyautogui.click(gameCenter) # get focused in game
                # if navPoints is not None:
                autoAlign = bool(autoAlign-1)
            if keyboard.is_pressed('['):
                sendKey(eventsQueue,'Speed100')    
            if keyboard.is_pressed(']'): # HyperJump
                # sendKey(eventsQueue,'Speed100')
                if alignment :
                    sendKey(eventsQueue,'SpeedZero')
                    sendDelay(eventsQueue,1)
                    sendKey(eventsQueue,'EnableFSD')
                    sendDelay(eventsQueue,7)
                    sendKey(eventsQueue,'EngineBoost')
        
            if keyboard.is_pressed('-'): # Request For Docking
                askForDocking()
            # sendKey(eventsQueue,"space")

        # if(keyboard.is_pressed())
        
        cv2.imshow("game",cv2ShowImg)
        cv2.imshow("compass",compassShowImg)
        if navShowImg is not None:
            cv2.imshow("navpoint",navShowImg)
        
        if keyboard.is_pressed('p') or cv2.waitKey(1) & 0xFF == ord('p'):
            cv2.destroyAllWindows()
            closeHandler(eventsQueue)
            c1.terminate()
            c2.terminate()
            break

        capturingQueue.task_done()
    