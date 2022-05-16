from gameui import Logger, ScriptSession
from PySide2.QtWidgets import QGridLayout
from PySide2.QtCore import QObject
class ScriptBase(QObject):
    description ='''
    '''
    def __init__(self,logger:Logger=None,layout:QGridLayout=None,session:ScriptSession=None) -> None:
        """
        Initialize the script including logger (print message to Logging area) 
        and layout (provides a QGridLayout so you can add widgets on the Script area) 
        and session (control the game)
        """
        super().__init__()
        self.logger = logger
        self.layout = layout
        self.session = session
        self._print_description()
    
    def _print_description(self) -> None:
        """
        Print the defined description as [TIP]
        """
        self.logger.tip(self.description)
    
    def run(self) -> None:
        """
        Main entrance for the script. Infinite loop is accepted here.
        """
        pass

    