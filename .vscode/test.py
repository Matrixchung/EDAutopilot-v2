from utils import *
pyautogui.PAUSE = 1
pyautogui.FAILSAFE = True
compassX = compassY = compassRadius = 0
targetX = targetY = targetDrawRadius = 0
capturingQueue = JoinableQueue(maxsize=3)
eventsQueue=Queue(maxsize=2)
autoAlign = False
alignment = False
if __name__ == '__main__':
    c1=Process(target=eventsHandler,args=(eventsQueue,)) # Initialize Events Handler
    c2=Process(target=screenCapture,args=(capturingQueue,))
    c1.daemon=True
    c2.daemon=True
    c2.start()
    c1.start()
    destCircleImg = cv2.imread("templates/dest_circle.png",0)
    navCircleImg = cv2.imread("templates/nav_circle.png",0)
    isFocused = False
    sift = cv2.SIFT_create()
    
    while True: 
        (gameCoord,img,isFocused)=capturingQueue.get() # Async Capturing
        gameResolution = gameCoord[2],gameCoord[3]
        gameCenterActual = gameCoord[0]+gameCoord[2]/2,gameCoord[1]+gameCoord[3]/2 # 绝对中点 用于鼠标操作
        gameCenterRel = gameCoord[2]/2,gameCoord[3]/2 # 相对中点
        cv2OriginImg = cv2.cvtColor(np.asarray(img),cv2.COLOR_RGB2BGR)
        cv2ShowImg = cv2OriginImg.copy() # ShowImg for Overlay
        cv2img = cv2.cvtColor(cv2OriginImg,cv2.COLOR_BGR2GRAY)
        centerImg = cv2img[int(gameCenterRel[1]-180):int(gameCenterRel[1]+180),int(gameCenterRel[0]-220):int(gameCenterRel[0]+220)]
        compassImg = cv2img[int(gameResolution[1]/1.63):int(gameResolution[1]/1.06),int(gameResolution[0]/4.04):int(gameResolution[0]/2.02)] # Magic Number: size for compass img
        
        compassOriginImg = cv2OriginImg[int(gameResolution[1]/1.63):int(gameResolution[1]/1.06),int(gameResolution[0]/4.04):int(gameResolution[0]/2.02)]
        compassHsv = cv2.cvtColor(compassOriginImg,cv2.COLOR_BGR2HSV)
        compassShowImg = compassOriginImg.copy() # 叠加彩色圆形的指南针图像
        hsvLower = np.array([100,43,46])
        hsvUpper = np.array([124,254,254]) # Filter UI
        compassHsv = cv2.inRange(compassHsv,hsvLower,hsvUpper)
        compassImg = filterColorInMask(compassImg,compassHsv,highlight=True)
        (targetX,targetY),navCenter,compassShowImg,navShowImg = getNavPointsByCompass(compassImg,compassShowImg,compassHsv)
        if navShowImg is not None:
            keypoints = detector.detect(navShowImg)
            # navRGB = cv2.cvtColor(navShowImg,cv2.COLOR_GRAY2BGR)
            # im_with_keypoints = cv2.drawKeypoints(navShowImg, keypoints, np.array([]), (0,255,0), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
            cv2.imshow('keypoint',navShowImg)
        # kp1,des1 = sift.detectAndCompute(compassImg,None)
        # kp2,des2 = sift.detectAndCompute(navCircleImg,None)
        # # FLANN parameters
        # FLANN_INDEX_KDTREE = 1
        # index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
        # search_params = dict(checks=50)   # or pass empty dictionary
        # flann = cv2.FlannBasedMatcher(index_params,search_params)
        # matches = flann.knnMatch(des1,des2,k=2)
        # # Need to draw only good matches, so create a mask
        # matchesMask = [[0,0] for i in range(len(matches))]
        # # ratio test as per Lowe's paper
        # for i,(m,n) in enumerate(matches):
        #     if m.distance < 0.7*n.distance:
        #         matchesMask[i]=[1,0]
        # draw_params = dict(matchColor = (0,255,0),
        #             singlePointColor = (255,0,0),
        #             matchesMask = matchesMask,
        #             flags = cv2.DrawMatchesFlags_DEFAULT)
        # img3 = cv2.drawMatchesKnn(compassImg,kp1,navCircleImg,kp2,matches,None,**draw_params)
        # cv2.imshow('flann',img3)
        
        cv2.imshow("game",cv2img)
        cv2.imshow("compass",compassShowImg)
        if keyboard.is_pressed('l'):
            cv2.imwrite("1.png",compassImg)
        if keyboard.is_pressed('p') or cv2.waitKey(1) & 0xFF == ord('p'):
            cv2.destroyAllWindows()
            closeHandler(eventsQueue)
            c1.terminate()
            c2.terminate()
            break

        capturingQueue.task_done()


