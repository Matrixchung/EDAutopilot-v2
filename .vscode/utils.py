from multiprocessing import Process,Queue,shared_memory
import pyautogui
import keyboard
import os
import win32gui
import win32file
import pathlib
import cv2
import logging
import time
import numpy as np
import traceback
from ctypes import windll
from journal import *
from directinputs import *
from keybinds import *
from status import *

## Constants
ALIGN_TRIMM_DELAY = 0.030
KEY_DEFAULT_DELAY = 0.120
KEY_REPEAT_DELAY = 0.200
MOUSE_CLICK_DELAY = 0.200
DELAY_BETWEEN_KEYS = 1.5
ALIGN_DEAD_ZONE = 1.4
SLEEP_UPDATE_DELAY = 0.1

globalWindowName = "Elite - Dangerous (CLIENT)"
fileRootPath = pathlib.Path.cwd()

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
# hsvUILow = np.array([100,43,46])
hsvUILow = np.array([75,45,51])
hsvUIUp = np.array([124,254,254]) # Filter UI
hsvNavPointLow = np.array([21,30,0])
hsvNavPointUp = np.array([179,254,254]) # Filter navPoints

destCircleImg = cv2.imread("templates/dest_circle.png",0)

## In-Game Utils

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


def checkAlignWithTemplate(centerImg,circleImg): 
    result = False
    ret,binary = cv2.threshold(centerImg,110,255,cv2.THRESH_BINARY)
    del ret
    # result = cv2.matchTemplate(binary, circleImg, cv2.TM_CCORR)
    result = cv2.matchTemplate(binary, circleImg, cv2.TM_CCOEFF)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    th,tw = circleImg.shape[:2]
    centerImg = cv2.cvtColor(centerImg,cv2.COLOR_GRAY2RGB)
    if max_val > 10000000:
        tl = max_loc
        br = (tl[0] + tw, tl[1] + th)
        # cv2.rectangle(centerImg, tl, br, (0, 0, 255), 2)
        cirCenter = (tl[0]+br[0])/2-60,(tl[1]+br[1])/2 # 应去位置
        center = 180,220 # 指向位置
        # if abs(center[0]-cirCenter[0])<35 and abs(center[1]-cirCenter[1])<35 : result = True
        if abs(center[0]-cirCenter[0])<60 and abs(center[1]-cirCenter[1])<60 : result = True
        
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
            startTime = time.time()
            isFocused = isForegroundWindow(globalWindowName,windowHwnd)
            img = pyautogui.screenshot(region=gameCoord)
        
            gameResolution = gameCoord[2],gameCoord[3]
            # gameCenterActual = gameCoord[0]+gameCoord[2]/2,gameCoord[1]+gameCoord[3]/2 # 绝对中点 用于鼠标操作
            gameCenterRel = gameCoord[2]/2,gameCoord[3]/2 # 相对中点

            # outsideOffsetY = (gameCoord[3]/3)*2
            cv2OriginImg = cv2.cvtColor(np.asarray(img),cv2.COLOR_RGB2BGR)
            # cv2ShowImg = cv2OriginImg.copy() # ShowImg for Overlay
            cv2GrayImg = cv2.cvtColor(cv2OriginImg,cv2.COLOR_BGR2GRAY)

            centerImg = cv2GrayImg[int(gameCenterRel[1]-180):int(gameCenterRel[1]+180),int(gameCenterRel[0]-220):int(gameCenterRel[0]+220)]
            compassImg = cv2GrayImg[int(gameResolution[1]/1.63):int(gameResolution[1]/1.06),int(gameResolution[0]/4.04):int(gameResolution[0]/2.02)] # Magic Number: size for compass img
        
            compassOriginImg = cv2OriginImg[int(gameResolution[1]/1.63):int(gameResolution[1]/1.06),int(gameResolution[0]/4.04):int(gameResolution[0]/2.02)]
            compassHsv = cv2.cvtColor(compassOriginImg,cv2.COLOR_BGR2HSV)
            # compassShowImg = compassOriginImg.copy() # screen overlay

            if checkAlignWithTemplate(centerImg,destCircleImg) is True: isAligned = 1
            else: isAligned = 0

            # (targetX,targetY),navCenter,compassShowImg,navShowImg = getNavPointsByCompass(compassImg,compassShowImg,compassHsv) # NO IMAGE RETURN NEEDED
            (targetX,targetY),navCenter = getNavPointsByCompass(compassImg,compassHsv)

            shr_coord = shared_memory.SharedMemory(name=coordShrName)
            coordArray = np.ndarray(shape=8,dtype=np.float64,buffer=shr_coord.buf)
            elapsedTime = time.time()-startTime
            coordArray[:] = [targetX,targetY,navCenter,isAligned,isFocused,elapsedTime,gameCoord[0],gameCoord[1]]  
        except:
            pass
            # traceback.print_exc()

def createSharedCoordsBlock(name='ImgCoords'): # targetX,targetY,navCenter,isAligned,isFocused,elapsedTime,windowLeftX,windowTopY
    a = np.zeros(8)
    shr = shared_memory.SharedMemory(create=True,name=name,size=a.nbytes)
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

# Window Utils
# def getNavPointsByCompass(compassImg,compassShowImg,compassHsv):
navPointsPrevX = -1.0
navPointsPrevY = -1.0
def getNavPointsByCompass(compassImg,compassHsv): # NO IMAGE RETURN NEEDED
    global navPointsPrevX,navPointsPrevY
    try:
        compassHsvUI = cv2.inRange(compassHsv,hsvUILow,hsvUIUp)
        maskedImg = compassImg.copy()
        maskedImg = filterColorInMask(maskedImg,compassHsvUI,highlight=True) # 反向高亮
        # binary = maskedImg.copy()
        # ret1,binary1 = cv2.threshold(maskedImg,130,255,cv2.THRESH_TOZERO_INV)
        # ret,binary = cv2.threshold(binary1,100,255,cv2.THRESH_BINARY) 
        # del ret1,ret
        # # binary = cv2.dilate(binary,kernel)
        # # binary = cv2.blur(binary,(3,3))
        # # binary = cv2.equalizeHist(binary) # 直方图均衡化 
        # binary = cv2.GaussianBlur(binary,(3,3),0) # 高斯滤波
        # binary = cv2.medianBlur(binary, 5) # 中值滤波
        binary = cv2.GaussianBlur(maskedImg,(3,3),0)
        circles = cv2.HoughCircles(binary, method=cv2.HOUGH_GRADIENT,dp=1,minDist=200,param1=50,param2=48,minRadius=20,maxRadius=30) 
        if circles is not None:
            circles = circles[0,:]
            compassX,compassY,compassRadius=circles[0]
            # cv2.circle(compassShowImg, (int(compassX),int(compassY)), int(compassRadius), (36,255,12), 2)
            if compassRadius !=0 : 
                navPointImg = compassImg[int(compassY-compassRadius)-10:int(compassY+compassRadius)+10,int(compassX-compassRadius)-10:int(compassX+compassRadius)+10]
                navPointHsv = compassHsv[int(compassY-compassRadius)-10:int(compassY+compassRadius)+10,int(compassX-compassRadius)-10:int(compassX+compassRadius)+10]
                navPointHsv = cv2.inRange(navPointHsv,hsvNavPointLow,hsvNavPointUp)
                navPointImg = filterColorInMask(navPointImg,navPointHsv)
                navCenter = compassRadius+10.0
                navPointImg = cv2.GaussianBlur(navPointImg,(7,7),0)
                navPoints = keyPointDetector(navPointImg)
                # navShowImg = cv2.cvtColor(navPointImg,cv2.COLOR_GRAY2RGB)
                if navPoints is not None:
                    # targetX = int(navPoints[0])
                    # targetY = int(navPoints[1])
                    targetX = navPoints[0]
                    targetY = navPoints[1] # change to float
                    if navPointsPrevX == -1.0 or navPointsPrevY == -1.0: # initialize
                        navPointsPrevX = targetX
                        navPointsPrevY = targetY
                    elif abs(navPointsPrevX-targetX)>=40 or abs(navPointsPrevY-targetY)>=40: # 滤波
                        targetX = navPointsPrevX
                        targetY = navPointsPrevY
                    else:
                        navPointsPrevX = targetX
                        navPointsPrevY = targetY
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

def screenCapture(toFile=True):
    gameCoord,hwnd = getWindowRectByName(globalWindowName)
    if toFile is True:
        imgPath = time.strftime("%Y-%m-%d-%H-%M-%S",time.localtime())+".png"
        img = pyautogui.screenshot(imgPath,region=gameCoord)
    else:
        img = pyautogui.screenshot(region=gameCoord)
        return img

def locateImageOnScreen(img,confidence=None,region=None):
    try:
        if confidence is not None:
            if region is not None: imageBox = pyautogui.locateOnScreen(img,confidence=confidence,region=region)
            else: imageBox = pyautogui.locateOnScreen(img,confidence=confidence)
        else:
            if region is not None: imageBox = pyautogui.locateOnScreen(img,region=region)
            else: imageBox = pyautogui.locateOnScreen(img)
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
    return origin[0]+offset[0],origin[1]+offset[1]

def getOffsetCoordByAbsolute(origin,abs): 
    return abs[0]-origin[0],abs[1]-origin[1]

def mouseClick(*args): # y=None to provide compability to Tuple
    clickX = clickY = None
    if len(args) == 1 and args[0][0]>=0 and args[0][1]>=0 : # Tuple
        clickX = args[0][0]
        clickY = args[0][1]
    elif len(args) == 2 and args[0]>=0 and args[1]>=0 : # x,y
        clickX = args[0]
        clickY = args[1]
    pyautogui.mouseDown(clickX,clickY)
    time.sleep(MOUSE_CLICK_DELAY)
    pyautogui.mouseUp()
    return True

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

def killProcess(processName):
    os.system('TASKKILL /F /IM '+processName)