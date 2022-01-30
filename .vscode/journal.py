from os import environ, listdir
from os.path import join, isfile, getmtime, abspath
import json
import time
import traceback
from datetime import datetime,timezone
savedGamePath = environ['USERPROFILE'] + "\Saved Games\Frontier Developments\Elite Dangerous"
journal = {
    'latestLogUpdateTime': 0.0,
    'missions': [],
    'navRoutes': [],
    'status': '',
    'location': '',
    'dockedStation': '',
    'lastTarget': '',
    'remainingJumpsInRoute': 0,
    'target': '',
    'isUnderAttack': False, # Interdiction and Under Attack check
    'isBeingScanned': False
}
# STATUS: normal,undocking,docking,startUndock,startDock,docked,startJump,finishJump
def getNavRoute(routePath=None):
    if not routePath:
        routePath = savedGamePath+r"\NavRoute.json"
    pass # WIP
    
def getLatestLogPath(logPath=None):
    if not logPath:
        logPath = savedGamePath
    logsList = [join(logPath, f) for f in listdir(logPath) if isfile(join(logPath, f)) and f.startswith('Journal.')]
    if not logsList:
        return None
    latestLog = max(logsList, key=getmtime)
    return latestLog

UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
latestLogLine = 0
def parseLogs(logPath=None):
    global latestLogLine
    if not logPath:
        logPath = getLatestLogPath()
    try:
        linesRead = 0
        with open(logPath, 'r', encoding='utf-8') as f:
            for line in f:
                logJson = json.loads(line)
                logEvent = logJson['event']
                # Event Filters start
                if logEvent == "FSSSignalDiscovered" or \
                   logEvent == "Friends" or \
                   logEvent == "Powerplay" or \
                   logEvent == "NpcCrewPaidWage" or \
                   logEvent == "MissionRedirected" or \
                   logEvent == "Loadout" or \
                   logEvent == "Statistics" or \
                   logEvent == "Materials":
                   continue
                # Event Filters end
                linesRead += 1
                if linesRead>latestLogLine:
                    logTime = datetime.strptime(logJson['timestamp'],UTC_FORMAT).replace(tzinfo=timezone.utc) # change to UTC time
                    logTime = logTime.timestamp()
                    if logTime>=journal['latestLogUpdateTime']: # should update
                        latestLogLine += 1
                        journal['latestLogUpdateTime']=logTime
                        # print(logEvent+' ') 
                        # print(logTime)

                        if ((logEvent == 'ReceiveText' and ('CargoHunter' in logJson['Message'] or 'PassengerHunter' in logJson['Message'] or 'AttackDutyStart' in logJson['Message'])) or logEvent == 'Interdicted' or logEvent == 'UnderAttack' or (logEvent == 'Music' and (logJson['MusicTrack'] == 'Interdiction' or logJson['MusicTrack'] == 'Combat_Dogfight'))) and time.time()-logTime <= 30: # May be interdicted!
                            journal['isUnderAttack'] = True
                        elif logEvent == 'Scanned' and time.time()-logTime <= 30 : # logged within 30 seconds 
                            journal['isBeingScanned'] = True
                        elif logEvent == 'Resurrect' or logEvent == 'LoadGame' or logEvent == 'Shutdown': # Ship destroyed / Reload the game
                            journal['isUnderAttack'] = journal['isBeingScanned'] = False
                        elif logEvent == 'Music': # music playing
                            if logJson['MusicTrack'] == 'DestinationFromHyperspace' and journal['target'] is not None: # Finish multi-hop route
                                journal['target'] = journal['lastTarget'] = None 
                            elif logJson['MusicTrack'] == 'MainMenu': journal['status'] = 'MainMenu'
                            elif logJson['MusicTrack'] == 'DockingComputer': 
                                if journal['status'] == 'startUndock': journal['status'] = 'undocking'
                                elif journal['status'] == 'startDock': journal['status'] = 'docking'
                    
                        elif logEvent == 'DockingRequested': journal['status'] = 'startDock'

                        elif logEvent == 'Docked': 
                            journal['status'] = 'Docked'
                            journal['dockedStation'] = logJson['StationName']

                        elif logEvent == 'StartJump' and 'StarSystem' in logJson: 
                            journal['status'] = 'startJump'
                            journal['location'] = logJson['StarSystem']
                            journal['lastTarget'] = logJson['StarSystem']
                    
                        elif logEvent == 'SupercruiseExit' or logEvent == 'DockingCancelled': journal['status'] = 'normal'

                        elif logEvent == 'Undocked': journal['status'] = 'normal'

                        elif logEvent == 'FSDTarget': 
                            if logJson['Name'] == journal['location'] : journal['target'] = None
                            else: 
                                journal['target'] = logJson['Name']
                                if 'RemainingJumpsInRoute' in logJson: # Multi-Hop
                                    journal['remainingJumpsInRoute'] = logJson['RemainingJumpsInRoute']
                                else : journal['remainingJumpsInRoute'] = 1 # single hop
                    
                        elif logEvent == 'FSDJump':
                            if journal['lastTarget'] == logJson['StarSystem']: 
                                journal['lastTarget'] = None
                                journal['status'] = 'finishJump'
                                if journal['target'] == logJson['StarSystem'] and journal['remainingJumpsInRoute'] == 0 : journal['target'] = None # Finish route
                    
                        elif (logEvent == 'Location' or logEvent == 'FSDJump') and 'StarSystem' in logJson:
                            journal['location'] = logJson['StarSystem']

                        elif logEvent == 'MissionAccepted': # Add to Mission List
                            journal['missions'].append(logJson['MissionID'])
                        elif (logEvent == 'MissionAbandoned' or logEvent == 'MissionCompleted' or logEvent == 'MissionFailed' )and logJson['MissionID'] in journal['missions']:
                            journal['missions'].remove(logJson['MissionID'])
                
                    if journal['status'] != 'Docked' and journal['dockedStation'] is not None: journal['dockedStation'] = None
    except IOError as e:
        print("Error in reading journal logs "+e)
        traceback.print_exc()

def setJournal():
    parseLogs()
    return journal

if __name__ == '__main__': # Test
    parseLogs()
    print(getLatestLogPath())
    print(journal['status'])
    print(journal['location'])
    print(journal['dockedStation'])
    print(journal['target'])
    print(journal['missions'])
    print(journal['isUnderAttack'])
    print(journal['isBeingScanned'])