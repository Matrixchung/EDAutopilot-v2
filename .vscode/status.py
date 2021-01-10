# https://elite-journal.readthedocs.io/en/latest/Status%20File/
from os import environ, listdir
from os.path import join, isfile, getmtime, abspath
from ctypes import windll
import win32file
import json
import traceback
savedGamePath = environ['USERPROFILE'] + "\Saved Games\Frontier Developments\Elite Dangerous"
status = {
    'Docked': False,
    'Landed': False,
    'LandingGearDown': False,
    'ShieldsUp': False,
    'Supercruise': False,
    'FlightAssistOff': False,
    'HardpointsDeployed': False,
    'InWing': False,
    'LightsOn': False,
    'CargoScoopDeployed': False,
    'SilentRunning': False,
    'ScoopingFuel': False,
    'SRVHandbrake': False,
    'SRVTurret': False,
    'SRVUnderShip': False,
    'SRVDriveAssist': False,
    'SRVHighBeam': False,
    'FSDMassLocked': False,
    'FSDCharging': False,
    'FSDCooldown': False,
    'FSDJump': False,
    'LowFuel': False,
    'Overheating': False,
    'HasLatLong': False,
    'IsInDanger': False,
    'BeingInterdicted': False,
    'InMainShip': False,
    'InFighter': False,
    'InSRV': False,
    'InAnalysisMode': False,
    'NightVision': False,
    'AltitudeFromAverageRadius': False,
    'GUIFocus': 'NoFocus' # NoFocus (default)
}
flags = {
    'Docked': 0x00000001,
    'Landed': 0x00000002,
    'LandingGearDown': 0x00000004,
    'ShieldsUp': 0x00000008,
    'Supercruise': 0x00000010,
    'FlightAssistOff': 0x00000020,
    'HardpointsDeployed': 0x00000040,
    'InWing': 0x00000080,
    'LightsOn': 0x00000100,
    'CargoScoopDeployed': 0x00000200,
    'SilentRunning': 0x00000400,
    'ScoopingFuel': 0x00000800,
    'SRVHandbrake': 0x00001000,
    'SRVTurret': 0x00002000,
    'SRVUnderShip': 0x00004000,
    'SRVDriveAssist': 0x00008000,
    'SRVHighBeam': 0x80000000,
    'FSDMassLocked': 0x00010000,
    'FSDCharging': 0x00020000,
    'FSDCooldown': 0x00040000,
    'FSDJump': 0x40000000,
    'LowFuel': 0x00080000,
    'Overheating': 0x00100000,
    'HasLatLong': 0x00200000,
    'IsInDanger': 0x00400000,
    'BeingInterdicted': 0x00800000,
    'InMainShip': 0x01000000,
    'InFighter': 0x02000000,
    'InSRV': 0x04000000,
    'InAnalysisMode': 0x08000000,
    'NightVision': 0x10000000,
    'AltitudeFromAverageRadius': 0x20000000
}
def isFileOpen(filePath):
    try:
        fHandle = win32file.CreateFile(filePath,win32file.GENERIC_READ,0,None,win32file.OPEN_EXISTING,win32file.FILE_ATTRIBUTE_NORMAL,None)
        if int(fHandle) == win32file.INVALID_HANDLE_VALUE: # already opened and occupied
            return True
        win32file.CloseHandle(fHandle)
        return False
    except:
        return True
def getFlagsAndFocusByJSON(statusPath=None):
    if not statusPath: # Default Saving Path
        statusPath = savedGamePath+r"\Status.json"
    data = {'Flags':0,'GuiFocus':''}
    try :
        if isFileOpen(statusPath) is not True:
            with open(statusPath,'r') as f:
                if f is not None or f != '':
                    data = json.load(f)
    except :
        print('Error occurred in reading Status.json')
        # traceback.print_exc()
        data = {'Flags':0,'GuiFocus':''}
    else :
        if data['GuiFocus'] != '':
            if data['GuiFocus'] == 0: status['GuiFocus'] = 'NoFocus'
            elif data['GuiFocus'] == 1: status['GuiFocus'] = 'Panel_4' # InternalPanel (right hand side)
            elif data['GuiFocus'] == 2: status['GuiFocus'] = 'Panel_1' # ExternalPanel (left hand side)
            elif data['GuiFocus'] == 3: status['GuiFocus'] = 'Panel_2' # CommsPanel (top)
            elif data['GuiFocus'] == 4: status['GuiFocus'] = 'Panel_3' # RolePanel (bottom)
            elif data['GuiFocus'] == 5: status['GuiFocus'] = 'StationServices'
            elif data['GuiFocus'] == 6: status['GuiFocus'] = 'GalaxyMap'
            elif data['GuiFocus'] == 7: status['GuiFocus'] = 'SystemMap'
            elif data['GuiFocus'] == 8: status['GuiFocus'] = 'Orrery'
            elif data['GuiFocus'] == 9: status['GuiFocus'] = 'FSS'
            elif data['GuiFocus'] == 10: status['GuiFocus'] = 'SAA'
            elif data['GuiFocus'] == 11: status['GuiFocus'] = 'Codex'
    return data['Flags']

def getStatusByFlags(rawFlags):
    for statusName in flags.keys():
        status[statusName] = rawFlags&flags[statusName] != 0

def setStatusToStatesMachine(model):
    rawFlags = getFlagsAndFocusByJSON()
    getStatusByFlags(rawFlags)
    if(status['Docked']) and model.state == 'initial': model.startInDock() # startInDock
    elif (status['Docked']) is False and model.state == 'initial' : model.startInSpace()
    # TODO: Add more status
    # WIP

def showAllTrueStatus():
    statusList = []
    for key,value in status.items():
        if value == True : statusList.append(key)
    if len(statusList) == 0 : statusList = ['None']
    return statusList

def getGuiFocus():
    return status['GuiFocus']