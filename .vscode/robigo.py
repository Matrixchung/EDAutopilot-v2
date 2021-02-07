from game import *
import transitions
class p(object):
    pass
progress = p()
if __name__ == '__main__': # Test
    isDebug = True
    states = ['initial','get-mission','mission-received','select-target-sothis','undock','thrust-up','first-align','first-jump', # in Robigo
    'first-sc','second-align','second-jump', # in middle starsystem
    'second-sc','first-enable-assist','third-align','first-search-for-target','first-waiting-for-arrive', # in sothis and sothis 5 (Sirius Atmospherics)
    'target-beacon','select-target-robigo','fourth-align','third-jump', # in sirius atmospherics
    'third-sc','second-enable-assist','fifth-align','second-waiting-for-arrive','trigger-autodock','waiting-for-docked' # back to robigo
    ]
    machine = transitions.Machine(model=progress,states=states,initial='initial')
    machine.add_ordered_transitions() # 按上文列表顺序转移状态
    session = gameSession(debug=isDebug)
    align = False
    auto = False
    if isDebug:
        statusImg = np.zeros((300,1200,3),np.uint8)
    while not keyboard.is_pressed('p'):
        session.update()
        # 输入区
        if keyboard.is_pressed('o'): align = True
        if keyboard.is_pressed('home'): auto = True
        # 功能区
        if auto:
            if session.status == 'Docked' and progress.state == 'initial': # in while loop
                if len(session.missionList)==0 : # 'get-mission'
                    machine.set_state('get-mission')
                else :
                    machine.set_state('mission-received')
            
            elif progress.state == 'get-mission':
                pass

            elif progress.state == 'mission-received': # elif 确保一次大的while循环中只执行一次状态判断，避免状态转移导致的update滞后
                if session.shipTarget == '': # select-target-sothis
                    pass
                machine.set_state('undock')
            
            elif progress.state == 'undock':
                # GUI:AutoLaunch
                session.sendKey('SpeedZero')
                time.sleep(1)
                machine.set_state('thrust-up')
                pass

            elif progress.state=='thrust-up':
                session.sendKey('ThrustUp',hold=20,block=True)
                machine.set_state('first-align')
            
            elif progress.state=='first-align':
                # if not align: align = True # pass true segment to next loop
                if not session.align(): # align completed
                    align=False
                    machine.set_state('first-jump')
            
            elif progress.state=='first-jump':
                pass # Enable FSD
                if not (('FSDJump' in session.stateList and 'FSDCharging' in session.stateList) or
                        'Supercruise' not in session.stateList or 'FSDCooldown' not in session.stateList): # Waiting for jump complete
                    machine.set_state('first-sc')
            
            elif progress.state=='first-sc':
                session.sendDelay(1,block=True)
                session.sunAvoiding()
                session.sendDelay(1,block=True)
                machine.set_state('second-align')
            
            elif progress.state=='second-align':
                if not session.align():
                    align=False
                    machine.set_state('second-jump')
            
            elif progress.state=='second-jump':
                pass # Enable FSD
                if not (('FSDJump' in session.stateList and 'FSDCharging' in session.stateList) or
                        'Supercruise' not in session.stateList or 'FSDCooldown' not in session.stateList): # Waiting for jump complete
                    machine.set_state('second-sc')
            
            elif progress.state=='second-sc':
                session.sendDelay(1,block=True)
                session.sunAvoiding()
                session.sendDelay(1,block=True)
                machine.set_state('first-enable-assist')
            
            elif progress.state=='first-enable-assist':
                pass # Enable Supercruise Assist
                # if Enabled:
                session.sendDelay(1,block=True)
                machine.set_state('third-align')

            elif progress.state=='third-align':
                if not session.align():
                    align=False
                    machine.set_state('first-search-for-target')
            
            elif progress.state=='first-search-for-target':
                session.sendDelay(10,block=True) # magic number:wait the ship approaching Sirius Atmospherics
                pass # Change the navigation target to Sirius Atmospherics and enable Supercruise Assist
                machine.set_state('first-waiting-for-arrive')

            elif progress.state=='first-waiting-for-arrive':
                if not ('Supercruise' in session.stateList): # add more condition
                    session.sendDelay(1,block=True)
                    session.sendKey('SpeedZero')
                    machine.set_state('target-beacon')
            
            elif progress.state=='target-beacon':
                session.sendKey('TargetAhead')
                session.sendDelay(1,block=True)
                # if target selected:
                machine.set_state('select-target-robigo')
            
            elif progress.state=='select-target-robigo':
                pass # select target
                session.sendDelay(3,block=True)
                if session.shipTarget == 'Robigo':
                    machine.set_state('fourth-align')
            
            elif progress.state=='fourth-align':
                if not session.align():
                    align=False
                    machine.set_state('third-jump')
            
            elif progress.state=='third-jump':
                pass # Enable FSD
                if not (('FSDJump' in session.stateList and 'FSDCharging' in session.stateList) or
                        'Supercruise' not in session.stateList or 'FSDCooldown' not in session.stateList): # Waiting for jump complete
                    machine.set_state('third-sc')
            
            elif progress.state=='third-sc':
                session.sendDelay(1,block=True)
                session.sunAvoiding(fwdDelay=30)
                session.sendDelay(1,block=True)
                machine.set_state('second-enable-assist')

            elif progress.state=='second-enable-assist':
                pass # Enable Supercruise Assist
                # if Enabled:
                session.sendDelay(1,block=True)
                machine.set_state('fifth-align')
            
            elif progress.state=='fifth-align':
                if not session.align():
                    align=False
                    machine.set_state('second-waiting-for-arrive')
            
            elif progress.state=='second-waiting-for-arrive':
                if not ('Supercruise' in session.stateList): # add more condition
                    session.sendDelay(1,block=True)
                    session.sendKey('SpeedZero')
                    machine.set_state('trigger-autodock')
            
            elif progress.state=='trigger-autodock':
                session.sendKey('Speed100')
                session.sendDelay(5,block=True) # magic number : wait for approaching to 7.5km
                session.sendKey('SpeedZero')
                pass # toggle autodock
                machine.set_state('waiting-for-docked')

            elif progress.state=='waiting-for-docked':
                if (session.status=='Docked'):
                    auto=False
                    machine.set_state('initial')
                
   
        if align: align = session.align()
        if isDebug:
            cv2.putText(statusImg,'GUIFocus:%s'%session.guiFocus,(10,30),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
            cv2.putText(statusImg,"align:%s"%session.isAligned,(400,30),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
            cv2.putText(statusImg,'state:%s'%session.stateList,(10,60),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
            cv2.putText(statusImg,'Status:%s'%session.status,(10,90),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
            cv2.putText(statusImg,'Loc:%s'%session.shipLoc,(310,90),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
            cv2.putText(statusImg,'Target:%s'%session.shipTarget,(700,90),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
            cv2.putText(statusImg,'%s'%progress.state,(10,120),cv2.FONT_HERSHEY_DUPLEX,1,(0,255,0))
            cv2.imshow("status",statusImg)
            statusImg.fill(0)
            cv2.waitKey(1)
    
    session.stop()