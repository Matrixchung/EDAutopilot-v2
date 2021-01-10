from transitions import *
from multiprocessing import Process,Queue,shared_memory
from threading import Event
import pyautogui
import keyboard
import win32gui
import win32file
import sys
import re
import array
import cv2
import time
import numpy as np
import traceback
from ctypes import windll
from journal import *
from directinputs import *
from keybinds import *
from status import *

## Constants
ALIGN_TRIMM_DELAY = 0.020
KEY_DEFAULT_DELAY = 0.120
KEY_REPEAT_DELAY = 0.200
DELAY_BETWEEN_KEYS = 1.5
alignDeadZone = 2.0
globalWindowName = "Elite - Dangerous (CLIENT)"

eventsQueue = Queue(maxsize=1)

params = cv2.SimpleBlobDetector_Params()
params.filterByArea = True
params.minArea = 15
params.filterByColor = True
params.blobColor = 255
params.filterByCircularity = True
params.minCircularity = 0.4
params.filterByConvexity = True
params.minConvexity = 0.3
params.filterByInertia = True
params.minInertiaRatio = 0.3

hsvWhiteLow = np.array([0,0,57])
hsvWhiteUp = np.array([179,55,254]) # Filter White
hsvUILow = np.array([100,43,46])
hsvUIUp = np.array([124,254,254]) # Filter UI

# compassX = compassY = 0
# targetX = targetY = 0
# outsideOffsetY = 0
autoAlign = False
alignment = False
destCircleImg = cv2.imread("templates/dest_circle.png",0)

## State Machine
class shipState(object):
    def on_enter_sunavoiding(self):
        sendKey('SpeedZero')
        sendKey('PitchUpButton',repeat=13)
    def on_enter_hyperspace(self):
        sendKey('SpeedZero') # Auto dethrottle
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

## In-Game Utils

def goToPanel(panelName,subPanelName=None,panelImg=None):
    # Three conditions : 1) not at the panelName,go to panelName
    # 2) not at the panelName,go to subPanelName
    # 3) at the panelName,go to subPanelName
    currentPanel = getGuiFocus()
    key = None
    if currentPanel != panelName : # cond 1 and 2
        if subPanelName is not None and panelImg is not None: # cond 2
            if panelName == 'Panel_1': 
                goToPanel('Panel_1') # GOTO cond 3 (to get panelImg)
        else: # cond 1
            if panelName == 'Panel_1': key = ('UI_1',)
            elif panelName == 'Panel_2': key = ('UI_2',)
            elif panelName == 'Panel_3': key = ('UI_3',)
            elif panelName == 'Panel_4': key = ('UI_4',)
    elif subPanelName is not None and panelImg is not None: # cond 3
        pass
    if key is not None:
        sendKeySequence(key)

def getUICursor(panelName,panelImg):
    if panelName == 'Panel_1':
        pass

def getSunPercent(outsideImage):
    return # WIP

def sendHexKey(key, hold=None, repeat=1, repeat_delay=None, state=None):
    global KEY_MOD_DELAY, KEY_DEFAULT_DELAY, KEY_REPEAT_DELAY
    if key is None:
        logging.warning('Send an empty key')
        return
    for i in range(repeat):
        if state is None or state == 1:
            PressKey(keysDict[key])
        if state is None:
            if hold:
                time.sleep(hold)
            else:
                time.sleep(KEY_DEFAULT_DELAY)
        if state is None or state == 0:
            ReleaseKey(keysDict[key])
        if repeat_delay:
            time.sleep(repeat_delay)
        elif repeat>2:
            time.sleep(KEY_REPEAT_DELAY)
        else:
            time.sleep(0.08)

def sendKeySequence(keys, delay=DELAY_BETWEEN_KEYS):
    # the param 'keys' is a TUPLE
    for key in keys:
        sendKey(key)
        sendDelay(delay)

def alignWithPos(navCenter,targetX,targetY,offsetX=None,offsetY=None,navCenterY=None,override=False,queue=None):
    trimX=trimY=0.0
    if queue is None:
        queue = eventsQueue
    if navCenterY is None:
        navCenterY = navCenter # 正方形中点
    if offsetX is None and offsetY is None :
        offsetX = abs(targetX-navCenter)
        offsetY = abs(targetY-navCenterY)
        if offsetX<3: trimX = ALIGN_TRIMM_DELAY # trimming
        if offsetY<3: trimY = ALIGN_TRIMM_DELAY
    if eventsQueue.empty() or override is True:
        if offsetX > alignDeadZone and offsetY > alignDeadZone : # 斜着的情况 先处理Y轴
            if targetY<navCenterY:
                sendKey('PitchUpButton',queue=queue,hold=KEY_DEFAULT_DELAY-trimY)
            else:
                sendKey('PitchDownButton',queue=queue,hold=KEY_DEFAULT_DELAY-trimY)
        else:
            if offsetX>alignDeadZone:
                if targetX>navCenter:
                    sendKey('YawRightButton',queue=queue,hold=KEY_DEFAULT_DELAY-trimX)
                else:
                    sendKey('YawLeftButton',queue=queue,hold=KEY_DEFAULT_DELAY-trimX)
            if offsetY>alignDeadZone:
                if targetY<navCenterY:
                    sendKey('PitchUpButton',queue=queue,hold=KEY_DEFAULT_DELAY-trimY)
                else:
                    sendKey('PitchDownButton',queue=queue,hold=KEY_DEFAULT_DELAY-trimY)
    return

def checkAlignWithTemplate(centerImg,circleImg): 
    result = False
    ret,binary = cv2.threshold(centerImg,110,255,cv2.THRESH_BINARY)
    del ret
    result = cv2.matchTemplate(binary, circleImg, cv2.TM_CCORR)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    th,tw = circleImg.shape[:2]
    centerImg = cv2.cvtColor(centerImg,cv2.COLOR_GRAY2RGB)
    if max_val > 10000000:
        tl = max_loc
        br = (tl[0] + tw, tl[1] + th)
        # cv2.rectangle(centerImg, tl, br, (0, 0, 255), 2)
        cirCenter = (tl[0]+br[0])/2-60,(tl[1]+br[1])/2 # 应去位置
        center = 180,220 # 指向位置
        if abs(center[0]-cirCenter[0])<45 and abs(center[1]-cirCenter[1])<45 : result = True
        # alignWithPos(queue,(tl[0]+br[0])/2,180,220,navCenterY=(tl[1]+br[1])/2,override=True)
    return result
    # return centerImg

# Image Processing Thread
def imageProcessing(coordShrName):
    isAligned = 0
    windowHwnd = win32gui.FindWindow(None,globalWindowName)
    while True:
        try: # already has windowHwnd
            gameCoord = getWindowRectByHwnd(windowHwnd)
        except: # gameHwnd changed
           gameCoord,windowHwnd = getWindowRectByName(globalWindowName)
        try:
            isFocused = isForegroundWindow(globalWindowName,windowHwnd)
            img = pyautogui.screenshot(region=gameCoord)
        
            gameResolution = gameCoord[2],gameCoord[3]
            gameCenterActual = gameCoord[0]+gameCoord[2]/2,gameCoord[1]+gameCoord[3]/2 # 绝对中点 用于鼠标操作
            gameCenterRel = gameCoord[2]/2,gameCoord[3]/2 # 相对中点

            outsideOffsetY = (gameCoord[3]/3)*2
            cv2OriginImg = cv2.cvtColor(np.asarray(img),cv2.COLOR_RGB2BGR)
            # cv2ShowImg = cv2OriginImg.copy() # ShowImg for Overlay
            cv2GrayImg = cv2.cvtColor(cv2OriginImg,cv2.COLOR_BGR2GRAY)

            centerImg = cv2GrayImg[int(gameCenterRel[1]-180):int(gameCenterRel[1]+180),int(gameCenterRel[0]-220):int(gameCenterRel[0]+220)]
            compassImg = cv2GrayImg[int(gameResolution[1]/1.63):int(gameResolution[1]/1.06),int(gameResolution[0]/4.04):int(gameResolution[0]/2.02)] # Magic Number: size for compass img
        
            compassOriginImg = cv2OriginImg[int(gameResolution[1]/1.63):int(gameResolution[1]/1.06),int(gameResolution[0]/4.04):int(gameResolution[0]/2.02)]
            compassHsv = cv2.cvtColor(compassOriginImg,cv2.COLOR_BGR2HSV)
            # compassShowImg = compassOriginImg.copy() # 叠加彩色圆形的指南针图像

            if checkAlignWithTemplate(centerImg,destCircleImg) is True: isAligned = 1
            else: isAligned = 0

            # (targetX,targetY),navCenter,compassShowImg,navShowImg = getNavPointsByCompass(compassImg,compassShowImg,compassHsv) # NO IMAGE RETURN NEEDED
            (targetX,targetY),navCenter = getNavPointsByCompass(compassImg,compassHsv)

            shr_coord = shared_memory.SharedMemory(name=coordShrName)
            coordArray = np.ndarray(shape=5,dtype=np.float64,buffer=shr_coord.buf)
            coordArray[:] = [targetX,targetY,navCenter,isAligned,isFocused]  
        except :
            traceback.print_exc()

def createSharedCoordsBlock(): # targetX,targetY,navCenter,isAligned,isFocused
    a = np.zeros(5)
    shr = shared_memory.SharedMemory(create=True,name='ImgCoords',size=a.nbytes)
    npArray = np.ndarray(a.shape,dtype=np.float64,buffer=shr.buf)
    npArray[:] = a[:]
    return shr,npArray

# Event Thread
def eventsHandler(q):
    while True:
        params=q.get()
        if params == 'ENDQUEUE':
            break
        elif params[0] == 'KEY' and isForegroundWindow(globalWindowName):
            sendHexKey(params[1],params[2],params[3],params[4],params[5])
        elif params[0] == 'DELAY':
            time.sleep(params[1])
            # callback when delay done WIP

def sendKey(key, hold=None, repeat=1, repeat_delay=None, state=None, queue=None):
    if queue is None : queue = eventsQueue
    eventStruct = 'KEY',key,hold,repeat,repeat_delay,state
    queue.put(eventStruct)
    return

def sendDelay(d):
    eventStruct = 'DELAY',d
    eventsQueue.put(eventStruct)
    return

def closeHandler():
    eventStruct = 'ENDQUEUE'
    eventsQueue.put(eventStruct)
    return

# Window Utils
# def getNavPointsByCompass(compassImg,compassShowImg,compassHsv):
def getNavPointsByCompass(compassImg,compassHsv): # NO IMAGE RETURN NEEDED
    try:
        compassHsvUI = cv2.inRange(compassHsv,hsvUILow,hsvUIUp)
        maskedImg = compassImg.copy()
        maskedImg = filterColorInMask(maskedImg,compassHsvUI,highlight=True)
        # binary = maskedImg.copy()
        ret1,binary1 = cv2.threshold(maskedImg,130,255,cv2.THRESH_TOZERO_INV)
        ret,binary = cv2.threshold(binary1,100,255,cv2.THRESH_BINARY) # TODO:Optimize Compass navCircle Recognization
        del ret1,ret
        # binary = cv2.dilate(binary,kernel)
        # binary = cv2.blur(binary,(3,3))
        # binary = cv2.equalizeHist(binary) # 直方图均衡化 
        binary = cv2.GaussianBlur(binary,(3,3),0) # 高斯滤波
        binary = cv2.medianBlur(binary, 5) # 中值滤波
        circles = cv2.HoughCircles(binary, method=cv2.HOUGH_GRADIENT,dp=2,minDist=20,param1=40,param2=40,minRadius=20,maxRadius=30) 
        if circles is not None:
            circles = circles[0,:]
            compassX,compassY,compassRadius=circles[0]
            # cv2.circle(compassShowImg, (int(compassX),int(compassY)), int(compassRadius), (36,255,12), 2)
            if compassRadius !=0 : 
                navPointImg = compassHsv[int(compassY-compassRadius)-10:int(compassY+compassRadius)+10,int(compassX-compassRadius)-10:int(compassX+compassRadius)+10]
                navPointImg = cv2.inRange(navPointImg,hsvWhiteLow,hsvWhiteUp)
                navCenter = compassRadius+10.0
                navPointImg = cv2.GaussianBlur(navPointImg,(11,11),0)
                navPoints = keyPointDetector(navPointImg)
                # navShowImg = cv2.cvtColor(navPointImg,cv2.COLOR_GRAY2RGB)
                if navPoints is not None:
                    # targetX = int(navPoints[0])
                    # targetY = int(navPoints[1])
                    targetX = navPoints[0]
                    targetY = navPoints[1] # change to float
                    # cv2.circle(navShowImg, (targetX,targetY), 2, (36,255,12), 2) # 圈出识别点
                    # cv2.line(navShowImg,(int(navCenter),int(navCenter)),(int(targetX),int(targetY)),(0,255,0)) # 中点与导航点连线
                    # cv2.putText(compassShowImg,"target:%s,%s"%(int(targetX),int(targetY)),(10,20),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
                else: 
                    # cv2.putText(compassShowImg,"Target Not Found",(10,20),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
                    targetX=targetY=-1.0
        else:
            targetX=targetY=navCenter=-1.0
            # navShowImg = None
    except Exception as e: 
        print('Error in getNavPointsByCompass()')
        # traceback.print_exc()
        targetX=targetY=navCenter=-1.0
        # navShowImg = None
    # return (targetX,targetY),navCenter,compassShowImg,navShowImg
    return (targetX,targetY),navCenter # NO IMAGE RETURN NEEDED
def screenCapture():
    gameCoord,hwnd = getWindowRectByName(globalWindowName)
    imgPath = time.strftime("%Y-%m-%d-%H-%M-%S",time.localtime())+".png"
    img = pyautogui.screenshot(imgPath,region=gameCoord)
def locateImageOnScreen(img,confidence=None):
    try:
        if confidence is not None:
            imageBox = pyautogui.locateOnScreen(img,confidence=confidence)
        else:imageBox = pyautogui.locateOnScreen(img)
        if imageBox is None: return (-1,-1)
        else:
            imageLoc = pyautogui.center(imageBox)
            return imageLoc
    except:
        traceback.print_exc()
def locateButtons(img,imgHL,confidence1=None,confidence2=None):
    if confidence1 is not None: imgLoc = locateImageOnScreen(img,confidence=confidence1)
    else: imgLoc = locateImageOnScreen(img)
    if confidence2 is not None: imgHL = locateImageOnScreen(imgHL,confidence=confidence2)
    else : imgHL = locateImageOnScreen(imgHL)
    if imgHL[0] == -1: return imgLoc
    if imgLoc[0] == -1: return imgHL
    
detector = cv2.SimpleBlobDetector_create(params)
def keyPointDetector(sourceImg):
    keypoints = detector.detect(sourceImg)
    # print(keypoints[0].pt)
    # navRGB = cv2.cvtColor(navShowImg,cv2.COLOR_GRAY2BGR)
    # im_with_keypoints = cv2.drawKeypoints(navRGB, keypoints, np.array([]), (0,255,0), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
    if not keypoints:
        return None
    return keypoints[0].pt

def filterColorInMask(origin,mask,highlight=False,dimensions=1):
    row,column = origin.shape[:2]
    for r in range(row):
        for c in range(column):
            if highlight is True:
                if mask.item(r,c) != 255:
                    if dimensions>1:
                        for i in range(0,dimensions):
                            origin.itemset((r,c,i),0)
                    else: 
                        origin.itemset((r,c),0)
            elif mask.item(r,c) == 255:
                if dimensions>1:
                    for i in range(0,dimensions):
                        origin.itemset((r,c,i),0)
                else: 
                    origin.itemset((r,c),0)
    return origin

def getWindowRectByHwnd(windowHwnd):
    left, top, right, bottom = win32gui.GetWindowRect(windowHwnd)
    w = right - left
    h = bottom - top
    return (left,top,w,h)

def getWindowRectByName(windowName):
    hwnd = win32gui.FindWindow(None, windowName)
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    w = right - left
    h = bottom - top
    return (left,top,w,h),hwnd

def getAbsoluteCoordByOffset(origin,offset):
    return origin[0]+(offset[0]+offset[2]/2),origin[1]+(offset[1]+offset[3]/2)

def matchTemplateCoord(origin,template,method):
    h,w=template.shape[:2]
    result=cv2.matchTemplate(origin,template,method)
    min_val,max_val,min_loc,max_loc = cv2.minMaxLoc(result)
    if method in [cv.TM_SQDIFF, cv.TM_SQDIFF_NORMED]:
        top_left = min_loc
    else:
        top_left = max_loc
    bottom_right = (top_left[0] + w, top_left[1] + h)
    return top_left,bottom_right

def isForegroundWindow(windowName,windowHwnd=None):
    if windowHwnd == None:
        windowHwnd = win32gui.FindWindow(None, windowName)
    foregroundHwnd = win32gui.GetForegroundWindow()
    if windowHwnd == foregroundHwnd:
        return True
    return False

def isFileOpen(filePath):
    try:
        fHandle = win32file.CreateFile(filePath,win32file.GENERIC_READ,0,None,win32file.OPEN_EXISTING,win32file.FILE_ATTRIBUTE_NORMAL,None)
        if int(fHandle) == win32file.INVALID_HANDLE_VALUE: # already opened and occupied
            return True
        win32file.CloseHandle(fHandle)
        return False
    except:
        return True