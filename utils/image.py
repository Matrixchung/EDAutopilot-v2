import traceback
import cv2
import operator
import numpy as np
import pathlib
import ctypes
import win32gui
from pyautogui import size,screenshot
from os import environ
from os.path import isfile
from xml.dom.minidom import parse
# Whole game screen is divided into four parts
# Left bottom: For compass recognition
# Left top: No use (comm panel)
# Right bottom: Fuel stats, etc.
# Right top: For message recognition (interdiction, etc.)

# Implement an Image.applyColorMask from ED's RGB in/out to fit different color of ui
# Do the template matching in grayscale / masked color

# <MatrixRed> 1, 0, 0 </MatrixRed>
# <MatrixGreen> 0, 1, 0 </MatrixGreen>
# <MatrixBlue> 0, 0, 1 </MatrixBlue> 
fileRootPath = pathlib.Path.cwd()
def joinPath(pathName):
    if '.vscode' in str(fileRootPath): root = fileRootPath.parent
    else: root = fileRootPath
    if pathName[0] == '/' or pathName[0] == '\\': pathName = pathName[1:]
    result = str(root.joinpath(pathName))
    return result
uiColorXmlPath = f"{environ['LOCALAPPDATA']}\Frontier Developments\Elite Dangerous\Options\Graphics\GraphicsConfigurationOverride.xml"
displayXmlPath = f"{environ['LOCALAPPDATA']}\Frontier Developments\Elite Dangerous\Options\Graphics\DisplaySettings.xml"
def getWindowRect(hwnd=None,name=None) -> tuple:
    if hwnd is None: 
        assert name, 'Invalid argument'
        hwnd = win32gui.FindWindow(None, name)
        if hwnd == 0: return (0,0,0,0) # can't find window
    try: 
        d = ctypes.windll.dwmapi.DwmGetWindowAttribute
    except WindowsError: return (0,0,0,0)
    if d: 
        rect = ctypes.wintypes.RECT()
        d(ctypes.wintypes.HWND(hwnd), ctypes.wintypes.DWORD(9), ctypes.byref(rect), ctypes.sizeof(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if rect.left<0 and rect.top<0: # FULLSCREEN
            w, h = size()
            return (0,0,w,h)
        return rect.left, rect.top, w, h # works well on WINDOWED and BORDERLESS
class Screen:
    # "Region name": {"loc"(all relative percent and in decimals):[leftTopX,leftTopY,rightBottomX,rightBottomY],"filter":np.array(cv2.inrange)}
    # relative loc in percent will be converted to relative loc in pixel based on window resolution
    regions = {
        "compass": {"loc":[0.25, 0.65, 0.48, 0.97]},
        "alert": {"loc":[0.33, 0.27, 0.66, 0.70]}, # target occluded and other alerts
        "navPanel": {"loc":[0.25, 0.36, 0.60, 0.85]},
        "center": {"loc":[0.4, 0.4, 0.6, 0.625]},
    }
    def __init__(self,logger,config) -> None: 
        self.logger = logger
        self.config = config
        try: 
           _,_,self.width,self.height = getWindowRect(name='Elite - Dangerous (CLIENT)')
           # self.width,self.height = (1920,1080) # for debug
        except: 
            traceback.print_exc()
            self = None
        else: 
            convertedRegions = {}
            for region in self.regions.items():
                locs = region[1]['loc']
                convertedLocs = [round(locs[0]*self.width),round(locs[1]*self.height),round(locs[2]*self.width),round(locs[3]*self.height)]
                region[1]['loc'] = convertedLocs
                convertedRegions[region[0]] = region[1]
            self.regions = convertedRegions
    def screenshot(self,grayscale=False) -> cv2.Mat:
        gameRegion = getWindowRect(name='Elite - Dangerous (CLIENT)')
        if gameRegion: return cv2.cvtColor(np.asarray(screenshot(region=gameRegion)),cv2.COLOR_RGB2GRAY if grayscale else cv2.COLOR_RGB2BGR)
        raise
    def getRegion(self,regionName:str,grayscale:bool=False,img:cv2.Mat=None) -> cv2.Mat:
        try: 
            locs = self.regions[regionName]['loc']
        except KeyError: print(f"Requested {regionName} is not valid!")
        else: 
            screenImg = self.screenshot(grayscale=grayscale) if type(img) == type(None) else img
            return screenImg[locs[1]:locs[3],locs[0]:locs[2]]
class Image:
    # "Template name" : {"grayscale","scalable","path"}
    # Any templates set "grayscale" to False will attempt to be converted by colorMatrix
    templates = {
        "destCircle": {"grayscale": True, "scalable": True, "path": "templates/dest_circle.png"},
        "compass": {"grayscale": True, "scalable": True, "path": "templates/compass.png"},
        "navPoint": {"grayscale": True, "scalable": True, "path": "templates/navpoint.png"},
        "navPointHollow": {"grayscale": True, "scalable": True, "path": "templates/navpoint_hollow.png"},
        # "destCircle_occluded": {"grayscale": "True","scalable": "True","path": "templates/dest_circle_occluded.png"},
        # "compass": {"grayscale": True,"scalable": True,"path": "templates/compass.png"}
    }
    # "Template name" : [converted img(cv2),size(x,y)(tuple)]
    result = {}
    originMatrix = [
    # R G B
    [1,0,0], #<MatrixRed>
    [0,1,0], #<MatrixGreen>
    [0,0,1]  #<MatrixBlue>
    ]
    # default resolution is 1600x900
    presetScales = {
        '1920x1080': [1.25,1.25],
        '2560x1440': [1.66,1.66],
        '1600x900': [1.0,1.0]
    }
    scale = [1.0,1.0]
    screenSize = [1920,1080]
    needMask = False
    logger = None
    def __init__(self,logger,config) -> None:
        self.config = config
        self.logger = logger
        # Load screen resolution and prepare to scaling
        # need to get game resolution instead of screen resolution
        try:
            if isfile(displayXmlPath):
                data = parse(displayXmlPath)
                rootConfig = data.documentElement
                gameWidth = rootConfig.getElementsByTagName('ScreenWidth')
                gameHeight = rootConfig.getElementsByTagName('ScreenHeight')
                if len(gameWidth)>0 and len(gameHeight)>0:
                    self.screenSize[0] = int(gameWidth[0].childNodes[0].nodeValue)
                    self.screenSize[1] = int(gameHeight[0].childNodes[0].nodeValue)
                else: raise
            else: raise
        except: self.screenSize[0], self.screenSize[1] = size()
        configuredRes = self.config.get('Image','game_resolution')
        configuredScale = self.config.get('Image','calibrated_scale')
        if configuredScale == [-1.0,-1.0] or configuredRes == [-1,-1] or self.screenSize != configuredRes:
            res = f"{self.screenSize[0]}x{self.screenSize[1]}"
            if res in self.presetScales:
                self.scale = self.presetScales[res]
                self.logger.info(f'Game resolution is {res}, using scale {self.scale}')
                self.config.set('Image','game_resolution',str(self.screenSize))
                self.config.set('Image','calibrated_scale',str(self.scale))
            else: self.logger.warn('Game resolution is not in presetScales, you may need to do calibration (Option->Settings->Graphics->Calibrate).')  
        else: self.scale = configuredScale
        self.logger.info(f'Using scale: {self.scale}')
        # Load colormatrix from setting, if it is the same with default colorMatrix then set needMask to False
        if isfile(uiColorXmlPath):
            data = parse(uiColorXmlPath)
            rootConfig = data.documentElement
            guiColorSection = rootConfig.getElementsByTagName('GUIColour')
            if len(guiColorSection)>0:
                defaultSetting = guiColorSection[0].getElementsByTagName('Default')[0]
                matrixRed = [float(val) for val in defaultSetting.getElementsByTagName('MatrixRed')[0].childNodes[0].nodeValue.strip().replace(' ','').split(',')]
                matrixGreen = [float(val) for val in defaultSetting.getElementsByTagName('MatrixGreen')[0].childNodes[0].nodeValue.strip().replace(' ','').split(',')]
                matrixBlue = [float(val) for val in defaultSetting.getElementsByTagName('MatrixBlue')[0].childNodes[0].nodeValue.strip().replace(' ','').split(',')]
                colorMatrix = [matrixRed,matrixGreen,matrixBlue]
                if not operator.eq(colorMatrix,self.originMatrix): # different
                    self.originMatrix = colorMatrix
                    self.needMask = True
                    self.logger.info('Custom GUIColor detected, will attempt to transform')
        self.addTemplates(self.templates)
    
    def addTemplates(self,templates:dict,debug=True) -> None:
        maskedCount = 0
        successCount = 0
        for template in templates:
            isGrayscale = templates[template]['grayscale']
            isScalable = templates[template]['scalable']
            absPath = joinPath(templates[template]['path'])
            img = cv2.imread(absPath)
            y, x = img.shape[:2]
            if img is None: 
                self.logger.warn(f"Failed to load template {template}")
                continue
            if isScalable and self.scale: img = self._resize(img,self.scale)
            if not isGrayscale and self.needMask: # do transforming
                img = self._applyColorMask(img,self.originMatrix)
                maskedCount += 1
            else: img = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY) # grayscale
            self.result[template] = [img,(x,y)]
            successCount += 1
        if debug: self.logger.info(f"Successfully loaded {successCount} templates ({maskedCount} masked), {len(self.templates)-successCount} failed.")

    def matchTemplate(self,template:str,origin:cv2.Mat,confidence:float=0.7,center:bool=True) -> tuple: # match a template in given image, return a tuple with target's center/lefttop with x and y
        templateImg = self.getImage(template)
        th, tw = self.getSize(template)
        result = cv2.matchTemplate(origin,templateImg,cv2.TM_CCOEFF_NORMED)
        _, max_val, _, min_loc = cv2.minMaxLoc(result)
        if max_val<confidence: return (0,0) # template not found
        return (min_loc[0]+(tw/2), min_loc[1]+(th/2)) if center else (min_loc[0], min_loc[1])
    
    def matchDualTemplate(self,template1:str,template2:str,origin:cv2.Mat,minConfidence:float=0.7,center:bool=True) -> tuple: # match two templates and choose one output whose max_val is higher, output: (x,y,templateName)
        templateImg1 = self.getImage(template1)
        templateImg2 = self.getImage(template2)
        th1, tw1 = self.getSize(template1)
        th2, tw2 = self.getSize(template2)
        result1 = cv2.matchTemplate(origin,templateImg1,cv2.TM_CCOEFF_NORMED)
        result2 = cv2.matchTemplate(origin,templateImg2,cv2.TM_CCOEFF_NORMED)
        _, max_val1, _, min_loc1 = cv2.minMaxLoc(result1)
        _, max_val2, _, min_loc2 = cv2.minMaxLoc(result2)
        if max_val1<minConfidence and max_val2<minConfidence: return (0,0,template1) # both template not found
        if max_val1>max_val2: return (min_loc1[0]+(tw1/2), min_loc1[1]+(th1/2), template1) if center else (min_loc1[0], min_loc1[1], template1)
        return (min_loc2[0]+(tw2/2), min_loc2[1]+(th2/2), template2) if center else (min_loc2[0], min_loc2[1], template2)
    
    def calibrate(self,startScale=(1.0,1.0),attempts=10) -> tuple:
        pass

    def getImage(self,template:str) -> cv2.Mat :
        if template in self.result: return self.result[template][0]
        raise IOError('Template not found')
    
    def getSize(self,template:str) -> tuple :
        if template in self.result: return self.result[template][1]
        raise IOError('Template not found')

    def _resize(self,img:cv2.Mat,scale:tuple) -> cv2.Mat:
        img = cv2.resize(img,(0,0),fx=scale[0],fy=scale[1])
        return img
    
    def _applyColorMask(self,img:cv2.Mat,destMatrix:list) -> cv2.Mat :
        """
        Apply a specific color mask based on colorMatrix in E:D Settings
        input: cv2.Mat (BGR)
        """
        rr = destMatrix[0][0]
        rg = destMatrix[0][1]
        rb = destMatrix[0][2]
        gr = destMatrix[1][0]
        gg = destMatrix[1][1]
        gb = destMatrix[1][2]
        br = destMatrix[2][0]
        bg = destMatrix[2][1]
        bb = destMatrix[2][2]
        height = img.shape[0]
        width = img.shape[1]
        for row in range(height):
            for col in range(width):
                # B G R
                rVal = img[row,col,2]
                gVal = img[row,col,1]
                bVal = img[row,col,0]
                rRes = int(rVal*rr)+int(gVal*gr)+int(bVal*br)
                gRes = int(rVal*rg)+int(gVal*gg)+int(bVal*bg)
                bRes = int(rVal*rb)+int(gVal*gb)+int(bVal*bb)
                if rRes>255: rRes=255
                if gRes>255: gRes=255
                if bRes>255: bRes=255
                img[row,col,2] = rRes
                img[row,col,1] = gRes
                img[row,col,0] = bRes
        return img
