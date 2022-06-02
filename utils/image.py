import cv2
import operator
import pathlib
from pyautogui import size
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
graphicsXmlPath = environ['LOCALAPPDATA']+"\Frontier Developments\Elite Dangerous\Options\Graphics\GraphicsConfigurationOverride.xml"
class Screen:
    # "Region name": {"loc":[leftTopX%,leftTopY%,rightBottomX%,rightBottomY%],"filter":cv2.inrange}
    regions = {
        "compass": {""},
    }
    def __init__(self) -> None:
        pass
    def screenshot(self) -> cv2.Mat:
        pass
    def getRegion(self,regionName) -> cv2.Mat:
        pass
class Image:
    # "Template name" : {"grayscale","scalable","path"}
    # Any templates set "grayscale" to False will attempt to be converted by colorMatrix
    templates = {
        "destCircle": {"grayscale": False,"scalable": True,"path": "templates/dest_circle.png"},
        # "destCircle_occluded": {"grayscale": "True","scalable": "True","path": "templates/dest_circle_occluded.png"},
        # "compass": {"grayscale": True,"scalable": True,"path": "templates/compass.png"}
    }
    # "Template name" : converted img(cv2)
    result = {}
    originMatrix = [
    # R G B
    [1,0,0], #<MatrixRed>
    [0,1,0], #<MatrixGreen>
    [0,0,1]  #<MatrixBlue>
    ]
    presetScales = {
        '1920x1080': [1.0,1.0],
        '2560x1440': [1.33,1.33]
    }
    scale = [1.0,1.0]
    screenSize = [1920,1080]
    needMask = False
    logger = None
    def __init__(self,logger,config) -> None:
        self.config = config
        self.logger = logger
        # Load screen resolution and prepare to scaling
        self.screenSize[0], self.screenSize[1] = size()
        configuredScale = self.config.get('Image','calibrated_scale')
        if configuredScale == [-1.0,-1.0]:
            res = str(self.screenSize[0])+'x'+str(self.screenSize[1])
            if res in self.presetScales:
                self.scale = self.presetScales[res]
                self.logger.info(f'Screen resolution is {res}, using scale {self.scale}')
                self.config.set('Image','calibrated_scale',str(self.scale))
            else: self.logger.warn('Screen resolution is not in presetScales, you may need to do calibration (Option->Settings->Graphics->Calibrate).')  
        else: self.scale = configuredScale
        self.logger.info(f'Using scale: {self.scale}')
        # Load colormatrix from setting, if it is the same with default colorMatrix then set needMask to False
        if isfile(graphicsXmlPath):
            data = parse(graphicsXmlPath)
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
            if img is None: 
                self.logger.warn("Failed to load template "+template)
                continue
            if isScalable and self.scale is not None: img = self._resize(img,self.scale)
            if not isGrayscale and self.needMask: # do transforming
                img = self._applyColorMask(img,self.originMatrix)
                maskedCount += 1
            else: img = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY) # grayscale
            self.result[template] = img
            successCount += 1
        if debug: self.logger.info(f"Successfully loaded {successCount} templates ({maskedCount} masked), {len(self.templates)-successCount} failed.")

    def matchTemplate(self):
        pass
    
    def calibrate(self,startScale=(1.0,1.0),attempts=10) -> tuple:
        pass

    def get(self,template) -> cv2.Mat :
        if template in self.result: return self.result[template]
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

if __name__ == "__main__":
    #image = Image()
    pass
