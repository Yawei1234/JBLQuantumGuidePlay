frequency = 0
volume = 0
currentOctive = 2
waveform = 'square'
runCV = False
runCVRadar = False
runTheremin = False
runCardinal = False
energyMode = "stop"
delta = 0
captureBackground = False
lastRadarFrame = None
radarRunning = False
radarProcessing = False
captureRunning = False
appName = "guide-play-1.0.1.16"
resolutions = []
screens = []
defaultResolution = None
monitors = []
monitorSelected = 1
radarTrackeds = []
port_server = 5005
port_app = 5006
devMode = False
defaultConfig = {
    "ScreenReader": {
        "icon": "default",
        "desc": "IN-GAME SCREEN READER",
        "tabIndex": 0,
        "full_desc": "This option reads aloud the text on the screen, it will help you access menu options, read UI\n game elements, such as inventory, and provide spoken guidance for text clues over the game \nthat indicate actions like open doors, to arm or disarm bombs and so on.",
        "subItems": [
            {
                "id": "InGameScreenReader",
                "title": "Enable in-game screen reader",
                "type": "switch",
                "value": "on",
                "tabIndex": 0
            },
            {
                "id": "InGameThereminMenus",
                "title": "Enable theremin effect over menus",
                "type": "switch",
                "value": "on",
                "tabIndex": 1
            },
            {
                "id": "InGameCompassVoice",
                "title": "Enable compass direction voiceover",
                "type": "switch",
                "value": "on",
                "tabIndex": 2
            },
            {
                "id": "InGameSectorVoice",
                "title": "Enable map location report",
                "type": "switch",
                "value": "on",
                "tabIndex": 3
            },
            {
                "id": "SpeechSpeed",
                "title": "Speech speed",
                "type": "spin",
                "label": "x",
                "value": 5,
                "range": "1-5",
                "tabIndex": 4
            },
            {
                "id": "Volume",
                "title": "Volume",
                "type": "rate",
                "value": "100",
                "range": "0-100",
                "tabIndex": 5
            }
        ]
    },
    "EnvironmentNavigation": {
        "icon": "default",
        "desc": "ENVIRONMENT NAVIGATION",
        "tabIndex": 1,
        "full_desc": "Get aware of obstacles, walls and other elements in the game map, \nso you can move better, without being stuck while walking.",
        "subItems": [
            {
                "id": "EnvironmentAlerts",
                "title": "Enable environment alerts",
                "type": "switch",
                "value": "off",
                "tabIndex": 0
            },
            {
                "id": "SfxVolume",
                "title": "SFX Volume",
                "type": "rate",
                "value": "100",
                "range": "0-100",
                "tabIndex": 1
            },
            {
                "id": "SfxSelect",
                "type": "combo",
                "title": "Select SFX file",
                "value": "beep_sonar.wav",
                "tabIndex": 2
            }
        ]
    },
    "TeamProximity": {
        "icon": "default",
        "desc": "TEAM PROXIMITY",
        "tabIndex": 2,
        "full_desc": "Through a spatial audio feature, know your team location",
        "subItems": [
            {
                "id": "TeamProximityAlerts",
                "title": "Enable team proximity",
                "type": "switch",
                "value": "on",
                "tabIndex": 0
            },
            {
                "id": "SfxVolume",
                "title": "SFX Volume",
                "type": "rate",
                "value": "100",
                "range": "0-100",
                "tabIndex": 1
            },
            {
                "id": "SfxSelect",
                "type": "combo",
                "title": "Select SFX file",
                "value": "_wzy_aim_a0_01.wav",
                "tabIndex": 2
            }
        ]
    },
    "EnemyProximity": {
        "icon": "default",
        "desc": "ENEMY PROXIMITY",
        "tabIndex": 3,
        "full_desc": "Using 360 sound effects, discover the enemy's \n position in front of you or other enemies' location shown in the game minimap.",
        "subItems": [
            {
                "id": "EnemyProximityAlerts",
                "title": "Enable enemy proximity",
                "type": "switch",
                "value": "on",
                "tabIndex": 0
            },
            {
                "id": "SfxVolume",
                "title": "SFX Volume",
                "type": "rate",
                "value": "100",
                "range": "0-100",
                "tabIndex": 1
            },
            {
                "id": "SfxSelect",
                "type": "combo",
                "title": "Select SFX file",
                "value": "_wzy_aim_a1_01.wav",
                "tabIndex": 2
            }
        ]
    },
    "AimAlerts": {
        "icon": "default",
        "desc": "AIM ALERTS",
        "tabIndex": 4,
        "full_desc": "Time to fire! There is an enemy in your -- sights shoot, shoot, shooot!",
        "subItems": [
            {
                "id": "AimAlertsAlerts",
                "title": "Enable aim alerts",
                "type": "switch",
                "value": "on",
                "tabIndex": 0
            },
            {
                "id": "SfxVolume",
                "title": "SFX Volume",
                "type": "rate",
                "value": "100",
                "range": "0-100",
                "tabIndex": 1
            },
            {
                "id": "SfxSelect",
                "type": "combo",
                "title": "Select SFX file",
                "value": "beep_aim.wav",
                "tabIndex": 2
            }
        ]
    },
    "EnemyKilled": {
        "icon": "default",
        "desc": "ENEMY KILLED",
        "tabIndex": 5,
        "full_desc": "Get feedback when your kill is confirmed.",
        "subItems": [
            {
                "id": "EnemyKilledAlerts",
                "title": "Enable kill feedback",
                "type": "switch",
                "value": "on",
                "tabIndex": 0
            },
            {
                "id": "SfxVolume",
                "title": "SFX Volume",
                "type": "rate",
                "value": "100",
                "range": "0-100",
                "tabIndex": 1
            },
            {
                "id": "SfxSelect",
                "type": "combo",
                "title": "Select SFX file",
                "value": "_wzy_enemydown_a1_01.wav",
                "tabIndex": 2
            }
        ]
    },
    "IncomingDamageDirection": {
        "icon": "default",
        "desc": "INCOMING DAMAGE DIRECTION",
        "tabIndex": 6,
        "full_desc": "Hey, you got hurt! Discover where the damage comes from. \n It could be a bomb explosion nearby, or someone shooting or stabbing you. ",
        "subItems": [
            {
                "id": "DamageDirectionAlerts",
                "title": "Enable damage direction feedback",
                "type": "switch",
                "value": "on",
                "tabIndex": 0
            },
            {
                "id": "SfxVolume",
                "title": "SFX Volume",
                "type": "rate",
                "value": "100",
                "range": "0-100",
                "tabIndex": 1
            },
            {
                "id": "SfxSelect",
                "type": "combo",
                "title": "Select SFX file",
                "value": "_wzy_enemydetected_a1_01.wav",
                "tabIndex": 2
            }
        ]
    }
}
