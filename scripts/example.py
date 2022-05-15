# An script example
from gameui import Logger, ScriptSession 
from utils.utils import *
from PySide2.QtWidgets import QGridLayout, QVBoxLayout, QLabel, QPushButton, QGroupBox # import widgets you want to add to 'Script' box here
import time
class example: # class name must be same with filename
    def __init__(self,logger:Logger=None,layout:QGridLayout=None,scriptSession:ScriptSession=None): 
        self.logger = logger
        self.layout = layout
        # Initialize scripts and layout here

        ### Example groupbox_1
        groupbox_1 = QGroupBox('Description')
        label1 = QLabel('Example')
        layout_1 = QVBoxLayout()
        layout_1.addWidget(label1)
        groupbox_1.setLayout(layout_1)

        ### Example groupbox_2
        groupbox_2 = QGroupBox('Controls')
        button1 = QPushButton('test')
        layout_2 = QVBoxLayout()
        layout_2.addWidget(button1)
        groupbox_2.setLayout(layout_2)

        self.layout.addWidget(groupbox_1,0,0,-1,1)
        self.layout.addWidget(groupbox_2,0,1,-1,1)
        button1.pressed.connect(self._onClickButton) # you can connect signals

        self.logger.info('example: __init__ is loaded')

    def run(self): # Program entrance, you can use infinite loop or anything here
        self.logger.info('run() is invoked')
        while True:
            time.sleep(1)
        
    def _onClickButton(self):
        self.logger.info('clicked')