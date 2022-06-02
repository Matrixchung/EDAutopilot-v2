from PySide2.QtGui import QImage, QPixmap, QTextCharFormat, QColor, QBrush, QCursor
from PySide2.QtWidgets import QApplication, QFileDialog, QPlainTextEdit, QLabel, QMenu, QAction, QGridLayout
from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import QThread, QObject, Signal
from queue import Queue
from dataclasses import dataclass
from utils.utils import *
from utils.config import Config
from utils.session import ScriptInputMsg, ScriptSession
from utils.image import Image
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
mainWindowPath = rootPath+'/assets/main.ui'
subWindowPath = rootPath+'/assets/sub.ui'
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
        open(self.logPath, "w")
    def _outputText(self,message:str,color='black',toFile=True):
        if toFile and self.init_file and self.logPath is not None:
            msgStack = traceback.format_stack(limit=3)[0]
            file,line=stackAnalyser(msgStack)
            with open(self.logPath, "a") as dest:
                dest.write(file+":"+str(line)+" - "+message+"\n")
        msg = LogMsg(message,color)
        self.queue.put(msg)
    def tip(self,message:str):
        msg = ('['+datetime.now().strftime('%H:%M:%S')+'][TIP] '+str(message))
        self._outputText(msg,color='blue',toFile=False) # don't save tips
    def debug(self,message:str): 
        msg = ('['+datetime.now().strftime('%H:%M:%S')+'][DEBUG] '+str(message))
        self._outputText(msg,color='black',toFile=False) # don't save debug
    def info(self,message:str,color='black'):
        msg = ('['+datetime.now().strftime('%H:%M:%S')+'][INFO] '+str(message))
        self._outputText(msg,color=color)
    def warn(self,message:str):
        msg = ('['+datetime.now().strftime('%H:%M:%S')+'][WARN] '+str(message))
        self._outputText(msg,color='orange')
    def critical(self,message:str):
        msg = ('['+datetime.now().strftime('%H:%M:%S')+'][CRITICAL] '+str(message))
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
            logPath = '{}/{}-{}.log'.format(rootPath,defaultLogPrefix,logIndex)
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
    def __init__(self,moduleBase,logger:Logger=None,layout:QGridLayout=None,keysDict:dict=None,templates:Image=None):
        super().__init__()
        self.setTerminationEnabled(True)
        self.logger = logger
        self.layout = layout # pass a gridLayout
        self.templates = templates
        self._module = importlib.import_module('scripts.'+moduleBase) # load 'scripts.moduleBase' module
        self._class = getattr(self._module, moduleBase) # class name is the same with module name
        # initialize instance
        self.session = ScriptSession(logger=self.logger,keysDict=keysDict)
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
    targetX: int
    targetY: int
    navCenter: int
    isAligned: bool
    isFocused: bool
    fps: int
    windowLeftX: int
    windowTopY: int
class ImageThread(QThread):
    _imageSignal = Signal(ImageMsg)
    def __init__(self,logger:Logger=None):
        super().__init__()
        self.logger = logger
    def run(self):
        isAligned = 0
        windowHwnd = win32gui.FindWindow(None,globalWindowName)
        while True:
            try: # already has windowHwnd
                gameCoord = getWindowRectByHwnd(windowHwnd)
            except: # gameHwnd changed
                # self.logger.critical(traceback.format_exc())
                try: 
                    gameCoord,windowHwnd = getWindowRectByName(globalWindowName)
                except Exception as e: 
                    if 'Invalid window handle' in str(e):
                        self.logger.critical('ImageThread: No game process found, retrying in '+str(IMAGE_WAITING_TIMEOUT)+' sec.')
                        time.sleep(IMAGE_WAITING_TIMEOUT)
                        continue
                    else: self.logger.critical(traceback.format_exc())
            try:
                startTime = time.time()
                isFocused = isForegroundWindow(globalWindowName,windowHwnd)
                img = pyautogui.screenshot(region=gameCoord)
            
                gameResolution = gameCoord[2],gameCoord[3]
                # gameCenterActual = gameCoord[0]+gameCoord[2]/2,gameCoord[1]+gameCoord[3]/2 
                gameCenterRel = gameCoord[2]/2,gameCoord[3]/2 

                # outsideOffsetY = (gameCoord[3]/3)*2
                cv2OriginImg = cv2.cvtColor(np.asarray(img),cv2.COLOR_RGB2BGR)
                # cv2ShowImg = cv2OriginImg.copy() # ShowImg for Overlay
                cv2GrayImg = cv2.cvtColor(cv2OriginImg,cv2.COLOR_BGR2GRAY)

                centerImg = cv2GrayImg[int(gameCenterRel[1]-180):int(gameCenterRel[1]+180),int(gameCenterRel[0]-220):int(gameCenterRel[0]+220)]
                compassImg = cv2GrayImg[int(gameResolution[1]/1.63):int(gameResolution[1]/1.06),int(gameResolution[0]/4.04):int(gameResolution[0]/2.02)] # Magic Number: size for compass img
            
                compassOriginImg = cv2OriginImg[int(gameResolution[1]/1.63):int(gameResolution[1]/1.06),int(gameResolution[0]/4.04):int(gameResolution[0]/2.02)]
                compassHsv = cv2.cvtColor(compassOriginImg,cv2.COLOR_BGR2HSV)
                compassShowImg = compassOriginImg.copy() # screen overlay

                if checkAlignWithTemplate(centerImg,destCircleImg) is True: isAligned = 1
                else: isAligned = 0
                elapsedTime = time.time()-startTime
                # (targetX,targetY),navCenter,compassShowImg,navShowImg = getNavPointsByCompass(compassImg,compassShowImg,compassHsv) 
                (targetX,targetY),navCenter = getNavPointsByCompass(compassImg,compassShowImg,compassHsv)
                fps = int(1.0/elapsedTime)
                message = ImageMsg(targetX,targetY,navCenter,isAligned,isFocused,fps,gameCoord[0],gameCoord[1])
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
    targetX = targetY = navCenter = 0
    isAligned = isFocused = False
    fps = 0
    windowLeftX = windowTopY = 0
    stateList = []
    journal = Journal()
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

        self.image_templates = Image(logger=self.logger,config=self.config)
        self.thread_image = ImageThread(logger=self.logger)
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

        if self.config.get('GUI','load_default_on_startup'):
            defaultPath = self.config.get('GUI','default_script')
            if defaultPath is not None: self.loadScript(path=defaultPath)

    def updateStatus(self,data:IOMsg):
        # unpack & update
        self.journal = data.journal
        self.stateList = data.stateList
        self.guiFocus = data.guiFocus
        if self.journal.nav.location is not None: self.shipLoc = self.journal.nav.location
        if self.journal.nav.target is not None: self.shipTarget = self.journal.nav.target

        # display
        self.locationLabel.setText(('Loc: '+self.shipLoc).ljust(49))
        self.targetLabel.setText(('Target: '+self.shipTarget).ljust(49))

        if self.thread_script is not None: # check if the script thread alives
            if not self.thread_script.isRunning(): # terminated
                self.stopScript()
            else: self.scriptStatusLabel.setText('Running'.ljust(20))
    
    def updateImage(self,data:ImageMsg):
        # unpack
        # targetX,targetY,navCenter,isAligned,isFocused,fps,windowLeftX,windowTopY
        self.targetX = data.targetX
        self.targetY = data.targetY
        self.navCenter = data.navCenter
        self.isAligned = data.isAligned
        self.isFocused = data.isFocused
        self.fps = data.fps
        self.windowLeftX = data.windowLeftX
        self.windowTopY = data.windowTopY

        # display
        self.fpsLabel.setText(('FPS: '+str(self.fps)).ljust(8))
        self.alignedLabel.setText(('Align: '+(str(1) if self.isAligned else str(0))).ljust(9))

        # try to send data to ScriptThread
        if self.thread_script is not None:
            # pack & form a ScriptInputMsg
            outputMsg = ScriptInputMsg(self.isAligned,self.isFocused,self.stateList,self.journal,self.guiFocus,self.targetX,self.targetY,self.navCenter,self.windowLeftX,self.windowTopY)
            # then emit it
            self._outputSignalToScript.emit(outputMsg)

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
        self.logger.info('Loading script: '+self.scriptPath,color='green')
        try:
            self.thread_script = ScriptThread(self.scriptName,logger=self.logger,layout=self.mainUI.scriptLayout,keysDict=self.keysDict)
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
            self.logger.info('Script exited, cleared '+str(widgetCounts)+' widget(s)')
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
        webbrowser.open('https://github.com/Matrixchung/EDAutopilot', new=1)
    
    def onExit(self): # release resources
        if self.thread_script is not None: self.thread_script.terminate()
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