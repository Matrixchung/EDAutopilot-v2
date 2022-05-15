from gameui import Logger, ScriptSession
from PySide2.QtWidgets import QGridLayout
from utils.utils import *
import transitions
pyautogui.FAILSAFE=False
map_bookmark = loadFromFile("templates/map_bookmark.png")
map_bookmarkHL = loadFromFile("templates/map_bookmark_highlight.png")
map_sothis = loadFromFile("templates/robigo/map_sothis_a_5.png")
map_sothisHL = loadFromFile("templates/robigo/map_sothis_a_5_highlight.png")
map_robigo = loadFromFile("templates/robigo/map_robigom.png")
map_robigoHL = loadFromFile("templates/robigo/map_robigom_highlight.png")

sign_scassist = loadFromFile('templates/sign_scassist.png')
sign_align_with_target = loadFromFile('templates/sign_align_with_target.png')
sign_autodock = loadFromFile('templates/sign_auto_dock.png')
sign_throttle_up = loadFromFile('templates/sign_throttle_up.png')
sign_obscured = loadFromFile('templates/sign_target_obscured.png')
sign_fuel_filled = loadFromFile('templates/sign_fuel_filled.png')
sign_mission = loadFromFile('templates/sign_has_mission.png')
sign_pause_menu = loadFromFile('templates/sign_pause_menu.png')

tab_contacts = loadFromFile('templates/contacts.png')
tab_contactsHL = loadFromFile('templates/contacts_highlight.png')
tab_sirius = loadFromFile('templates/robigo/tab_sirius.png')
tab_siriusHL = loadFromFile('templates/robigo/tab_sirius_highlight.png')
tab_siriusMarked = loadFromFile('templates/robigo/tab_sirius_marked.png')
tab_robigominesNormal = loadFromFile('templates/robigo/tab_robigo_mines_normal.png')
tab_robigominesMarked = loadFromFile('templates/robigo/tab_robigo_mines_marked.png')
tab_robigominesNormalHL = loadFromFile('templates/robigo/tab_robigo_mines_normal_highlight.png')
tab_robigomines = loadFromFile('templates/robigo/tab_robigo_mines_mission.png')
tab_robigominesHL = loadFromFile('templates/robigo/tab_robigo_mines_mission_highlight.png')

exitButton = loadFromFile("templates/exit.png")
exitButtonHL = loadFromFile("templates/exit_highlight.png")
launchButton = loadFromFile("templates/autolaunch.png")
launchButtonHL = loadFromFile("templates/autolaunch_highlight.png")
button_requestDock = loadFromFile('templates/button_request_docking.png')
button_requestDockHL = loadFromFile('templates/button_request_docking_highlight.png')
button_fuel = loadFromFile('templates/button_fuel.png')
button_complete_mission = loadFromFile('templates/button_complete_mission.png')
button_complete_missionHL = loadFromFile('templates/button_complete_mission_highlight.png')
button_starport_service = loadFromFile('templates/button_starport_services.png')
sign_passenger_lounge = loadFromFile('templates/sign_passenger_lounge.png')

mission_dest = loadFromFile('templates/robigo/mission_dest.png')
mission_destHL = loadFromFile('templates/robigo/mission_dest_highlight.png')
mission_low_value_target = loadFromFile('templates/robigo/mission_low_value_target.png')
mission_high_value_target = loadFromFile('templates/robigo/mission_high_value_target.png')
button_back_smallHL = loadFromFile('templates/button_back_small_highlight.png')
button_accept_unavail = loadFromFile('templates/robigo/button_accept_unavailable.png')
button_accept_unavailHL = loadFromFile('templates/robigo/button_accept_unavailable_highlight.png')
button_accept = loadFromFile('templates/robigo/button_accept.png')

# Offset coord as follows (for mouse clicking, only in 1600x900)
# using GetAbsoluteByOffset()
offset_button_reward_1 = (695,633) # CR reward (1)
offset_button_mission = (319,494)
offset_button_passenger = (319,545)
offset_button_provider_1 = (293,287) # first mission provider in passenger lounge
offset_button_provider_2 = (293,404) # second
offset_button_provider_3 = (293,520) # third
offset_button_mission_back = (281,872) # back button in mission board/passenger lounge
offset_button_stationservice_exit = (326,808)
offset_button_reward_back = (649,872) # back button in rewarding screen/mission detail board
# offset_button_pick_cabin = (893,872)
offset_pick_cabin_bottom = (1044,796)

def setDest(session,dest):
    if session.guiFocus != 'GalaxyMap': 
        session.sendKey('UI_OpenGalaxyMap') # Toggle Map
        session.sleep(3)
    session.sleep(1)
    session.sendKey('UI_NextTab',repeat=2,repeat_delay=0.5)
    session.sleep(2)
    if dest == 'Sothis': destLoc = locateButtons(map_sothis,map_sothisHL,confidence1=0.8,confidence2=0.8)
    elif dest == 'Robigo': destLoc = locateButtons(map_robigo,map_robigoHL,confidence1=0.7,confidence2=0.7)
    else : return False
    session.sleep(1)
    mouseClick(destLoc)
    session.sleep(3)
    session.sendKey('space')
    session.sleep(3)
    session.sendKey('UI_OpenGalaxyMap')
    return True

class p(object):
    pass
progress = p()

class robigo:
    ## USER_DEFINITIONS_AREA_BEGINS
    isDebug = True
    showProcessedImg = True # show the compassImg and navpoint for debug
    usingWatchDog = True # watchdog can help you force CLOG when being interdicted or attacked
    stateOverride = '' # Debugging Options (default: none)
    
    # !!! The middle destinations depend on your ship's jumping capability, so change this if necessary !!!
    firstJumpDest = 'Wredguia TH-U c16-18' # From Robigo to Sothis (3-jump middle star)
    thirdJumpDest = 'Wredguia TH-U c16-18' # From Sothis to Robigo (3-jump middle star)
    maxMissionCount = 8
    missionCountOverride = 0 # For any unread missions or the mission count not shown properly
    ## USER_DEFINITIONS_AREA_ENDS

    states = ['initial','get-mission','mission-received','select-target-sothis','undock','thrust-up','first-align','first-jump', # in Robigo
    'first-sc','second-align','second-jump', # in first-jump middle star
    'second-sc','third-align','first-approaching','first-enable-assist','first-waiting-for-arrive','first-auxiliary-align', # in Sothis and Sothis 5 (Sirius Atmospherics)
    'target-beacon','waiting-for-beacon','select-target-robigo','sothis-a-5-avoiding','fourth-align','third-jump', # in Sirius Atmospherics
    'third-sc','fifth-align','fourth-jump', # in third-jump middle star
    'fourth-sc','sixth-align','second-enable-assist','second-auxiliary-align','second-waiting-for-arrive','approach-station','trigger-autodock','waiting-for-docked','goto-passenger','claim-task-reward' # back to Robigo
    ]
    align = False
    auto = False
    failsafeState = ''
    def __init__(self,logger:Logger=None,layout:QGridLayout=None,scriptSession:ScriptSession=None):
        self.logger = logger
        self.layout = layout   
        initialState = 'initial' # do not change! (default: initial)
        if self.stateOverride != '':self.initialState=self.stateOverride
        self.machine = transitions.Machine(model=progress,states=self.states,initial=initialState)
        self.session = ScriptSession(logger=self.logger)
        
    def run(self):
        while not keyboard.is_pressed('end'):
            try:
                self.session.update()
                # 输入区
                if keyboard.is_pressed('o'): 
                    align = True
                if keyboard.is_pressed('home'): 
                    auto = True
                    startTime = datetime.now()
                if self.isDebug : # Debugging functions
                    if keyboard.is_pressed('capslock+space'): screenCapture()
                    if keyboard.is_pressed("f11") : 
                        current = pyautogui.position()
                        window = self.session.windowCoord
                        self.logger.info(getOffsetCoordByAbsolute(window,current))
                        self.session.sleep(0.1)
                    if keyboard.is_pressed("f9"):
                        pass
                inEmergency = self.session.shipEmergency # Emergency
                if missionCountOverride != 0: missionCount = missionCountOverride
                else: missionCount = len(self.session.missionList)
                # 功能区
                if auto:
                    if progress.state!='initial':
                        elapsedTime = datetime.now()-startTime
                    if keyboard.is_pressed('f10') or inEmergency: # Emergency Break
                        auto=False
                        failsafeState = progress.state
                        continue
                    if failsafeState != '':self.machine.set_state(failsafeState)
                    if self.session.status == 'Docked' and progress.state == 'initial': # in while loop
                        if missionCount < self.maxMissionCount : # 'get-mission'
                            self.machine.set_state('get-mission')
                            # pass
                            # if isDebug: self.machine.set_state('mission-received') # allow launch without missions (Debug)
                        else :
                            self.machine.set_state('mission-received')
                    
                    elif progress.state == 'get-mission':
                        lounge = isImageInGame(sign_passenger_lounge,confidence=0.6)
                        windowCoord = self.session.windowCoord
                        if lounge:
                            for i in range(3): # 3 mission providers
                                if i == 0 : # check first provider
                                    mouseClick(getAbsoluteCoordByOffset(windowCoord,offset_button_provider_1))
                                if i == 1 : # check second
                                    mouseClick(getAbsoluteCoordByOffset(windowCoord,offset_button_provider_2))
                                if i == 2 : # check third
                                    mouseClick(getAbsoluteCoordByOffset(windowCoord,offset_button_provider_3))
                                self.session.sleep(5)
                                for j in range(6): # failsafe number 6
                                    self.session.sleep(1)
                                    result = locateImageInGame(mission_dest,confidence=0.7)
                                    result1 = locateImageInGame(mission_destHL,confidence=0.7)
                                    if result[0]==-1 and result1[0]==-1: break # No more mission
                                    if result1[0]!=-1: pyautogui.moveTo(result1[0]-200,result1[1])
                                    else: pyautogui.moveTo(result[0]-200,result[1])
                                    self.session.sleep(1)
                                    result1 = locateImageInGame(mission_destHL,confidence=0.7)
                                    if result1[0]==-1 : continue
                                    mouseClick(result1)
                                    self.session.sleep(2) # entering mission detail board
                                    lowValue = isImageInGame(mission_low_value_target,confidence=0.6)
                                    highValue = isImageInGame(mission_high_value_target,confidence=0.6)
                                    if lowValue and not highValue : # low value target
                                        if isDebug: self.logger.info("get-mission: Low-value target detected")
                                        self.session.sleep(1)
                                        # mouseClick(getAbsoluteCoordByOffset(windowCoord,offset_button_pick_cabin))
                                        self.session.sendKey('UI_Right')
                                        self.session.sendDelay(1)
                                        self.session.sendKey('space')
                                        self.session.sendDelay(1)
                                        self.session.sleep(1)
                                        pyautogui.moveTo(getAbsoluteCoordByOffset(windowCoord,offset_pick_cabin_bottom))
                                        self.session.sleep(1)
                                        for t in range(8): # do 8 times of scrolling down 100 "ticks" to go to cabin bottom (fewest slots)
                                            pyautogui.scroll(-100)
                                            self.session.sleep(0.5)
                                        # now we`re at the bottom, start enumerating
                                        for t in range(maxMissionCount):
                                            backButton = isImageInGame(button_back_smallHL,confidence=0.6)
                                            acceptButton = isImageInGame(button_accept,confidence=0.7)
                                            acceptButton_unavail = isImageInGame(button_accept_unavail,confidence=0.8)
                                            acceptButton_unavailHL = isImageInGame(button_accept_unavailHL,confidence=0.7)
                                            if backButton == False and (acceptButton or acceptButton_unavail or acceptButton_unavailHL): # ensure we're not targetting the back button and still in the picking board
                                                if t == 0: # first enumerate
                                                    self.session.sendKey('space')
                                                    self.session.sendDelay(1)
                                                else:
                                                    self.session.sendKey('UI_Up')
                                                    self.session.sendDelay(1)
                                                    self.session.sendKey('space')
                                                    self.session.sendDelay(1)
                                            else:
                                                break
                                    else: # high-value
                                        if isDebug: self.logger.info("get-mission: High-value target detected")
                                        # mouseClick(getAbsoluteCoordByOffset(windowCoord,offset_button_reward_back))
                                        self.session.sendKey('UI_Back')
                                        self.session.sendDelay(1)
                                        # Now go one down to avoid infinite loop in the same mission
                                        self.session.sendKey('UI_Down')
                                        self.session.sendDelay(1)
                                    self.session.sleep(2)
                                    self.session.update()
                                    missionCount = len(self.session.missionList)
                                    if missionCount >= maxMissionCount : break # No more slot
                                if missionCount >= maxMissionCount : break # break the outer loop
                            self.session.update()
                            missionCount = len(self.session.missionList)
                            if missionCount >= maxMissionCount or missionCount != 0 : # got
                                self.machine.set_state('mission-received')
                                self.logger.info("success")
                                pass
                    elif progress.state == 'mission-received': # elif 确保一次大的while循环中只执行一次状态判断，避免状态转移导致的update滞后
                        if missionCount == 0 : self.machine.set_state('get-mission')
                        else:
                            if self.session.shipTarget != firstJumpDest and self.session.shipTarget != 'Sothis' : # select-target-sothis 
                                self.session.sleep(1)
                                setDest(self.session,'Sothis')
                            self.session.sleep(2)
                            if self.session.shipTarget == firstJumpDest or self.session.shipTarget == 'Sothis' :
                                self.session.sleep(2)
                                self.machine.set_state('undock')
                    
                    elif progress.state == 'undock':
                        if self.session.status == 'Docked':
                            windowCoord = self.session.windowCoord
                            self.session.sleep(1)
                            if self.session.guiFocus != 'NoFocus': # 返回到主界面
                                mouseClick(getAbsoluteCoordByOffset(windowCoord,offset_button_mission_back))
                                self.session.sleep(2)
                                mouseClick(getAbsoluteCoordByOffset(windowCoord,offset_button_stationservice_exit))
                                self.session.sleep(2)
                            if self.session.guiFocus == 'NoFocus':
                                self.session.sleep(2)
                                self.session.sendKey('UI_Down',repeat=3) # choose AUTO LAUNCH
                                self.session.sleep(1)
                                self.session.sendKey('space') 
                                self.session.sendKey('SpeedZero')
                                self.session.sleep(1)
                                self.machine.set_state('thrust-up')

                    elif progress.state=='thrust-up':
                        self.session.sendKey('ThrustUp')
                        if 'FSDMassLocked' not in self.session.stateList:
                            self.session.sendKey('ThrustUp',hold=3,block=True)
                            self.session.sendKey('SpeedZero')
                            self.machine.set_state('first-align')
                    
                    elif progress.state=='first-align':
                        if 'FSDMassLocked' in self.session.stateList:
                            self.machine.set_state('thrust-up')
                        # if not align: align = True # pass true segment to next loop
                        if not self.session.align(): # align complete
                            # self.session.sendKey('TargetAhead')
                            align=False
                            self.machine.set_state('first-jump')
                    
                    elif progress.state=='first-jump':
                        # Enable FSD
                        if (('FSDJump' not in self.session.stateList and 'FSDCharging' not in self.session.stateList) and
                            'Supercruise' in self.session.stateList or 'FSDCooldown' in self.session.stateList) and self.session.shipLoc!='Robigo': # Waiting for jump complete
                            self.machine.set_state('first-sc')
                        elif 'FSDCharging' not in self.session.stateList and self.session.shipLoc=='Robigo' and not isImageInGame(sign_throttle_up,confidence=0.6): # need charge
                            self.session.sendKey('EnableFSD')
                            self.session.sendDelay(1,block=True) # Just for update the stateList
                            self.session.sendDelay(15,block=True)
                            self.session.sendKey('EngineBoost')
                            self.session.sendDelay(0.5,block=True)
                            self.session.sendKey('SpeedZero')
                        
                    elif progress.state=='first-sc':
                        self.session.sendDelay(1,block=True)
                        self.session.sunAvoiding(fwdDelay=25,turnDelay=11)
                        self.session.sendDelay(1,block=True)
                        self.session.sendKey('PitchUpButton',repeat=3) # trick
                        self.machine.set_state('second-align')
                    
                    elif progress.state=='second-align':
                        if not self.session.align():
                            align=False
                            self.machine.set_state('second-jump')
                    
                    elif progress.state=='second-jump':
                        # Enable FSD
                        if (('FSDJump' not in self.session.stateList and 'FSDCharging' not in self.session.stateList) and
                            'Supercruise' in self.session.stateList or 'FSDCooldown' in self.session.stateList) and self.session.shipLoc != firstJumpDest: # Waiting for jump complete
                            self.machine.set_state('second-sc')
                        elif 'FSDCharging' not in self.session.stateList and self.session.shipLoc==firstJumpDest and not isImageInGame(sign_throttle_up,confidence=0.6): # need charge
                            self.session.sendKey('EnableFSD')
                            self.session.sendDelay(1,block=True) # Just for update the stateList
                            self.session.sendDelay(15,block=True)
                            self.session.sendKey('Speed100') # This time it is in supercruise,so no boost can be applied
                            self.session.sendDelay(2,block=True)
                            self.session.sendKey('SpeedZero')
                    
                    elif progress.state=='second-sc':
                        self.session.sendDelay(1,block=True)
                        self.session.sunAvoiding(fwdDelay=25)
                        self.session.sendDelay(1,block=True)
                        self.machine.set_state('third-align')

                    elif progress.state=='third-align':
                        if not self.session.align():
                            align=False
                            self.machine.set_state('first-approaching')
                    
                    elif progress.state=='first-approaching':
                        if not self.session.align():
                            self.session.sendKey('Speed100')
                            self.session.sendDelay(50,block=True) # magic number:wait the ship approaching Sirius Atmospherics
                            self.session.align()
                            self.session.sendKey('SpeedZero')
                            self.machine.set_state('first-enable-assist')
                    
                    elif progress.state == 'first-enable-assist':
                        # Change the navigation target to Sirius Atmospherics and enable Supercruise Assist
                        result1 = isImageInGame(sign_scassist,confidence=0.8)
                        result2 = isImageInGame(sign_align_with_target,confidence=0.8)
                        if result2 or result1: # Supercruise Assist active
                            # self.machine.set_state('first-waiting-for-arrive')
                            self.machine.set_state('first-auxiliary-align')
                            self.logger.info('first-enable-assist:Assist Already Active!')
                        elif not result1 and not result2: # Supercruise Assist not enabled
                            self.session.sendKey('SpeedZero')
                            self.session.sendDelay(3,block=True)
                            if self.session.guiFocus != 'NoFocus':
                                self.session.sendKey('esc') # back to main panel
                                self.session.sendDelay(1,block=True)
                            if self.session.guiFocus != 'Panel_1':
                                self.session.sendKey('UI_1')
                                self.session.sendDelay(1,block=True)
                            self.session.sendKey('UI_Left',repeat=3)
                            self.session.sendKey('UI_Up',repeat=5) # To Left-Up Corner
                            # Now start from FILTER button
                            # Select Sirius Atmospherics (This time it should be the nearest POI)
                            self.session.sendKey('UI_Right')
                            self.session.sendDelay(1,block=True)
                            self.session.sendKey('UI_Down',hold=4,block=True) # small trick:hold the button to get to the bottom
                            # update: the image size acts weirdly in the bottoms, so backward iterate
                            self.session.sendDelay(1,block=True)
                            for i in range(30): 
                                # 因为使得POI最近的距离实在不好控制 所以遍历导航页的项目 选取 Sirius Atmospherics 
                                res1 = isImageInGame(tab_sirius,confidence=0.7)
                                res2 = isImageInGame(tab_siriusHL,confidence=0.6)
                                res3 = isImageInGame(tab_siriusMarked,confidence=0.6)
                                if res2 or res3 : # Match Found
                                    break
                                if (not res2 and not res3) or res1:
                                    self.session.sendKey('UI_Up')
                                    self.session.sendDelay(2.5,block=True)
                            self.session.sendKey('space')
                            self.session.sendDelay(1,block=True)
                            self.session.sendKey('UI_Right')
                            self.session.sendKey('space')
                            self.session.sendDelay(1,block=True)
                            self.session.sendKey('esc') # back to main panel
                            self.session.sendDelay(5,block=True)
                            result1 = isImageInGame(sign_scassist,confidence=0.6) # re-check assist status
                            result2 = isImageInGame(sign_align_with_target,confidence=0.6)
                            if result2 or result1: # Supercruise Assist active
                                # self.machine.set_state('first-waiting-for-arrive')
                                self.machine.set_state('first-auxiliary-align')
                        
                    elif progress.state == 'first-auxiliary-align':
                        if not self.session.align():
                            self.machine.set_state('first-waiting-for-arrive')

                    elif progress.state=='first-waiting-for-arrive':
                        if 'Supercruise' in self.session.stateList:
                            if isImageInGame(sign_obscured,confidence=0.8): # target obscured
                                self.logger.info('first-waiting-for-arrive:Destination Target Obscured!') # 目标被遮挡
                                self.session.sunAvoiding(turnDelay=9,fwdDelay=30)
                                self.machine.set_state('first-auxiliary-align')
                            else: self.session.align()
                        # else:
                            # result2 = isImageInGame(sign_align_with_target,confidence=0.55)
                            # if result2 and 'Supercruise' in self.session.stateList :
                                # self.session.align()
                        if not ('Supercruise' in self.session.stateList) and self.session.status == 'normal': # add more condition
                            self.session.sendDelay(1,block=True)
                            self.session.sendKey('SpeedZero')
                            self.machine.set_state('target-beacon')
                    
                    elif progress.state=='target-beacon':
                        self.session.sendKey('TargetAhead')
                        self.session.sendDelay(1,block=True)
                        self.machine.set_state('waiting-for-beacon')

                    elif progress.state == 'waiting-for-beacon':
                        if 'FSDCooldown' not in self.session.stateList: # About the same time
                            self.session.sendDelay(5,block=True)
                            self.machine.set_state('select-target-robigo')

                    elif progress.state=='select-target-robigo':
                        if self.session.shipTarget != thirdJumpDest and self.session.shipTarget != 'Robigo': # select-target-sothis 
                            self.session.sleep(1)
                            setDest(self.session,'Robigo')
                        self.session.sleep(2)
                        if self.session.shipTarget == thirdJumpDest or self.session.shipTarget == 'Robigo': # provide direct jump capability
                            self.session.sleep(2)
                            self.machine.set_state('sothis-a-5-avoiding')

                    elif progress.state == 'sothis-a-5-avoiding':
                        self.session.sleep(2)
                        self.session.sunAvoiding(turnDelay=18,fwdDelay=22) # Avoid the blue planet which affects the Template Matching
                        self.session.sendDelay(2,block=True)
                        self.machine.set_state('fourth-align')
                    
                    elif progress.state=='fourth-align':
                        if not self.session.align():
                            align=False
                            self.machine.set_state('third-jump')
                    
                    elif progress.state=='third-jump':
                        # Enable FSD
                        if (('FSDJump' not in self.session.stateList and 'FSDCharging' not in self.session.stateList) and
                            'Supercruise' in self.session.stateList or 'FSDCooldown' in self.session.stateList) and self.session.shipLoc != 'Sothis': # Waiting for jump complete
                            self.machine.set_state('third-sc')
                        elif 'FSDCharging' not in self.session.stateList and self.session.shipLoc == 'Sothis' and not isImageInGame(sign_throttle_up,confidence=0.6): # need charge
                            self.session.sendKey('EnableFSD')
                            self.session.sendDelay(1,block=True) # Just for update the stateList
                            self.session.sendDelay(15,block=True)
                            self.session.sendKey('EngineBoost') # in normal space
                            self.session.sendDelay(0.5,block=True)
                            self.session.sendKey('SpeedZero')
                    
                    elif progress.state=='third-sc':
                        self.session.sendDelay(1,block=True)
                        self.session.sunAvoiding()
                        self.session.sendDelay(1,block=True)
                        self.machine.set_state('fifth-align')
                    
                    elif progress.state=='fifth-align':
                        if not self.session.align():
                            align=False
                            self.machine.set_state('fourth-jump')
                    
                    elif progress.state=='fourth-jump':
                        # Enable FSD
                        if (('FSDJump' not in self.session.stateList and 'FSDCharging' not in self.session.stateList) and
                            'Supercruise' in self.session.stateList or 'FSDCooldown' in self.session.stateList) and self.session.shipLoc != thirdJumpDest : # Waiting for jump complete
                            self.machine.set_state('fourth-sc')
                        elif 'FSDCharging' not in self.session.stateList and self.session.shipLoc==thirdJumpDest and not isImageInGame(sign_throttle_up,confidence=0.6): # need charge
                            self.session.sendKey('EnableFSD')
                            self.session.sendDelay(1,block=True) # Just for update the stateList
                            self.session.sendDelay(15,block=True)
                            self.session.sendKey('Speed100') # This time it is in supercruise,so no boost can be applied
                            self.session.sendDelay(2,block=True)
                            self.session.sendKey('SpeedZero')
                    
                    elif progress.state == 'fourth-sc':
                        self.session.sendDelay(1,block=True)
                        self.session.sunAvoiding()
                        self.session.sendDelay(1,block=True)
                        self.machine.set_state('sixth-align')
                    
                    elif progress.state == 'sixth-align':
                        if not self.session.align():
                            align=False
                            self.machine.set_state('second-enable-assist')
                    
                    elif progress.state == 'second-enable-assist':
                        # just enable Supercruise Assist to Robigo Mines
                        self.session.sendDelay(2,block=True)
                        result1 = isImageInGame(sign_scassist,confidence=0.8)
                        result2 = isImageInGame(sign_align_with_target,confidence=0.8)
                        if result2 or result1: # Supercruise Assist active
                            self.machine.set_state('second-waiting-for-arrive')
                            self.logger.info('second-enable-assist:Assist Already Active!')
                        elif not result1 and not result2: # Supercruise Assist not enabledwe
                            self.session.sendKey('SpeedZero')
                            self.session.sendDelay(3,block=True)
                            if self.session.guiFocus != 'NoFocus':
                                self.session.sendKey('esc') # back to main panel
                                self.session.sendDelay(1,block=True)
                            if self.session.guiFocus != 'Panel_1':
                                self.session.sendKey('UI_1')
                                self.session.sendDelay(1,block=True)
                            self.session.sendKey('UI_Left',repeat=3)
                            self.session.sendKey('UI_Up',repeat=5) # To Left-Up Corner
                            # Now start from FILTER button
                            # Select Robigo Mines (This time it should be the second POI/Station while the first is NAV BEACON)
                            self.session.sendKey('UI_Right')
                            self.session.sendDelay(1,block=True)
                            self.session.sendKey('UI_Down',hold=4,block=True) # small trick:hold the button to get to the bottom
                            # update: the image size acts weirdly in the bottoms, so backward iterate
                            for i in range(30):
                                # 因为使得POI最近的距离实在不好控制 所以遍历导航页的项目 选取 Robigo Mines
                                res1 = isImageInGame(tab_robigomines,confidence=0.7)
                                res2 = isImageInGame(tab_robigominesHL,confidence=0.7)
                                res3 = isImageInGame(tab_robigominesNormal,confidence=0.7)
                                res4 = isImageInGame(tab_robigominesNormalHL,confidence=0.7)
                                res5 = isImageInGame(tab_robigominesMarked,confidence=0.7)
                                if res2 or res4: # Match Found
                                    break
                                if (not res2 and not res4) or (res1 or res3 or res5): 
                                    self.session.sendKey('UI_Up')
                                    self.session.sendDelay(2.5,block=True)
                            self.session.sendKey('space')
                            self.session.sendDelay(1,block=True)
                            self.session.sendKey('UI_Right')
                            self.session.sendKey('space')
                            self.session.sendDelay(1,block=True)
                            self.session.sendKey('esc') # back to main panel
                            self.session.sendDelay(3,block=True)
                            result1 = isImageInGame(sign_scassist,confidence=0.6) # re-check assist status
                            result2 = isImageInGame(sign_align_with_target,confidence=0.6)
                            if result2 or result1: # Supercruise Assist active
                                # self.machine.set_state('second-waiting-for-arrive')
                                self.machine.set_state('second-auxiliary-align')

                    elif progress.state == 'second-auxiliary-align': # make sure the supercruise assist active
                        if not self.session.align():
                            self.machine.set_state('second-waiting-for-arrive')
                    
                    elif progress.state=='second-waiting-for-arrive':
                        if 'Supercruise' in self.session.stateList :
                            if isImageInGame(sign_obscured,confidence=0.8): # target obscured
                                self.logger.info('second-waiting-for-arrive:Destination Target Obscured!') # 目标被遮挡
                                self.session.sunAvoiding(turnDelay=9,fwdDelay=30)
                                self.machine.set_state('second-auxiliary-align')
                            else: self.session.align()
                        # else:
                            # result2 = isImageInGame(sign_align_with_target,confidence=0.55)
                            # if result2 and 'Supercruise' in self.session.stateList :
                                # self.session.align()
                        if not ('Supercruise' in self.session.stateList) and self.session.status == 'normal': # add more condition
                            self.session.sendDelay(1,block=True)
                            self.session.sendKey('SpeedZero')
                            self.machine.set_state('approach-station')
                    
                    elif progress.state=='approach-station':
                        self.session.sendKey('EngineBoost') # trick:boost
                        self.session.sendDelay(5,block=True) # magic number : wait for approaching to 7.5km
                        self.session.sendKey('TargetAhead') # trick: select the station so that it can be directly selected in CONTACTS Tab
                        self.session.sendKey('SpeedZero')
                        self.machine.set_state('trigger-autodock')

                    elif progress.state=='trigger-autodock':
                        # TRIGGER Autodock
                        if self.session.guiFocus != 'Panel_1':
                            if self.session.guiFocus != 'NoFocus':
                                self.session.sendKey('esc')
                                self.session.sendDelay(1,block=True)
                            if self.session.guiFocus == 'NoFocus':
                                self.session.sendKey('UI_1')
                                self.session.sendDelay(1,block=True)

                        result1 = locateImageInGame(tab_contactsHL,confidence=0.6)
                        if result1[0] == -1: # Not in contacts Tab
                            self.session.sendKey('UI_PrevTab') # trick : often in navigation tab,so previous tab is contact
                            self.session.sendDelay(0.5,block=True)
                            result1 = locateImageInGame(tab_contactsHL,confidence=0.6)
                            if result1[0] == -1: # in Transaction tab initially
                                self.session.sendKey('UI_PrevTab')
                                self.session.sendDelay(0.5,block=True)
                        # now the cursor should be in the contact tab
                        # WIP: give it a second check for sure
                        self.session.sendKey('UI_Left',repeat=2)
                        self.session.sendKey('UI_Right',repeat=2)
                        self.session.sendDelay(1,block=True)
                        result1=isImageInGame(button_requestDockHL,confidence=0.6)
                        if result1:
                            self.session.sendKey('space')
                            self.session.sendDelay(5,block=True)
                            self.session.sendKey('esc') # back to main panel and let's check if the docking computer is active
                            self.session.sendDelay(3,block=True)
                            result1=isImageInGame(sign_autodock,confidence=0.6)
                            if result1 or self.session.status == 'docking': # Autodock active
                                self.machine.set_state('waiting-for-docked')
                            else: # docking request denied
                                self.session.sleep(10) # sleep for 10s
                    
                    elif progress.state=='waiting-for-docked':
                        if (self.session.status=='Docked'):
                            self.session.sendDelay(2,block=True)
                            # self.machine.set_state('claim-task-reward')
                            self.machine.set_state('goto-passenger')
                    
                    elif progress.state=='goto-passenger':
                        windowCoord = self.session.windowCoord
                        if self.session.guiFocus != 'NoFocus' and self.session.guiFocus != 'StationServices': 
                            self.session.sendKey('esc')
                            self.session.sendDelay(2,block=True)
                        if self.session.guiFocus == 'NoFocus':
                            self.session.sendDelay(2,block=True)
                            self.session.sendKey('UI_Up',repeat=3)
                            # if isImageInGame(button_fuel,confidence=0.6): # Fuel Button
                                #self.session.sendKey('space')
                                #self.session.sendDelay(3,block=True)
                            self.session.sendKey('space') # force refuel
                            self.session.sendDelay(4,block=True)
                            self.session.sendKey('space') # force refuel
                            self.session.sendDelay(1,block=True)
                            self.session.sendKey('UI_Down')
                            self.session.sendDelay(2,block=True)
                            self.session.sendKey('space') # auto fuel and go to Station Services
                            self.session.sendDelay(5,block=True) 
                        if self.session.guiFocus == 'StationServices':
                            self.session.sleep(2)
                            mouseClick(getAbsoluteCoordByOffset(windowCoord,offset_button_passenger))
                            self.machine.set_state('claim-task-reward')

                    elif progress.state=='claim-task-reward': # Auto claim task rewards
                        windowCoord = self.session.windowCoord
                        self.session.sleep(10) # depends on internet connection
                        if self.session.guiFocus != 'StationServices' or not isImageInGame(sign_passenger_lounge,confidence=0.6): self.machine.set_state('goto-passenger')
                        else:
                            for i in range(3): # 3 mission providers
                                if i == 0 : # check first provider
                                    mouseClick(getAbsoluteCoordByOffset(windowCoord,offset_button_provider_1))
                                if i == 1 : # check second
                                    mouseClick(getAbsoluteCoordByOffset(windowCoord,offset_button_provider_2))
                                if i == 2 : # check third
                                    mouseClick(getAbsoluteCoordByOffset(windowCoord,offset_button_provider_3))
                                self.session.sleep(5)
                                for j in range(10): # failsafe number 10 (in fact the max mission number is 7)
                                    self.session.sleep(1)
                                    result = locateImageInGame(button_complete_mission,confidence=0.6)
                                    if result[0]==-1: break # No more mission
                                    pyautogui.moveTo(result[0]-200,result[1]) # prevent mouse cursor
                                    self.session.sleep(1)
                                    result1 = locateImageInGame(button_complete_missionHL,confidence=0.6)
                                    if result1[0]==-1 : continue
                                    mouseClick(result1)
                                    self.session.sleep(2)
                                    mouseClick(getAbsoluteCoordByOffset(windowCoord,offset_button_reward_1))
                                    self.session.sleep(3)
                                    backButton = isImageInGame(button_back_smallHL,confidence=0.6)
                                    while not backButton:  backButton = isImageInGame(button_back_smallHL,confidence=0.6)
                                    self.session.sleep(1)
                                    mouseClick(getAbsoluteCoordByOffset(windowCoord,offset_button_reward_back))
                                    # self.session.sendKey('space')
                                    if missionCountOverride >= 1: missionCountOverride -= 1
                                self.session.update()
                                missionCount = len(self.session.missionList)
                                if missionCount == 0 and missionCountOverride == 0: break # No more mission
                            self.session.update()
                            missionCount = len(self.session.missionList)
                            if missionCount == 0: # all claimed
                                # auto=False
                                # failsafeState = ''
                                missionCountOverride = 0
                                self.machine.set_state('initial')

                if align: align = self.session.align()
            except Exception:
                self.logger