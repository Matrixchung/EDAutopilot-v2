from utils import *
from knn import knnMatcher

sign_scassist = fileRootPath.joinpath('templates/sign_scassist.png')
sign_align_with_target = str(fileRootPath.joinpath('templates/sign_align_with_target.png'))
tab_contacts = 'templates/contacts.png'
tab_contacts_highlight = 'templates/contacts_highlight.png'
tab_sirius = 'templates/robigo/tab_sirius.png'
tab_siriusHL = 'templates/robigo/tab_sirius_highlight.png'

button_complete_mission = 'templates/button_complete_mission.png'
sign_fuel_filled = 'templates/sign_fuel_filled.png'
sign_mission = 'templates/sign_has_mission.png'

hsvWhiteLow = np.array([0,0,57])
hsvWhiteUp = np.array([179,55,254]) # Filter White
UILow = np.array([75,45,51])
# hsvUILow = np.array([100,43,46])
UIUp = np.array([124,254,254]) # Filter UI
hsvNavPointLow = np.array([21,30,0])
hsvNavPointUp = np.array([179,254,254])
navPointsPrevX = -1.0
navPointsPrevY = -1.0
def getNavPointsByCompass(compassImg,compassShowImg,compassHsv):
# def getNavPointsByCompass(compassImg,compassHsv): # NO IMAGE RETURN NEEDED
    global navPointsPrevX,navPointsPrevY
    try:
        compassHsvUI = cv2.inRange(compassHsv,UILow,UIUp)
        maskedImg = compassImg.copy()
        maskedImg = filterColorInMask(maskedImg,compassHsvUI,highlight=True) # 反向高亮
        # binary = maskedImg.copy()
        # ret1,binary1 = cv2.threshold(maskedImg,130,255,cv2.THRESH_TOZERO_INV)
        # ret,binary = cv2.threshold(binary1,100,255,cv2.THRESH_BINARY) # TODO:面临问题：雷达上的行星图标严重干扰霍夫圆变换，考虑先检测橙色的navPoint，再以它为圆心搜索导航圆
        # del ret1,ret
        # binary = cv2.dilate(binary,kernel)
        # binary = cv2.blur(binary,(3,3))
        # binary = cv2.equalizeHist(binary) # 直方图均衡化 
        # binary = cv2.GaussianBlur(binary,(3,3),0) # 高斯滤波
        # binary = cv2.medianBlur(binary, 5) # 中值滤波
        binary = cv2.GaussianBlur(maskedImg,(3,3),0)
        # binary = cv2.medianBlur(binary, 5) # 中值滤波
        circles = cv2.HoughCircles(binary, method=cv2.HOUGH_GRADIENT,dp=1,minDist=200,param1=50,param2=48,minRadius=20,maxRadius=30) 
        if circles is not None:
            circles = circles[0,:]
            compassX,compassY,compassRadius=circles[0]
            cv2.circle(compassShowImg, (int(compassX),int(compassY)), int(compassRadius), (36,255,12), 2)
            if compassRadius !=0 : 
                navPointImg = compassImg[int(compassY-compassRadius)-10:int(compassY+compassRadius)+10,int(compassX-compassRadius)-10:int(compassX+compassRadius)+10]
                navPointHsv = compassHsv[int(compassY-compassRadius)-10:int(compassY+compassRadius)+10,int(compassX-compassRadius)-10:int(compassX+compassRadius)+10]
                navPointHsv = cv2.inRange(navPointHsv,hsvNavPointLow,hsvNavPointUp)
                navPointImg = filterColorInMask(navPointImg,navPointHsv)
                navCenter = compassRadius+10.0
                navPointImg = cv2.GaussianBlur(navPointImg,(7,7),0)
                navPoints = keyPointDetector(navPointImg)
                navShowImg = cv2.cvtColor(navPointImg,cv2.COLOR_GRAY2RGB)
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
                    cv2.line(navShowImg,(int(navCenter),int(navCenter)),(int(targetX),int(targetY)),(0,255,0)) # 中点与导航点连线
                    # cv2.putText(compassShowImg,"target:%s,%s"%(int(targetX),int(targetY)),(10,20),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
                else: 
                    # cv2.putText(compassShowImg,"Target Not Found",(10,20),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
                    targetX=targetY=-1.0
        else:
            targetX=targetY=navCenter=-1.0
            navShowImg = None
    except Exception as e: 
        # print('Error in getNavPointsByCompass()')
        traceback.print_exc()
        targetX=targetY=navCenter=-1.0
        navShowImg = None
    return (targetX,targetY),navCenter,compassShowImg,navShowImg
    # return (targetX,targetY),navCenter,binary,navShowImg
def callback(a):
    pass
sign_heat = cv2.imread('templates/sign_heat_level_masked.png',0)
if __name__ == '__main__':
    # cv2.namedWindow('hsv')
    # cv2.createTrackbar('lowH','hsv',0,179,callback)
    # cv2.createTrackbar('lowS','hsv',0,254,callback)
    # cv2.createTrackbar('lowV','hsv',0,254,callback)
    # cv2.createTrackbar('upH','hsv',0,179,callback)
    # cv2.createTrackbar('upS','hsv',0,254,callback)
    # cv2.createTrackbar('upV','hsv',0,254,callback)
    # # imgReturn = ''
    # # while not keyboard.is_pressed('end'):
    # #     if keyboard.is_pressed('home'):
    # #         # screenImg = screenCapture(toFile=False)
    # #         # screenImg = cv2.cvtColor(np.asarray(screenImg),cv2.COLOR_RGB2BGR)
    # #         # sign_scassist = cv2.imread(sign_scassist)
    # #         # sign_scassist = cv2.cvtColor(sign_scassist,cv2.COLOR_RGB2BGR)
    # #         # imgReturn = knnMatcher(screenImg,sign_scassist,debug=True)
    # #         res1 = locateImageOnScreen(button_complete_mission,confidence=0.6)
            
    # #         if res1[0] != -1:
    # #             print('has mission')
    # #             pyautogui.moveTo(res1)
    # #         else : 
    # #             res2 = locateImageOnScreen(tab_siriusHL,confidence=0.6)
    # #             if res2[0]!=-1:
    # #                 print('target')
    # #     if imgReturn !='':
    # #         cv2.imshow('return',imgReturn)
    # #     cv2.waitKey(1)
    
    # cv2.setTrackbarPos('lowH','hsv',21)
    # cv2.setTrackbarPos('lowS','hsv',30)
    # cv2.setTrackbarPos('lowV','hsv',0)
    # cv2.setTrackbarPos('upH','hsv',179)
    # cv2.setTrackbarPos('upS','hsv',254)
    # cv2.setTrackbarPos('upV','hsv',254)
    # while not keyboard.is_pressed('end'):
    #     gameCoord,windowHwnd = getWindowRectByName(globalWindowName)
    #     isFocused = isForegroundWindow(globalWindowName,windowHwnd)
    #     img = pyautogui.screenshot(region=gameCoord)

    #     gameResolution = gameCoord[2],gameCoord[3]
    #     gameCenterRel = gameCoord[2]/2,gameCoord[3]/2 # 相对中点

    #     cv2OriginImg = cv2.cvtColor(np.asarray(img),cv2.COLOR_RGB2BGR)
    #     cv2ShowImg = cv2OriginImg.copy() # ShowImg for Overlay
    #     cv2GrayImg = cv2.cvtColor(cv2OriginImg,cv2.COLOR_BGR2GRAY)

    #     centerImg = cv2GrayImg[int(gameCenterRel[1]-180):int(gameCenterRel[1]+180),int(gameCenterRel[0]-220):int(gameCenterRel[0]+220)]
    #     compassImg = cv2GrayImg[int(gameResolution[1]/1.63):int(gameResolution[1]/1.06),int(gameResolution[0]/4.04):int(gameResolution[0]/2.02)] # Magic Number: size for compass img
        
    #     compassOriginImg = cv2OriginImg[int(gameResolution[1]/1.63):int(gameResolution[1]/1.06),int(gameResolution[0]/4.04):int(gameResolution[0]/2.02)]
    #     compassHsv = cv2.cvtColor(compassOriginImg,cv2.COLOR_BGR2HSV)
    #     compassShowImg = compassOriginImg.copy() # screen overlay

    #     # if checkAlignWithTemplate(centerImg,destCircleImg) is True: isAligned = 1
    #     # else: isAligned = 0
    #     hsvNavPointLow = np.array([cv2.getTrackbarPos('lowH','hsv'),cv2.getTrackbarPos('lowS','hsv'),cv2.getTrackbarPos('lowV','hsv')])
    #     hsvNavPointUp = np.array([cv2.getTrackbarPos('upH','hsv'),cv2.getTrackbarPos('upS','hsv'),cv2.getTrackbarPos('upV','hsv')])
    #     (targetX,targetY),navCenter,compassShowImg,navShowImg = getNavPointsByCompass(compassImg,compassShowImg,compassHsv)
    #     # (targetX,targetY),navCenter = getNavPointsByCompass(compassImg,compassHsv)
        
    #     # hsvUILow = np.array([cv2.getTrackbarPos('lowH','hsv'),cv2.getTrackbarPos('lowS','hsv'),cv2.getTrackbarPos('lowV','hsv')])
    #     # hsvUIUp = np.array([cv2.getTrackbarPos('upH','hsv'),cv2.getTrackbarPos('upS','hsv'),cv2.getTrackbarPos('upV','hsv')])
    #     # compassMask1 = cv2.inRange(compassHsv,hsvUILow,hsvUIUp)
    #     # compassMask1 = filterColorInMask(compassImg,compassMask1,highlight=True)
    #     # # compassMask2 = cv2.GaussianBlur(compassMask1,(5,5),0)
    #     # result = cv2.matchTemplate(compassMask1, sign_heat, cv2.TM_CCOEFF)
    #     # min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    #     # th,tw = sign_heat.shape[:2]
    #     # compassMask2 = cv2.cvtColor(compassMask1,cv2.COLOR_GRAY2RGB)
    #     # # print(max_val)
    #     # if max_val > 920000:
    #     #     tl = max_loc
    #     #     br = (tl[0] + tw, tl[1] + th)
    #     #     cv2.rectangle(compassMask2, tl, br, (0, 0, 255), 2)
    #     #     # cirCenter = (tl[0]+br[0])/2-60,(tl[1]+br[1])/2 # 应去位置
    #     # cv2.imshow('1',compassMask1)
    #     # if keyboard.is_pressed('home'):
    #     #     cv2.imwrite('img.png',compassMask1)

    #     cv2.imshow('1',compassShowImg)
    #     if navShowImg is not None:
    #         cv2.imshow('2',navShowImg)
    #     cv2.waitKey(1)
    locateImageOnScreen(sign_align_with_target)
    # print (type(sign_align_with_target))


    


