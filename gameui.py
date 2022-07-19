from PySide2.QtGui import QImage, QPixmap, QTextCharFormat, QColor, QBrush, QCursor
from PySide2.QtWidgets import QApplication, QFileDialog, QLabel, QMenu, QAction, QGridLayout, QWidget
from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import QThread, QObject, Signal
from queue import Queue
from dataclasses import dataclass
from utils.utils import *
from utils.config import Config
from utils.session import *
from datetime import datetime
import sys
import webbrowser
import importlib
# 3 subthreads + 1 main thread (UI): 
# I/O Thread: handle journal and status reading + watchdog
# Image Thread: handle imageProcessing
# Scripts Thread: handle scripts and key sending (dynamic import)
# Logger Thread: handle logging from different threads and provide a mediation to prevent crashing main thread

IO_TIMEOUT = 1.0 # I/O thread timeout(preventing heavy io)
IMAGE_MINIMUM_TIMEOUT = 0.2 # sleep for # in each cycle to prevent heavy CPU load
IMAGE_WAITING_TIMEOUT = 5 # Re-detecing timeout if ImageThread found no process instance

rootPath = os.path.split(os.path.realpath(__file__))[0]
mainWindowPath = f"{rootPath}/assets/main.ui"
subWindowPath = f"{rootPath}/assets/sub.ui"
defaultLogPrefix = 'autopilot'

## LOGGER THREAD START
@dataclass
class LogMsg:
    text: str
    color: str
class Logger:
    init_file = False # Logging before the config loaded
    logPath = None
    def __init__(self,queue:Queue,logPath:str=None,init:bool=False):
        self.queue = queue
        self.logPath = logPath
        self.init_file = init
    def setInitFile(self,logPath): 
        self.init_file = True
        self.logPath = logPath
        nowTime = datetime.now().strftime('%Y-%m-%d')
        with open(self.logPath, "w") as dest:
            dest.write(f"# Autopilot log starts at {nowTime}\n")
    def _outputText(self,message:str,color='black',toFile=True):
        if toFile and self.init_file and self.logPath is not None:
            msgStack = traceback.format_stack(limit=3)[0]
            file,line=stackAnalyser(msgStack)
            with open(self.logPath, "a") as dest:
                dest.write(f"{file}:{line} - {message}\n")
        msg = LogMsg(message,color)
        self.queue.put(msg)
    def tip(self,message:str):
        msg = f"[{datetime.now().strftime('%H:%M:%S')}][TIP] {message}"
        self._outputText(msg,color='blue',toFile=False) # don't save tips
    def debug(self,message:str): 
        msg = f"[{datetime.now().strftime('%H:%M:%S')}][DEBUG] {message}"
        self._outputText(msg,color='black',toFile=False) # don't save debug
    def info(self,message:str,color='black'):
        msg = f"[{datetime.now().strftime('%H:%M:%S')}][INFO] {message}"
        self._outputText(msg,color=color)
    def warn(self,message:str):
        msg = f"[{datetime.now().strftime('%H:%M:%S')}][WARN] {message}"
        self._outputText(msg,color='orange')
    def critical(self,message:str):
        msg = f"[{datetime.now().strftime('%H:%M:%S')}][CRITICAL] {message}"
        self._outputText(msg,color='red')
class LogThread(QThread):
    _logSignal = Signal(LogMsg)
    def __init__(self):
        super().__init__()
        self.queue = Queue()
        self.logger = Logger(self.queue)
    def getLogger(self) -> Logger:
        return self.logger
    def initFile(self,override:bool): 
        logPath = '{}/{}.log'.format(rootPath,defaultLogPrefix)
        if override and isfile(logPath):
            logIndex = 0
            for f in listdir(rootPath):
                if isfile(join(rootPath, f)) and f.startswith(defaultLogPrefix):
                    last = os.path.splitext(f)[0][-1]
                    if last.isdigit(): logIndex = int(last)
            logIndex += 1
            logPath = f"{rootPath}/{defaultLogPrefix}-{logIndex}.log"
        self.logger.setInitFile(logPath)
    def run(self):
        while True:
            result = self.queue.get()
            self._logSignal.emit(result)
## LOGGER THREAD END

## I/O THREAD START
@dataclass
class IOMsg:
    journal: Journal
    stateList: list
    guiFocus: str
class IOThread(QThread):
    _ioSignal = Signal(IOMsg)
    usingWatchdog = False
    def __init__(self,watchDog,logger:Logger=None) -> None:
        super().__init__()
        self.usingWatchdog = watchDog
        self.logger = logger
    def run(self) -> None:
        while True:
            journal = parseLogs(logger=self.logger)
            stateList = showAllTrueStatus()
            guiFocus = getGuiFocus()
            data = IOMsg(journal,stateList,guiFocus)
            self._ioSignal.emit(data)
            isEmergency = 'UnderAttack' in journal.signs or 'Scanned' in journal.signs
            if isEmergency and self.usingWatchdog and isProcessExist(globalProcessName): # Force terminating...
                if self.logger is not None: self.logger.critical("Watchdog: killing process")
                else: print("Watchdog: killing process")
                killProcess(globalProcessName)
            QThread.sleep(IO_TIMEOUT)
## I/O THREAD END

## SCRIPTS THREAD START
# Dynamic import scripts file
# Input: Main -> ScriptThread (status,journal,navpoints,etc)
# Output: ScriptThread -> Main ()
class ScriptThread(QThread):
    # _inSignal = Signal(object)
    # _outSignal = Signal(object)
    def __init__(self,moduleBase,logger:Logger=None,layout:QGridLayout=None,keysDict:dict=None,templates:Image=None,screen:Screen=None):
        super().__init__()
        self.setTerminationEnabled(True)
        self.logger = logger
        self.layout = layout # pass a gridLayout
        self.templates = templates
        self.screen = screen
        self._module = importlib.import_module(f'scripts.{moduleBase}') # load 'scripts.moduleBase' module
        self._class = getattr(self._module, moduleBase) # class name is the same with module name
        # initialize instance
        self.session = ScriptSession(logger=self.logger,keysDict=keysDict,image=self.templates,screen=self.screen)
        self.instance = self._class(logger=self.logger,layout=self.layout,session=self.session,templates=self.templates) 

    def onReceiveData(self,data:ScriptInputMsg):
        self.session._update(data)

    def run(self):
        try:
            self.instance.run()
        except Exception:
            self.logger.critical(traceback.format_exc())

## SCRIPTS THREAD END

## IMAGE THREAD START
@dataclass
class ImageMsg:
    offsetX: int
    offsetY: int
    isAligned: bool
    isFocused: bool
    fps: int
    windowLeftX: int
    windowTopY: int
class ImageThread(QThread):
    _imageSignal = Signal(ImageMsg)
    def __init__(self,screen:Screen,image:Image,logger:Logger=None):
        super().__init__()
        self.logger = logger
        self.screen = screen
        self.image = image
    
    def getNavPoint(self,compassImg) -> tuple : # return offsetX and offsetY 
        compassLeftTop = self.image.matchTemplate('compass',compassImg,confidence=0.45,center=False)
        if compassLeftTop == (0,0): return (0,0) # can't get compassImage, left it standby
        compassSize = self.image.getSize('compass')
        trimX, trimY = int(compassSize[0]*0.2), int(compassSize[1]*0.2)
        compassCropped = compassImg[compassLeftTop[1]-trimY:compassLeftTop[1]+compassSize[1]+trimY,compassLeftTop[0]-trimX:compassLeftTop[0]+compassSize[0]+trimX]
        navPointCenter = self.image.matchDualTemplate('navPoint','navPointHollow',compassCropped,minConfidence=0.7)
        compassImgSizeY, compassImgSizeX = compassCropped.shape[:2]
        offsetX = navPointCenter[0]-compassImgSizeX/2
        offsetY = navPointCenter[1]-compassImgSizeY/2
        return (offsetX,offsetY)

    def run(self):
        isAligned = 0
        windowHwnd = win32gui.FindWindow(None,globalWindowName)
        while True:
            try: # already has windowHwnd
                gameCoord = getWindowRectByHwnd(windowHwnd)
            except: # gameHwnd changed
                try: 
                    gameCoord,windowHwnd = getWindowRectByName(globalWindowName)
                except Exception as e: 
                    if 'Invalid window handle' in str(e):
                        self.logger.critical(f'ImageThread: No game process found, retrying in {IMAGE_WAITING_TIMEOUT} sec.')
                        time.sleep(IMAGE_WAITING_TIMEOUT)
                        continue
                    else: self.logger.critical(traceback.format_exc())
            try:
                startTime = time.time()
                isFocused = isForegroundWindow(globalWindowName,windowHwnd)
                originImg = self.screen.screenshot()
                originGrayImg = cv2.cvtColor(originImg,cv2.COLOR_BGR2GRAY)
                centerImg = self.screen.getRegion('center',img=originGrayImg)
                compassImg = self.screen.getRegion('compass',img=originGrayImg)
                destCircleImg = self.image.getImage('destCircle')
                isAligned = 1 if checkAlignWithTemplate(centerImg,destCircleImg) else 0
                (offsetX,offsetY) = self.getNavPoint(compassImg)
                # print(offsetX,offsetY)
                elapsedTime = time.time()-startTime
                fps = int(1.0/elapsedTime)
                message = ImageMsg(offsetX,offsetY,isAligned,isFocused,fps,gameCoord[0],gameCoord[1])
                self._imageSignal.emit(message)
            except:
                self.logger.critical(traceback.format_exc())
            time.sleep(IMAGE_MINIMUM_TIMEOUT)
## IMAGE THREAD END
class Main(QObject):
    scriptPath = ''
    scriptName = ''
    usingWatchdog = False
    isDebug = True
    offsetX = offsetY = 0 
    isAligned = isFocused = False
    fps = 0
    windowLeftX = windowTopY = 0
    stateList = []
    journal = Journal()
    guiFocus = 'NoFocus'
    shipLoc = ''
    shipTarget = ''

    _outputSignalToScript = Signal(ScriptInputMsg)

    def __init__(self):
        super().__init__()
        self.mainUI = QUiLoader().load(mainWindowPath)
        self.subUI = QUiLoader().load(subWindowPath)
        self.mainUI.setWindowTitle('EDAutopilot v2')
        # self.logger = Logger(self.mainUI.logText,toFile=True) # start logger
        self.thread_log = LogThread()
        self.logger = self.thread_log.getLogger()
        self.thread_log._logSignal.connect(self.onReceiveLog)
        self.thread_log.start()

        self.config = Config(logger=self.logger)
        if self.config.get('Main','log_to_file'): self.thread_log.initFile(self.config.get('Main','override_previous_logs'))
        self.keysDict = init_keybinds(self.logger)
        
        self.mainUI.actionScriptName.setDisabled(True)

        self.thread_io = IOThread(self.usingWatchdog,logger=self.logger)
        self.thread_io._ioSignal.connect(self.updateStatus)
        self.thread_io.start()

        self.screen = Screen(logger=self.logger,config=self.config)
        self.image_templates = Image(logger=self.logger,config=self.config)
        self.thread_image = ImageThread(logger=self.logger,screen=self.screen,image=self.image_templates)
        self.thread_image._imageSignal.connect(self.updateImage)
        self.thread_image.start()
        self.thread_script = None # initialize in loadScript()

        self.mainUI.logText.customContextMenuRequested.connect(self._onRightClickLog) # connect to ContextMenu in logging area (Copy, debug view, clear screen...)

        self.mainUI.actionLoadScript.triggered.connect(lambda: self.loadScript(None))
        self.mainUI.actionStopScript.triggered.connect(self.stopScript)
        self.mainUI.actionSettings.triggered.connect(self.onSettings)
        self.mainUI.actionAbout.triggered.connect(self.onAbout) 
        self.mainUI.actionExit.triggered.connect(self.onExit)
        QApplication.instance().aboutToQuit.connect(self.onExit)

        self.mainUI.actionScriptName.setText('(Empty)')
        self.locationLabel = QLabel('Loc: None'.ljust(49))
        self.targetLabel = QLabel('Target: None'.ljust(49))
        self.alignedLabel = QLabel('Align: 0'.ljust(9))
        self.fpsLabel = QLabel('FPS: 0'.ljust(8))
        self.scriptStatusLabel = QLabel('Idle'.ljust(20))
        self.mainUI.statusBar().addWidget(self.locationLabel)
        self.mainUI.statusBar().addWidget(self.targetLabel)
        self.mainUI.statusBar().addWidget(self.alignedLabel)
        self.mainUI.statusBar().addWidget(self.fpsLabel)
        self.mainUI.statusBar().addWidget(self.scriptStatusLabel)

        self._setScriptActionsState(True)

        self.showDebugWindow = True if self.config.get('GUI','show_debug_window') is True else False

        if self.config.get('GUI','load_default_on_startup'):
            defaultPath = self.config.get('GUI','default_script')
            if defaultPath is not None: self.loadScript(path=defaultPath)
        else: self.config.set('GUI','default_script','')

    def updateStatus(self,data:IOMsg):
        # unpack & update
        self.journal = data.journal
        self.stateList = data.stateList
        self.guiFocus = data.guiFocus
        if self.journal.nav.location: self.shipLoc = self.journal.nav.location
        if self.journal.nav.target: self.shipTarget = self.journal.nav.target

        # display
        self.locationLabel.setText((f'Loc: {self.shipLoc}').ljust(49))
        self.targetLabel.setText((f'Target: {self.shipTarget}').ljust(49))

        if self.thread_script: # check if the script thread alives
            if not self.thread_script.isRunning(): # terminated
                self.stopScript()
            else: self.scriptStatusLabel.setText('Running'.ljust(20))
    
    def updateImage(self,data:ImageMsg):
        # unpack
        # offsetX,offsetY,isAligned,isFocused,fps,windowLeftX,windowTopY
        #self.targetX = data.targetX
        #self.targetY = data.targetY
        #self.navCenter = data.navCenter
        self.offsetX = data.offsetX
        self.offsetY = data.offsetY
        self.isAligned = data.isAligned
        self.isFocused = data.isFocused
        self.fps = data.fps
        self.windowLeftX = data.windowLeftX
        self.windowTopY = data.windowTopY

        # display
        self.fpsLabel.setText((f'FPS: {self.fps}').ljust(8))
        self.alignedLabel.setText((f'Align: {1 if self.isAligned else 0}').ljust(9))

        # try to send data to ScriptThread
        if self.thread_script:
            # pack & form a ScriptInputMsg
            outputMsg = ScriptInputMsg(self.isAligned,self.isFocused,self.stateList,self.journal,self.guiFocus,self.offsetX,self.offsetY,self.windowLeftX,self.windowTopY)
            # then emit it
            self._outputSignalToScript.emit(outputMsg)
    
    def showImage(self,img:cv2.Mat,name=1) -> None : # only works when showDebugWindow is set
        if not self.showDebugWindow: return
        cv2.imshow(f'Debug Window {str(name)}',img)
        cv2.waitKey(0)

    def loadScript(self,path=None):
        if path is None: 
            try:
                filePath = QFileDialog.getOpenFileName(self.mainUI,'Choose script',os.path.join(os.getcwd(),'scripts'), "Python file (*.py)")[0]
            except Exception:
                self.logger.critical(traceback.format_exc())
            finally: 
                if filePath is None or filePath == '': 
                    self.logger.critical('Loaded an empty file')
                    self.stopScript()
                    return
                else: self.config.set('GUI','default_script',filePath)
        else: filePath = path
        self.scriptPath = filePath
        _,self.scriptName = os.path.split(self.scriptPath)
        self.mainUI.actionScriptName.setText(self.scriptName)
        self.scriptName = self.scriptName[:-3] # remove '.py'
        self.logger.info(f'Loading script: {self.scriptPath}',color='green')
        try:
            self.thread_script = ScriptThread(self.scriptName,logger=self.logger,layout=self.mainUI.scriptLayout,keysDict=self.keysDict,templates=self.image_templates,screen=self.screen)
            self._outputSignalToScript.connect(self.thread_script.onReceiveData)
            self.thread_script.start()
        except Exception:
            self.logger.critical(traceback.format_exc())
            self.stopScript()
        else: # loaded successfully
            self._setScriptActionsState(False)

    def stopScript(self):
        if self.thread_script is None:
            self._setScriptActionsState(True)
            self.mainUI.actionScriptName.setText('(Empty)')
        else:
            if self.thread_script.isRunning(): 
                self.thread_script.terminate()
            if not self.thread_script.isRunning(): # terminated
                self._setScriptActionsState(True)
                self.thread_script = None
                self.mainUI.actionScriptName.setText('(Empty)')
        widgetCounts = self.mainUI.scriptLayout.count() # going to remove all created widgets
        if widgetCounts>0:
            self.logger.info(f'Script exited, cleared {widgetCounts} widget(s)')
            for i in range(widgetCounts):
                item = self.mainUI.scriptLayout.itemAt(i)
                if item.widget(): item.widget().deleteLater()
                else: self.mainUI.scriptLayout.removeItem(item)

    def onReceiveLog(self,data:LogMsg):
        format = QTextCharFormat()
        format.setForeground(QBrush(QColor(data.color)))
        self.mainUI.logText.setCurrentCharFormat(format)
        self.mainUI.logText.appendPlainText(data.text)
        format.setForeground(QBrush(QColor('black'))) # restore to default color
        self.mainUI.logText.setCurrentCharFormat(format)
    
    def _setScriptActionsState(self,state:bool): # True means 'Load' is active and 'Stop' can't be triggered
        self.mainUI.actionStopScript.setDisabled(state)
        self.mainUI.actionLoadScript.setDisabled(bool(1-state))
        self.mainUI.actionScriptName.setChecked(bool(1-state))
        self.scriptStatusLabel.setText('{:<20}'.format('Idle' if state else 'Running'))

    def _onRightClickLog(self):
        self.mainUI.logBoxMenu = QMenu()
        self.mainUI.logBoxActionCopy = QAction('Copy')
        self.mainUI.logBoxActionCopy.setShortcut('Ctrl+C')
        self.mainUI.logBoxMenu.addAction(self.mainUI.logBoxActionCopy)
        self.mainUI.logBoxActionClear = QAction('Clear')
        self.mainUI.logBoxMenu.addAction(self.mainUI.logBoxActionClear)
        self.mainUI.logBoxActionDebug = QAction('Debug')
        self.mainUI.logBoxActionDebug.setCheckable(True)
        self.mainUI.logBoxActionDebug.setChecked(self.isDebug)
        self.mainUI.logBoxMenu.addAction(self.mainUI.logBoxActionDebug)

        self.mainUI.logBoxActionCopy.triggered.connect(self.mainUI.logText.copy)
        self.mainUI.logBoxActionClear.triggered.connect(self.mainUI.logText.clear)
        self.mainUI.logBoxActionDebug.triggered.connect(self._onClickDebug)
        self.mainUI.logBoxMenu.popup(QCursor.pos())
    
    def _onClickDebug(self):
        self.isDebug = bool(1-self.isDebug)
    def onSettings(self):
        self.subUI.show()

    def onAbout(self):
        webbrowser.open('https://github.com/Matrixchung/EDAutopilot-v2', new=1)
    
    def onExit(self): # release resources
        cv2.destroyAllWindows()
        if self.thread_script: self.thread_script.terminate()
        self.thread_io.terminate()
        self.thread_image.terminate()
        self.logger.info("Resource cleared, program will exit.")
        self.thread_log.terminate()
        QApplication.instance().quit()

if __name__ == '__main__':
    app = QApplication([])
    main = Main()
    main.mainUI.show()
    sys.exit(app.exec_())