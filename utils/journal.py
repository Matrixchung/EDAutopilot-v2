from os import environ, listdir
from os.path import join, isfile, getmtime
from dataclasses import dataclass, field
import json
import time
import traceback
from datetime import datetime,timezone
savedGamePath = environ['USERPROFILE'] + "\Saved Games\Frontier Developments\Elite Dangerous"
@dataclass
class mission:
    id: int
    localisedName: str = ''
    reward: int = 0
    wing: bool = False
    def __hash__(self) -> int:
        return hash(self.id)
    def __eq__(self, __o: object) -> bool:
        return self.id == __o.id
@dataclass
class Journal:
    @dataclass
    class log:
        path: str = ''
        version: str = ''
        latestUpdate: float = 0.0
        updateInterval: float = 0.0
        raw: str = ''
    @dataclass
    class ship:
        model: str = ''
        name: str = ''
        ident: str = ''
        fuel: float = 0.0
        fuelCap: float = 0.0
        fuelLevel: int = 100 # round((fuel/fuelCap)*100) %
        isScooping: bool = False
        hull: float = 0.0
        cargoCap: int = 0
        jumpRange: float = 0.0
        modules: list = field(default_factory=list)
    @dataclass
    class nav:
        navRoutes: list = field(default_factory=list)
        location: str = ''
        lastTarget: str = ''
        target: str = ''
        targetStarClass: str = ''
        remainingJumps: int = 0
        dockedStation: str = ''
    status: str = ''
    signs: set = field(default_factory=set) # unique signs
    missions: set[mission] = field(default_factory=set)
journal = Journal()
# STATUS: normal,undocking,docking,startUndock,startDock,docked,startJump,finishJump,supercruise
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
def parseLogs(logPath=None,logger=None) -> Journal:
    global latestLogLine, journal
    if not logPath:
        logPath = getLatestLogPath()
    try:
        linesRead = 0
        with open(logPath, 'r', encoding='utf-8') as f:
            for line in f:
                journal.log.path = logPath
                logJson = json.loads(line)
                logEvent = logJson['event']
                # Event Filters start
                if logEvent == "FSSSignalDiscovered" or \
                   logEvent == "Friends" or \
                   logEvent == "Powerplay" or \
                   logEvent == "NpcCrewPaidWage" or \
                   logEvent == "MissionRedirected" or \
                   logEvent == "Statistics" or \
                   logEvent == "Materials":
                   continue
                # Event Filters end
                linesRead += 1
                if linesRead>latestLogLine:
                    logTime = datetime.strptime(logJson['timestamp'],UTC_FORMAT).replace(tzinfo=timezone.utc) # change to UTC time
                    logTime = logTime.timestamp()
                    if logTime>=journal.log.latestUpdate: # should update
                        latestLogLine += 1
                        journal.log.latestUpdate=logTime
                        journal.log.updateInterval = time.time()-logTime
                        journal.log.raw = logJson
                        # print(logEvent+' ') 
                        # print(logTime)
                        if logEvent == 'Fileheader':
                            journal.log.version = 'Odyssey' if logJson['Odyssey'] else 'Horizons'

                        elif logEvent == 'Loadout':
                            journal.ship.model = logJson['Ship']
                            journal.ship.name = logJson['ShipName']
                            journal.ship.ident = logJson['ShipIdent']
                            journal.ship.hull = logJson['HullHealth']
                            journal.ship.fuelCap = logJson['FuelCapacity']['Main']
                            journal.ship.cargoCap = logJson['CargoCapacity']
                            journal.ship.jumpRange = logJson['MaxJumpRange']
                            journal.ship.modules = logJson['Modules']

                        elif logEvent == 'RefuelAll' or logEvent == 'RefuelPartial':
                            journal.ship.fuel += logJson['Amount']
                            journal.ship.fuelLevel = round((journal.ship.fuel/journal.ship.fuelCap)*100)
                        elif logEvent == 'FuelScoop':
                            journal.ship.fuel += logJson['Scooped']
                            journal.ship.fuelLevel = round((journal.ship.fuel/journal.ship.fuelCap)*100)
                            if journal.log.updateInterval <= 10 and journal.ship.fuelLevel < 99: journal.ship.isScooping = True
                            else: journal.ship.isScooping = False
                        
                        elif ((logEvent == 'ReceiveText' and 'AttackDutyStart' in logJson['Message']) or logEvent == 'Interdicted' or logEvent == 'UnderAttack' or (logEvent == 'Music' and (logJson['MusicTrack'] == 'Interdiction' or logJson['MusicTrack'] == 'Combat_Dogfight'))) and journal.log.updateInterval <= 30: # May be interdicted!
                            journal.signs.add('UnderAttack')
                        elif logEvent == 'Scanned' and journal.log.updateInterval <= 30 : # logged within 30 seconds 
                            journal.signs.add('Scanned')
                        elif logEvent == 'Resurrect' or logEvent == 'LoadGame' or logEvent == 'Shutdown': # Ship destroyed / Reload the game
                            if 'UnderAttack' in journal.signs: journal.signs.remove('UnderAttack')
                            if 'Scanned' in journal.signs: journal.signs.remove('Scanned')
                        
                        elif logEvent == 'Music': # music playing
                            if logJson['MusicTrack'] == 'DestinationFromHyperspace' and journal.nav.target is not None: # Finish multi-hop route
                                journal.nav.target = journal.nav.lastTarget = None 
                            elif logJson['MusicTrack'] == 'MainMenu': journal.status = 'MainMenu'
                            elif logJson['MusicTrack'] == 'DockingComputer': 
                                if journal.status == 'startUndock': journal.status = 'undocking'
                                elif journal.status == 'startDock': journal.status = 'docking'
                    
                        elif logEvent == 'DockingRequested': journal.status = 'startDock'

                        elif logEvent == 'Docked': 
                            journal.status = 'Docked'
                            journal.nav.dockedStation = logJson['StationName']

                        elif logEvent == 'StartJump': 
                            if logJson['JumpType'] == 'Hyperspace' and 'StarSystem' in logJson:
                                journal.status = 'startJump'
                                journal.nav.location = logJson['StarSystem']
                                journal.nav.lastTarget = logJson['StarSystem']
                                journal.nav.targetStarClass = logJson['StarClass']
                            elif logJson['JumpType'] == 'Supercruise':
                                journal.status = 'supercruise'
                        
                        elif logEvent == 'SupercruiseEntry': journal.status = 'supercruise'

                        elif logEvent == 'SupercruiseExit' or logEvent == 'DockingCancelled': journal.status = 'normal'

                        elif logEvent == 'Undocked': journal.status = 'normal'

                        elif logEvent == 'FSDTarget': 
                            if logJson['Name'] == journal.nav.location : journal.nav.target = None
                            else: 
                                journal.nav.target = logJson['Name']
                                if 'RemainingJumpsInRoute' in logJson: # Multi-Hop
                                    journal.nav.remainingJumps = logJson['RemainingJumpsInRoute']
                                else : journal.nav.remainingJumps = 1 # single hop
                    
                        elif logEvent == 'FSDJump':
                            journal.ship.fuel = logJson['FuelLevel']
                            journal.ship.fuelLevel = round((journal.ship.fuel/journal.ship.fuelCap)*100)
                            if journal.nav.lastTarget == logJson['StarSystem']: 
                                journal.nav.lastTarget = None
                                journal.status = 'finishJump'
                                if journal.nav.target == logJson['StarSystem'] and journal.nav.remainingJumps == 0 : 
                                    journal.nav.targetStarClass = None
                                    journal.nav.target = None # Finish route
                    
                        elif (logEvent == 'Location' or logEvent == 'FSDJump') and 'StarSystem' in logJson:
                            journal.nav.location = logJson['StarSystem']

                        elif logEvent == 'MissionAccepted': # Add to Mission List
                            journal.missions.add(mission(id=logJson['MissionID'],localisedName=logJson['LocalisedName'],reward=logJson['Reward'],wing=logJson['Wing']))
                        elif (logEvent == 'MissionAbandoned' or logEvent == 'MissionCompleted' or logEvent == 'MissionFailed' )and mission(id=logJson['MissionID']) in journal.missions:
                            journal.missions.remove(mission(id=logJson['MissionID']))
                
                    if journal.status != 'Docked' and journal.nav.dockedStation is not None: journal.nav.dockedStation = None
    except IOError as e:
        if logger: logger.warn("Error in reading journal logs "+e)
        else:
            print("Error in reading journal logs "+e)
            traceback.print_exc()
    return journal

if __name__ == '__main__': # Test
    # parseLogs()
    # print(getLatestLogPath())
    # print(journal['status'])
    # print(journal['location'])
    # print(journal['dockedStation'])
    # print(journal['target'])
    # print(journal['missions'])
    # print(journal['isUnderAttack'])
    # print(journal['isBeingScanned'])
    jn = parseLogs()
    print(jn.nav.targetStarClass)