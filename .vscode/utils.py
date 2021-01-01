from transitions import *
from multiprocessing import Process,Queue,JoinableQueue
import pyautogui
import keyboard
import win32gui
import win32ui
import win32api
import win32con
import sys
import cv2
import time
import numpy as np
import traceback
import time
from directinputs import *
from keybinds import *
from status import *

## Constants
KEY_DEFAULT_DELAY = 0.200
KEY_REPEAT_DELAY = 0.100
FUNCTION_DEFAULT_DELAY = 0.500
alignDeadZone = 2
globalWindowName = "Elite - Dangerous (CLIENT)"

params = cv2.SimpleBlobDetector_Params()
# params.minThreshold = 200
# params.maxThreshold = 255
params.filterByArea = True
params.minArea = 25
params.filterByColor = True
params.blobColor = 255
params.filterByCircularity = True
params.minCircularity = 0.6
params.filterByConvexity = True
params.minConvexity = 0.5
params.filterByInertia = False
params.minInertiaRatio = 0.01

## In-Game Utils

def askForDocking():
    sendKey(eventsQueue,"UI_1")
    sendDelay(eventsQueue,1)
    sendKey(eventsQueue,"UI_NextTab",repeat=2)
    sendDelay(eventsQueue,1)
    sendKey(eventsQueue,"space")
    sendDelay(eventsQueue,1)
    sendKey(eventsQueue,"UI_Right")
    sendDelay(eventsQueue,1)
    sendKey(eventsQueue,"space")
    sendDelay(eventsQueue,1)

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
        else:
            time.sleep(KEY_REPEAT_DELAY)

def alignWithPos(eventsQueue,navCenter,targetX,targetY,offsetX=None,offsetY=None,navCenterY=None,override=False):
    if navCenterY is None:
        navCenterY = navCenter # 正方形中点
    if offsetX is None and offsetY is None :
        offsetX = abs(targetX-navCenter)
        offsetY = abs(targetY-navCenterY)
    if eventsQueue.empty() or override is True:
        if offsetX > alignDeadZone and offsetY > alignDeadZone : # 斜着的情况 先处理Y轴
            if targetY<navCenterY:
                sendKey(eventsQueue,'PitchUpButton')
            else:
                sendKey(eventsQueue,'PitchDownButton')
        else:
            if offsetX>alignDeadZone:
                if targetX>navCenter:
                    sendKey(eventsQueue,'YawRightButton')
                else:
                    sendKey(eventsQueue,'YawLeftButton')
            if offsetY>alignDeadZone:
                if targetY<navCenterY:
                    sendKey(eventsQueue,'PitchUpButton')
                else:
                    sendKey(eventsQueue,'PitchDownButton')
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
        if abs(center[0]-cirCenter[0])<80 and abs(center[1]-cirCenter[1])<80 : result = True
        # alignWithPos(queue,(tl[0]+br[0])/2,180,220,navCenterY=(tl[1]+br[1])/2,override=True)
    return result
    # return centerImg

# Screen Capturing Queues
def screenCapture(q):
    while True:
        gameCoord,hwnd = getWindowRectByName(globalWindowName)
        isFocused = isForegroundWindow(globalWindowName,hwnd)
        img = pyautogui.screenshot(region=gameCoord)
        q.put((gameCoord,img,isFocused))
        q.join()

# Event Queues
def eventsHandler(q):
    while True:
        params=q.get()
        if params == 'ENDQUEUE':
            break
        elif params[0] == 'KEY' and isForegroundWindow(globalWindowName):
            sendHexKey(params[1],params[2],params[3],params[4],params[5])
        elif params[0] == 'DELAY':
            time.sleep(params[1])

def sendKey(q, key, hold=None, repeat=1, repeat_delay=None, state=None):
    if q is None:
        return
    eventStruct = 'KEY',key,hold,repeat,repeat_delay,state
    q.put(eventStruct)
    return

def sendDelay(q,d):
    eventStruct = 'DELAY',d
    q.put(eventStruct)
    return

def closeHandler(q):
    eventStruct = 'ENDQUEUE'
    q.put(eventStruct)
    return

# Window Utils

def getNavPointsByCompass(compassImg,compassShowImg,compassHsv):
    try:
        maskedImg = compassImg.copy()
        maskedImg = filterColorInMask(maskedImg,compassHsv,highlight=True)
        # binary = maskedImg.copy()
        ret1,binary1 = cv2.threshold(maskedImg,130,255,cv2.THRESH_TOZERO_INV)
        ret,binary = cv2.threshold(binary1,100,255,cv2.THRESH_BINARY)
        del ret1,ret
        # binary = cv2.dilate(binary,kernel)
        # binary = cv2.blur(binary,(3,3))
        # binary = cv2.equalizeHist(binary) # 直方图均衡化
        binary = cv2.GaussianBlur(binary,(3,3),0) # 高斯滤波
        binary = cv2.medianBlur(binary, 5) # 中值滤波
        circles = cv2.HoughCircles(binary, method=cv2.HOUGH_GRADIENT,dp=2,minDist=20,param1=40,param2=40,minRadius=20,maxRadius=30) 
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            compassX,compassY,compassRadius=circles[0]
            cv2.circle(compassShowImg, (compassX,compassY), compassRadius, (36,255,12), 2)
            if compassRadius !=0 : 
                navPointImg = compassImg[compassY-compassRadius-10:compassY+compassRadius+10,compassX-compassRadius-10:compassX+compassRadius+10]
                navCenter = compassRadius+10
                ret,navPointImg=cv2.threshold(navPointImg,170,255,cv2.THRESH_BINARY)
                del ret
                navPointImg = cv2.GaussianBlur(navPointImg,(3,3),0)
                navPoints = keyPointDetector(navPointImg)
                navShowImg = cv2.cvtColor(navPointImg,cv2.COLOR_GRAY2RGB)
                if navPoints is not None:
                    targetX = int(navPoints[0])
                    targetY = int(navPoints[1])
                    cv2.circle(navShowImg, (targetX,targetY), 2, (36,255,12), 2) # 圈出识别点
                    cv2.line(navShowImg,(navCenter,navCenter),(targetX,targetY),(0,255,0)) # 中点与导航点连线
                    cv2.putText(compassShowImg,"target:%s,%s"%(targetX,targetY),(10,20),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
                else: 
                    cv2.putText(compassShowImg,"Target Not Found",(10,20),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
                    targetX=targetY=-1
        else:
            targetX=targetY=navCenter=-1
            navShowImg = None
    except Exception as e: 
        print('Error in getNavPointsByCompass()')
        traceback.print_exc()
        targetX=targetY=navCenter=-1
        navShowImg = None
    return (targetX,targetY),navCenter,compassShowImg,navShowImg

detector = cv2.SimpleBlobDetector_create(params)
def keyPointDetector(sourceImg):
    keypoints = detector.detect(sourceImg)
    # print(keypoints[0].pt)
    # navRGB = cv2.cvtColor(navShowImg,cv2.COLOR_GRAY2BGR)
    # im_with_keypoints = cv2.drawKeypoints(navRGB, keypoints, np.array([]), (0,255,0), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
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