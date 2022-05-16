# An script example
from gameui import Logger, ScriptSession 
from scripts.ScriptBase import ScriptBase
from utils.utils import *
from PySide2.QtWidgets import QGridLayout, QVBoxLayout, QLabel, QPushButton, QGroupBox # import widgets you want to add to 'Script' box here
class example(ScriptBase): # class name must be same with filename
    description ='''
    example.py: A script example for you to write your own EDAutopilot script
    '''
    def __init__(self,logger:Logger=None,layout:QGridLayout=None,session:ScriptSession=None): 
        super().__init__(logger,layout,session)
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
        session = self.session
        logger = self.logger
        align = False
        while not keyboard.is_pressed('end'):
            if keyboard.is_pressed('o'): 
                align = True
            if align: 
                align = session.align()
            session.sleep(0.01)
        
    def _onClickButton(self):
        self.logger.info('clicked')