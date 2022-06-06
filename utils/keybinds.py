from os import environ, listdir
from os.path import join, isfile, getmtime
import time
import traceback
from xml.dom.minidom import parse
from utils.directinputs import PressKey,ReleaseKey
# Keys need to be parsed are started from capital letter
# Here are default keys (don't have to change them)
defaultDict = {
    'YawLeftButton': 0x1E, # Key A
    'YawRightButton': 0x20, # Key D
    'PitchUpButton': 0xB5, # NUM /
    'PitchDownButton': 0x37, # NUM *
    'RollLeftButton': 0x4E, # NUM +
    'RollRightButton': 0x9C, # NUM ENTER
    'PipLeft': 0xCB, # LeftArrow
    'PipRight': 0xCD, # RightArrow
    'PipUp': 0xC8, # UpArrow
    'PipDown': 0xD0, # DownArrow
    'EnableFSD': 0x24, # Key J
    'EngineBoost': 0x0F, # Key Tab
    'Speed100': 0x47, # NUM 7
    'SpeedZero': 0x2D, # Key X
    'Speed50': 0x48, # NUM 8
    'ThrustUp': 0x13, # Key R
    'TargetAhead': 0x14, # Key T 
    'UI_OpenGalaxyMap': 0x4A, # NUM -
    'UI_NextTab': 0x12, # Key E
    'UI_PrevTab': 0x10, # Key Q
    'UI_Up': 0x11, # Key W
    'UI_Down': 0x1F, # Key S
    'UI_Left': 0x1E, # Key A
    'UI_Right': 0x20, # Key D
    'UI_Up_Alt': 0xC8, # (Alternative UI Buttons for GalaxyMap)UpArrow
    'UI_Down_Alt': 0xD0, # DownArrow
    'UI_Left_Alt': 0xCB, # LeftArrow
    'UI_Right_Alt': 0xCD, # RightArrow
    'UI_Back': 0x0E, # Backspace
    'UI_1': 0x02, # Key 1
    'UI_2': 0x03, # Key 2
    'UI_3': 0x04, # Key 3
    'UI_4': 0x05, # Key 4
    'Pause': 0x19, # Key P
    'UI_Select': 0x39, # Key Space
    'enter': 0x1C, # Key RETURN(ENTER)
    'esc': 0x01 # Key ESC    
}

aliasDict = { # in-program key alias: in-game name
    'EnableFSD': 'HyperSuperCombination',
    'EngineBoost': 'UseBoostJuice',
    'Speed100': 'SetSpeed100',
    'SpeedZero': 'SetSpeedZero',
    'Speed50': 'SetSpeed50',
    'ThrustUp': 'UpThrustButton',
    'TargetAhead': 'SelectTarget',
    'UI_OpenGalaxyMap': 'GalaxyMapOpen',
    'UI_NextTab': 'CycleNextPanel',
    'UI_PrevTab': 'CyclePreviousPanel',
    'UI_1': 'FocusLeftPanel',
    'UI_2': 'FocusCommsPanel',
    'UI_3': 'FocusRadarPanel',
    'UI_4': 'FocusRightPanel',
    'UI_Up_Alt': 'UI_Up',
    'UI_Left_Alt': 'UI_Left',
    'UI_Right_Alt': 'UI_Right',
    'UI_Down_Alt': 'UI_Down',
    'PipLeft': 'IncreaseSystemsPower',
    'PipRight': 'IncreaseWeaponsPower',
    'PipUp': 'IncreaseEnginesPower',
    'PipDown': 'ResetPowerDistribution'
} # some key names in ED are really confusing

convert_to_direct_keys = {
    'Key_LeftShift': 'Key_LShift',
    'Key_RightShift': 'Key_RShift',
    'Key_LeftAlt': 'Key_LAlt',
    'Key_RightAlt': 'Key_RAlt',
    'Key_LeftControl': 'Key_LControl',
    'Key_RightControl': 'Key_RControl',
    'Key_LeftBracket': 'Key_LBracket',
    'Key_RightBracket': 'Key_RBracket',
}

duplicatedKeysDict = { # Here are some keybinds which may cause problems if they are binded to the same keys
# in-program key alias: (in-game name, notice)
    'UI_NextTab': ('CamYawRight', 'CycleNextPanel and CamYawRight (default: E) are duplicated. Please check the settings, otherwise the setTargetSystem() will not be performed correctly.'),
    'UI_PrevTab': ('CamYawLeft', 'CyclePreviousPanel and CamYawLeft (default: Q) are duplicated. Please check the settings, otherwise the setTargetSystem() will not be performed correctly.')
}
#Scancode Reference
SCANCODE = {
    'KEY_ESCAPE'          : 0x01,
    'KEY_1'               : 0x02,
    'KEY_2'               : 0x03,
    'KEY_3'               : 0x04,
    'KEY_4'               : 0x05,
    'KEY_5'               : 0x06,
    'KEY_6'               : 0x07,
    'KEY_7'               : 0x08,
    'KEY_8'               : 0x09,
    'KEY_9'               : 0x0A,
    'KEY_0'               : 0x0B,
    'KEY_MINUS'           : 0x0C,    # - on main keyboard */
    'KEY_EQUALS'          : 0x0D,
    'KEY_BACKSPACE'       : 0x0E,    # backspace */
    'KEY_TAB'             : 0x0F,
    'KEY_Q'               : 0x10,
    'KEY_W'               : 0x11,
    'KEY_E'               : 0x12,
    'KEY_R'               : 0x13,
    'KEY_T'               : 0x14,
    'KEY_Y'               : 0x15,
    'KEY_U'               : 0x16,
    'KEY_I'               : 0x17,
    'KEY_O'               : 0x18,
    'KEY_P'               : 0x19,
    'KEY_LBRACKET'        : 0x1A,
    'KEY_RBRACKET'        : 0x1B,
    'KEY_RETURN'          : 0x1C,    # Enter on main keyboard */
    'KEY_ENTER'           : 0x1C,
    'KEY_LCONTROL'        : 0x1D,
    'KEY_A'               : 0x1E,
    'KEY_S'               : 0x1F,
    'KEY_D'               : 0x20,
    'KEY_F'               : 0x21,
    'KEY_G'               : 0x22,
    'KEY_H'               : 0x23,
    'KEY_J'               : 0x24,
    'KEY_K'               : 0x25,
    'KEY_L'               : 0x26,
    'KEY_SEMICOLON'       : 0x27,
    'KEY_APOSTROPHE'      : 0x28,
    'KEY_GRAVE'           : 0x29,    # accent grave */
    'KEY_LSHIFT'          : 0x2A,
    'KEY_BACKSLASH'       : 0x2B,
    'KEY_Z'               : 0x2C,
    'KEY_X'               : 0x2D,
    'KEY_C'               : 0x2E,
    'KEY_V'               : 0x2F,
    'KEY_B'               : 0x30,
    'KEY_N'               : 0x31,
    'KEY_M'               : 0x32,
    'KEY_COMMA'           : 0x33,
    'KEY_PERIOD'          : 0x34,    # . on main keyboard */
    'KEY_SLASH'           : 0x35,    # / on main keyboard */
    'KEY_RSHIFT'          : 0x36,
    'KEY_NUMPAD_MULTIPLY' : 0x37,    # * on numeric keypad */
    'KEY_LMENU'           : 0x38,    # left Alt */
    'KEY_SPACE'           : 0x39,
    'KEY_CAPITAL'         : 0x3A,
    'KEY_F1'              : 0x3B,
    'KEY_F2'              : 0x3C,
    'KEY_F3'              : 0x3D,
    'KEY_F4'              : 0x3E,
    'KEY_F5'              : 0x3F,
    'KEY_F6'              : 0x40,
    'KEY_F7'              : 0x41,
    'KEY_F8'              : 0x42,
    'KEY_F9'              : 0x43,
    'KEY_F10'             : 0x44,
    'KEY_NUMLOCK'         : 0x45,
    'KEY_SCROLL'          : 0x46,    # Scroll Lock */
    'KEY_NUMPAD_7'        : 0x47,
    'KEY_NUMPAD_8'        : 0x48,
    'KEY_NUMPAD_9'        : 0x49,
    'KEY_NUMPAD_SUBTRACT' : 0x4A,    # - on numeric keypad */
    'KEY_NUMPAD_4'        : 0x4B,
    'KEY_NUMPAD_5'        : 0x4C,
    'KEY_NUMPAD_6'        : 0x4D,
    'KEY_NUMPAD_ADD'      : 0x4E,    # + on numeric keypad */
    'KEY_NUMPAD_1'        : 0x4F,
    'KEY_NUMPAD_2'        : 0x50,
    'KEY_NUMPAD_3'        : 0x51,
    'KEY_NUMPAD_0'        : 0x52,
    'KEY_DECIMAL'         : 0x53,    # . on numeric keypad */
    'KEY_F11'             : 0x57,
    'KEY_F12'             : 0x58,
    'KEY_F13'             : 0x64,    #                     (NEC PC98) */
    'KEY_F14'             : 0x65,    #                     (NEC PC98) */
    'KEY_F15'             : 0x66,    #                     (NEC PC98) */
    'KEY_KANA'            : 0x70,    # (Japanese keyboard)            */
    'KEY_CONVERT'         : 0x79,    # (Japanese keyboard)            */
    'KEY_NOCONVERT'       : 0x7B,    # (Japanese keyboard)            */
    'KEY_YEN'             : 0x7D,    # (Japanese keyboard)            */
    'KEY_NUMPAD_EQUALS'   : 0x8D,    # : on numeric keypad (NEC PC98) */
    'KEY_CIRCUMFLEX'      : 0x90,    # (Japanese keyboard)            */
    'KEY_AT'              : 0x91,    #                     (NEC PC98) */
    'KEY_COLON'           : 0x92,    #                     (NEC PC98) */
    'KEY_UNDERLINE'       : 0x93,    #                     (NEC PC98) */
    'KEY_KANJI'           : 0x94,    # (Japanese keyboard)            */
    'KEY_STOP'            : 0x95,    #                     (NEC PC98) */
    'KEY_AX'              : 0x96,    #                     (Japan AX) */
    'KEY_UNLABELED'       : 0x97,    #                        (J3100) */
    'KEY_NUMPAD_ENTER'    : 0x9C,    # Enter on numeric keypad */
    'KEY_RCONTROL'        : 0x9D,
    'KEY_NUMPAD_COMMA'    : 0xB3,    # , on numeric keypad (NEC PC98) */
    'KEY_NUMPAD_DIVIDE'   : 0xB5,    # / on numeric keypad */
    'KEY_SYSRQ'           : 0xB7,
    'KEY_RMENU'           : 0xB8,    # right Alt */
    'KEY_HOME'            : 0xC7,    # Home on arrow keypad */
    'KEY_UP'              : 0xC8,    # UpArrow on arrow keypad */
    'KEY_PRIOR'           : 0xC9,    # PgUp on arrow keypad */
    'KEY_LEFT'            : 0xCB,    # LeftArrow on arrow keypad */
    'KEY_RIGHT'           : 0xCD,    # RightArrow on arrow keypad */
    'KEY_END'             : 0xCF,    # End on arrow keypad */
    'KEY_DOWN'            : 0xD0,    # DownArrow on arrow keypad */
    'KEY_NEXT'            : 0xD1,    # PgDn on arrow keypad */
    'KEY_INSERT'          : 0xD2,    # Insert on arrow keypad */
    'KEY_DELETE'          : 0xD3,    # Delete on arrow keypad */
    'KEY_LWIN'            : 0xDB,    # Left Windows key */
    'KEY_RWIN'            : 0xDC,    # Right Windows key */
    'KEY_APPS'            : 0xDD,    # AppMenu key */
    'KEY_BACKSPACE'       : 0x0E,            # backspace */
    'KEY_NUMPAD_STAR'     : 0x37,        # * on numeric keypad */
    'KEY_LALT'            : 0x38,           # left Alt */
    'KEY_CAPSLOCK'        : 0x3A,         # CapsLock */
    'KEY_NUMPAD_MINUS'    : 0x4A,        # - on numeric keypad */
    'KEY_NUMPAD_PLUS'     : 0x4E,             # + on numeric keypad */
    'KEY_NUMPAD_PERIOD'   : 0x53,         # . on numeric keypad */
    'KEY_NUMPAD_SLASH'    : 0xB5,          # / on numeric keypad */
    'KEY_RALT'            : 0xB8,           # right Alt */
    'KEY_UPARROW'         : 0xC8,              # UpArrow on arrow keypad */
    'KEY_PGUP'            : 0xC9,           # PgUp on arrow keypad */
    'KEY_LEFTARROW'       : 0xCB,            # LeftArrow on arrow keypad */
    'KEY_RIGHTARROW'      : 0xCD,           # RightArrow on arrow keypad */
    'KEY_DOWNARROW'       : 0xD0,            # DownArrow on arrow keypad */
    'KEY_PGDN'            : 0xD1            # PgDn on arrow keypad */
}

keyBindsPath = environ['LOCALAPPDATA']+"\Frontier Developments\Elite Dangerous\Options\Bindings"
latestBindsPath = ""

def keyTranslate(keyName,logger=None):
    if keyName in convert_to_direct_keys: keyName = convert_to_direct_keys[keyName]
    keyName = keyName.upper()
    if keyName not in SCANCODE: 
        if logger is not None: logger.critical(f"{keyName} is not in SCANCODE list!!")
        else: print(f"{keyName} is not in SCANCODE list!!")
        return 0x0
    return SCANCODE[keyName]

def init_keybinds(logger=None):
    global keysDict, aliasDict, latestBindsPath
    list_of_bindings = [join(keyBindsPath, f) for f in listdir(keyBindsPath) if isfile(join(keyBindsPath, f)) and f.endswith('.binds')]
    if not list_of_bindings: 
        latestBindsPath = ''
        if logger is not None:
            logger.critical('No keybinds found, please check your game settings!')
        else: print('No keybinds found')
        return
    else: latestBindsPath = max(list_of_bindings, key=getmtime)
    origin = parse(latestBindsPath)
    rootNode = origin.documentElement
    if rootNode.hasAttribute('PresetName'): 
        presetName = rootNode.getAttribute('PresetName')
        if rootNode.hasAttribute('MajorVersion'): 
            presetName += "."+rootNode.getAttribute('MajorVersion')
            if rootNode.hasAttribute('MinorVersion'): presetName += "."+rootNode.getAttribute('MinorVersion')
        if logger is not None:
            logger.info('Parsing keybinds: '+presetName)
        else: print('Parsing keybinds: '+presetName)
    emptyKeys = []
    successKeys = 0
    for keyName in defaultDict:
        if keyName[0].isupper(): # start from capital
            if keyName in aliasDict:
                keybind = rootNode.getElementsByTagName(aliasDict[keyName])[0]
            else: keybind = rootNode.getElementsByTagName(keyName)[0]
            dKeys = [] # duplicated key list
            if keyName in duplicatedKeysDict: # we need to check if duplicated
                duplicatedKeyName = duplicatedKeysDict[keyName][0]
                try:
                    k = rootNode.getElementsByTagName(duplicatedKeyName)[0]
                    p = k.getElementsByTagName('Primary')[0]
                    if p.getAttribute('Device') == 'Keyboard': # get all keys
                        pKey = keyTranslate(p.getAttribute('Key'),logger=logger)
                        if pKey != 0x0: dKeys.append(pKey)
                    s = k.getElementsByTagName('Secondary')[0]
                    if s.getAttribute('Device') == 'Keyboard': 
                        sKey = keyTranslate(s.getAttribute('Key'),logger=logger)
                        if sKey != 0x0: dKeys.append(sKey)
                except:
                    pass
            primary = keybind.getElementsByTagName('Primary')[0]
            primaryDevice = primary.getAttribute('Device')
            if primaryDevice == 'Keyboard' and not keyName.endswith('_Alt'):
                key = keyTranslate(primary.getAttribute('Key'),logger=logger)
                if key != 0x0:
                    defaultDict[keyName] = key
                    successKeys += 1
                    if key in dKeys and logger is not None: logger.warn(duplicatedKeysDict[keyName][1])
                    # print("Successfully added "+keyName+" "+key+" "+hex(keyTranslate(key)))
                    continue 
            # fall to secondary
            second = keybind.getElementsByTagName('Secondary')[0]
            secondDevice = second.getAttribute('Device')
            if secondDevice == 'Keyboard':
                key = keyTranslate(second.getAttribute('Key'),logger=logger)
                if key != 0x0:
                    defaultDict[keyName] = key
                    successKeys += 1
                    if key in dKeys and logger is not None: logger.warn(duplicatedKeysDict[keyName][1])
                    # print("Successfully added "+keyName+" "+key+" "+hex(keyTranslate(key)))
                    continue
            if keyName.endswith('_Alt') and logger is not None:
                logger.warn(f'For capability, Key {keyName} needs a secondary key setting while we failed to find it.')
            emptyKeys.append(keyName)# no key is specific
    if len(emptyKeys)>0:
        if logger is not None:
            logger.critical(f'Error in setting keybind(s): {str(emptyKeys)}')
            logger.critical('You may have to bind the keybind(s) in game manually')
        else: 
            print(f'Error in setting keybind(s): {str(emptyKeys)}')
            print('You may have to bind the keybind(s) in game manually')
    if logger is not None: logger.info(f'Successfully added {successKeys} keybinds, {len(emptyKeys)} failed.')
    else: print(f'Successfully added {successKeys} keybinds, {len(emptyKeys)} failed.')
    return defaultDict

def typewrite(text:str) -> bool:
    try:
        for word in text:
            if word == ' ': hexCodeEntry = 'KEY_SPACE'
            elif word == '-': hexCodeEntry = 'KEY_MINUS'
            else: hexCodeEntry = f'KEY_{word.upper()}'
            PressKey(SCANCODE[hexCodeEntry])
            time.sleep(0.18)
            ReleaseKey(SCANCODE[hexCodeEntry])
    except:
        traceback.print_exc()
