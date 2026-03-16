

# IN-GAME SCREEN READER

# This option reads aloud the text on the screen, it will help you access menu options,
# read UI game elements, such as inventory, and provide spoken guidance
#  for text clues over the game that indicate actions like open doors, to arm or disarm bombs and so on.

# Enable in-game screen reader
# Speech speed
# Volume


# ENVIRONMENT NAVIGATION

# Get aware of obstacles, walls and other elements in the game map,
# so you can move better, without being stuck while walking.

# Enable environment alerts
# SFX Volume


# TEAM PROXIMITY
# Through a spatial audio feature, know your team location
# as they are near you.

# Enable team proximity
# SFX Volume


# ENEMY PROXIMITY
# Using 360 sound effects, discover the enemy's
# position in front of you or other enemies' location shown in the game minimap.

# Enable enemy proximity

# SFX Volume


# AIM ALERTS
# Time to fire! There is an enemy in your sights — shoot, shoot, shooot!
# Enable aim alerts
# SFX Volume


# ENEMY KILLED
# Get feedback when your kill is confirmed.
# Enable kill feedback
# SFX Volume

# INCOMING DAMAGE DIRECTION
# Hey, you got hurt! Discover where the damage comes from.
# It could be a bomb explosion nearby, or someone shooting or stabbing you.

# Enable damage direction feedback
# SFX Volume


from typing import Optional, Tuple, Union
from subprocess import run, Popen, PIPE, STDOUT
from threading import Timer, Thread
import threading
import os
from pystray import MenuItem as item
import pystray
from pythonosc import udp_client, osc_server
from pythonosc.dispatcher import Dispatcher
import data
import json
import time
import logcontrol
import logging
import threadmanager
import argparse
import sys
import webview
import pyautogui
import asyncio
import websockets
from steamHacks import SteamHacks as steam
# import game processes
from PIL import Image, ImageTk
from capture_WC import cvFullCapture
from theremin import Theremin
from pipe_radar import *
from mss import mss
from utils import get_active_window, checkNarrator, find_window_wildcard, focus_guideplay, checkRunningProcess, set_active_on_top, is_running_as_admin
from screenInfo import getDPITK, on_set_resolution, getVideoModes, get_screen_resolution, get_screen_resolution_methods
import ctypes.wintypes


from AppComponents.mr_API import *
from AppComponents.mr_importer import *
from AppComponents.mr_windowinfo import windowinfo

from subStarter import SubStarter
# from sharedMemo import update_aim, update_enemy, update_friend, clearUltra

CSIDL_PERSONAL = 5       # My Documents
SHGFP_TYPE_CURRENT = 0   # Get current, not default value
pathBUF = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
ctypes.windll.shell32.SHGetFolderPathW(
    None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, pathBUF)

os.chdir(os.path.dirname(os.path.abspath(__file__)))
PhotoImage = ImageTk.PhotoImage
currentDir = os.getcwd()
client = udp_client.SimpleUDPClient("127.0.0.1", data.port_server)

logfile = "threadLogs.log"
logger = logging.getLogger()
logcontrol.set_log_file(logfile, max_size=64000)
logcontrol.set_level(logging.DEBUG)


global devMode
global app
global mywindow
global documentsPath

documentsPath = pathBUF.value


class GameApp():

    def __init__(self, serverCallback=None, devMode=False, parentRef=None):
        self.game = None
        self.radar = None
        self.gameThread = None
        self.radarThread = None
        self.gameIsAlive = False
        self.radarIsAlive = False
        self.threadCVGamePlay = None
        self.threadCVTheremin = None
        self.serverCallback = serverCallback
        self.parentRef = parentRef
        self.resolutions = []
        self.monitors = []
        self.screens = webview.screens
        self.devMode = devMode
        self.isQuitting = False
        self.serverReady = False
        self.captureFailCount = 0
        self.captureRetryBlockedUntil = 0

        # game states
        self.gameState = "guideplay-ui"
        self.playerOnRadar = False
        self.screenTemplate = "guideplay-ui"
        self.match = {
            "type": "match",
            "round": 0,
            "map": "",
            "score": {
                "ct": 0,
                "ts": 0
            },
        }
        self.round = {
            "type": "round",
            "roundId": 0,
            "team": "nf",
            "lifelevel": 100,
            "armor": 0,
            "total_damages": 0,
            "damages": [],
            "alive": {
                    "ct": 0,
                    "ts": 0
            },
            "time_left": 0,
            "bomb": {
                "planted": False,
                "defused": False,
                "exploded": False,
                "exploded_at": 0,
                "defused_at": 0
            }
        }
        self.matches = []
        self.rounds = [

        ]
        self.gameStateResetTimer = None
        self.bestTargets = 0
        self.aimplusTargets = 0
        self.aimaligned = False
        self.lastSetStateTime = time.time() + 5

        self.primaryMonitor, monitorsList, primaryIndex = self.getMonitors()

        time.sleep(1)
        # Theremin props
        width, height = data.defaultResolution.width, data.defaultResolution.height
        self.there = Theremin(width, height, self.updateTheremin, self.devMode)
        self.there.send = self.receiveFromCapture
        self.there.parentREF = self
        self.thereX = 0
        self.thereY = 0
        self.lastThereX = 0
        self.lastThereY = 0
        self.lastThereUpdate = time.time()
        self.screenReaderSectors = []
        self.currentTemplate = None

        self.cvFullCapture = cvFullCapture
        self.cvFullCapture.defineCapture(
            primaryIndex+1, self.primaryMonitor, monitorsList)
        self.cvFullCapture.parentRef = self
        self.cvFullCapture.callback = self.receiveFromCapture
        self.cvFullCapture.checker = self.checkGameState
        self.cvFullCapture.startCapturePipes(
            self.receiveFromCapture, self.devMode)

    def getMonitors(self):
        for i in range(len(mss().monitors)):
            monitor = mss().monitors[i]
            self.resolutions.append(
                (monitor["top"], monitor["left"], monitor["width"], monitor["height"]))
            self.monitors.append("Monitor " + str(i + 1))
        data.resolutions = self.resolutions
        data.monitors = self.monitors
        data.screens = webview.screens
        for i, screen in enumerate(data.screens):
            if i == 0:
                data.defaultResolution = screen
            print("WEBVIEW_SCREEN", i, screen)
        print("WEBVIEW_SCREEN_DEFAULT", data.defaultResolution)

        result = get_screen_resolution()

        monitorsList = result[0]
        findPrimary = result[1]
        monitorIndex = result[2]

        # Pick the webview screen that matches the primary monitor resolution
        if findPrimary is not None:
            try:
                primary_w, primary_h = (int(x) for x in findPrimary[1].split('x'))
                for screen in data.screens:
                    if screen.width == primary_w and screen.height == primary_h:
                        data.defaultResolution = screen
                        print("WEBVIEW_SCREEN_PRIMARY_MATCH", screen)
                        break
            except Exception as e:
                print("WEBVIEW_SCREEN_PRIMARY_MATCH_ERROR", e)

        return findPrimary, monitorsList, monitorIndex

    def checkGameState(self, reason=None):
        lastGameState = self.getGameState()
        # print("CHECKING_GAME_STATE", lastGameState, reason)
        if reason == "isHomeScreen":
            if lastGameState == "home":
                return True
            return False

        if reason == "roundRunning":
            if self.isQuitting == True:
                self.stopService("cv-fullcapture")
                self.stopService("cv-radar")
                self.stopService("cv-theremin")
                return False
            if lastGameState == "spectator" or lastGameState == "ingame-spectator":
                return False
            if lastGameState != "ingame-spectator" and \
                    lastGameState != "ingame-menu" and \
                    lastGameState != "home" and \
                    lastGameState != "gameplay-ui" and \
                    lastGameState != "loading":
                return True

        return False

    def getGameState(self):
        return self.gameState

    def setGameState(self, state, template=None, rest=None):
        # print("SETING GAME STATE", state)

        # TO-DO: check if state is valid
        # if state == self.gameState:
        #     print("REJECTED")
        #     return
        self.gameState = state
        if rest is not None:
            if rest['playerOnRadar'] is not None:
                self.playerOnRadar = rest['playerOnRadar']
        # if template is not None:
        #     self.screenTemplate = template
        #     self.there.currentTemplate = '144126_home_play_practice'
        self.lastSetStateTime = time.time()

        # set time to reset game state
        # if self.gameStateResetTimer is not None:
        #     self.gameStateResetTimer.cancel()
        # if self.gameState != "guideplay-ui" and self.gameState != "guideplay-exit":

        #     if self.isQuitting == False:
        #         self.gffameStateResetTimer = Timer(
        #             5, lambda: self.resetGameState()).start()
        #         print("RESETING GAME STATE TIMER", self.gameStateResetTimer)
        # broadCast game state
        # self.serverCallback("/gamestate", self.gameState)

    def resetGameState(self):
        print("RESETING GAME STATE")
        self.lastSetStateTime = time.time()
        self.gameState = "unknown"
        self.serverCallback("/gamestate", self.gameState)

    def updateTheremin(self, _width, _height, _x, _y, volume, freq, waveform, status):

        if self.gameState == "guideplay-exit" or self.gameState == "unknown":
            return

        if data.defaultResolution is None:
            return

        if self.parentRef is not None:
            SR = self.parentRef.get_subitem(
                "ScreenReader", "InGameScreenReader")
            if SR["value"] == "off":
                return

            TH = self.parentRef.get_subitem(
                "ScreenReader", "InGameThereminMenus")
            if TH["value"] == "off":
                return

        # print("UPDATE THEREMIN", _x, _y, volume, freq, waveform, status)

        if _x != self.lastThereX or _y != self.lastThereY:

            self.thereX = _x
            self.thereY = _y

            self.lastThereX = _x
            self.lastThereY = _y

            self.lastThereUpdate = time.time()

            # print("UPDATE THEREMIN", _x, _y, volume, freq, waveform, status)

            setStateJSON({
                "x": _x,
                "y": _y,
                "volume": volume,
                "freq": freq,
                "waveform": waveform,
                "status": status,
                "width": _width,
                "height": _height

            }, "theremin")

    def updateMatch(self, key=None, value=None):
        if key is None:
            self.match = value
        else:
            self.match[key] = value
        self.serverCallback("/match", self.match)

    def updateRound(self, key=None, value=None):
        if key is None:
            self.round = value
        else:
            self.round[key] = value
        self.serverCallback("/round", self.round)

    def filterEnemyIfAIM(self, trackeds):

        friends = []
        enemies = []
        finalTrackeds = []

        for tracked in trackeds:
            if "enemy" in tracked["class"]:
                if self.aimaligned == False and self.aimplusTargets < 1:
                    enemies.append(tracked)
            else:
                friends.append(tracked)

        if self.aimaligned == False and len(enemies) < 1:
            self.bestTargets = 0

        if self.aimaligned == True and self.aimplusTargets > 0:
            self.bestTargets = 1

        aim = self.parentRef.get_subitem(
            "AimAlerts", "AimAlertsAlerts")
        if aim["value"] == "on":
            if self.bestTargets > 0:
                finalTrackeds = friends
            else:
                finalTrackeds = friends + enemies
        else:
            finalTrackeds = friends + enemies

        return finalTrackeds

    def receiveFromCapture(self, *params, **kwargs):
        topic = params[0]

        if len(params) > 0:
            # if contains /screenreader on topic
            if "/screenreader/" in topic:
                tags = topic.split("/")

                # print("*********** SCREEN READER", tags, len(tags))

                if len(tags) == 3:
                    if tags[2] == "update-categories":
                        self.screenReaderSectors = params[1]
                        # print("updating-sector-categories", params[1])
                    elif tags[2] == "current-template":
                        print("updating-sector-templates", params[1])
                        self.currentTemplate = params[1]

                    else:
                        self.serverCallback(topic, params[1])
                return
            # if topic == "/screenreader/":
            #     # print("TOPMENU", params[1])
            #     self.serverCallback(topic, params[1])
            #     return
            if topic == "/roundstate":
                self.serverCallback(topic, params[1], params[2])
                self.round["roundId"] = params[2]["roundId"]
                self.round["team"] = params[2]["team"]
                self.round["time_left"] = params[2]["time_left"]

                # print("ROUND_STATE", params[1], params[2])
                return
            if topic == "/aim_damage":
                self.serverCallback(topic, params[1])
                return
            if topic == "/aimplus":
                self.aimplusTargets = len(params[1])
                self.serverCallback(topic, params[1])
                return
            if topic == "/aim_cross":
                print("AIM CROSS", params[1], params[1])
                return
            if topic == "/aim":
                self.bestTargets = int(params[2])
                if self.aimaligned == False:
                    self.serverCallback(topic, params[1])
                return
            if topic == "/binarymap":
                # print("BINARY_MAP", params[1])
                self.serverCallback(topic, params[1])
                return
            if topic == "/floorgrid":
                # print("BINARY_MAP", params[1])
                self.serverCallback(topic, params[1])
                return

            if topic == "/trackeds":
                print("[GUI_DEBUG] /trackeds before filter:", len(params[1]), "aimaligned:", self.aimaligned, "aimplusTargets:", self.aimplusTargets)
                trackedsIncome = self.filterEnemyIfAIM(params[1])
                print("[GUI_DEBUG] /trackeds after filter:", len(trackedsIncome))
                self.serverCallback(topic, trackedsIncome)
                return
            if topic == "/obstacles":
                self.serverCallback(topic, params[1])
                return

            if topic == "/address":
                self.serverCallback(topic, params[1])
                return
            if topic == "/cardinal":
                self.serverCallback(topic, params[1])
                return
            if topic == "/gamestate":
                stateName = params[1]
                stateTemplate = params[2]['detail']
                self.aimaligned = params[2]['aimaligned']
                self.setGameState(stateName, stateTemplate, params[2])
                self.serverCallback(topic, stateName, params[2])
                return

        # enunmerate index and value
        # for i, j in enumerate(args):
        #     print("NEW_ARG\n")
        #     print(i, j)
        return
        print('\nFULLCAPTURE____keywords are:')
        for k in kwargs:
            print(k)

    def stopService(self, process="cv-fullcapture"):

        if process == "cv-radar":
            data.runCVRadar = False
            data.runCV = False

        if process == "cv-fullcapture":
            if self.threadCVGamePlay is not None:

                self.cvFullCapture.stopRawCapture()

                if self.threadCVGamePlay.is_alive() == True:
                    self.threadCVGamePlay.join()
                    self.threadCVGamePlay = None
                    data.runCV = False
                    data.runCardinal = False
                    logging.info('process_stopped_cv-fullcapture')

            data.runCV = False

        if process == "cv-theremin":
            if self.threadCVTheremin is not None:
                data.runTheremin = False
                # check if is running
                # if running stop it
                if self.threadCVTheremin.is_alive() == True:
                    self.threadCVTheremin.join()
                    self.threadCVTheremin = None
                    logging.info('process_stopped_cv-theremin')

            data.runTheremin = False

    def startService(self, process):

        if process == "cv-fullcapture":
            data.runCV = True
            logging.info('process_started-cv-fullcapture')

            if self.threadCVGamePlay == None:
                self.threadCVGamePlay = threading.Thread(target=self.cvFullCapture.startRawCapture,
                                                         args=(
                                                             self.checkGameState, self.devMode),
                                                         name="cv-fullcapture",
                                                         daemon=True)
                self.threadCVGamePlay.start()
            elif self.threadCVGamePlay != None:
                if self.threadCVGamePlay.is_alive() == False:
                    self.threadCVGamePlay = threading.Thread(target=self.cvFullCapture.startRawCapture,
                                                             args=(
                                                                 self.checkGameState, self.devMode),
                                                             name="cv-fullcapture",
                                                             daemon=True)
                    self.threadCVGamePlay.start()

        if process == "cv-theremin":

            logging.info('process_started-theremin')
            print("STARTING THEREMIN")

            if self.threadCVTheremin == None:
                data.runTheremin = True
                self.threadCVTheremin = threading.Thread(target=self.there.startThereminCapture,
                                                         name="cv-theremin",
                                                         daemon=True)
                self.threadCVTheremin.start()
            elif self.threadCVTheremin != None:
                data.runTheremin = True
                if self.threadCVTheremin.is_alive() == False:
                    self.threadCVTheremin = threading.Thread(target=self.there.startThereminCapture,
                                                             name="cv-theremin",
                                                             daemon=True)
                    self.threadCVTheremin.start()


class ApiDev():

    def __init__(self, app):
        self.app = app

    def get_config(self, key):
        return self.app.get_subitem(key)

    def set_config(self, key, value):
        self.app.set_subitem(key, value)

    def get_state(self, key):
        return self.app.get_state(key)

    def set_state(self, key, value):
        self.app.set_state(key, value)

    def sync_state(self, key, value):
        self.app.sync_state(key, value)

    def sync_game(self, key, value, extras=None):
        self.app.sync_game(key, value, extras)

    def toggle_service(self, key, value):
        self.app.toggle_service(key, value)

    def update_prop(self, pipename, key, value):
        # if pipename == 'floorRadar':
        #     value = value

        self.app.devUpdateProp(pipename, key, value)

    def quit_root(self):
        self.app.quit_root()


class App():
    global tm
    global devMode
    global mywindow

    DIRPATH = os.path.join(os.path.dirname(__file__))
    LOADED_IMAGES = {}

    threadmanager.enable_statistics()
    tm = threadmanager.ThreadManager("gui_root", monitor_interval=1.0)

    ####################################

    def __init__(self):
        super().__init__()
        self.devMode = devMode
        self.processController = None
        self.steamController = steam(self)
        self.steamControllerThread = None
        self.lastSay = "welcome to guide play"
        self.sayTime = Timer(2, lambda: self.sendSay())
        self.sayTime.start()
        self.isQuitting = False
        self.isAdmin = is_running_as_admin()
        self.warnedNonAdminCapture = False
        self.title = "Guide Play"
        self.version = "1.0.1.16"
        self.width = int(1280)
        self.height = int(720)

        self.machineResolution = None

        self.trayImage = Image.open("assets/app-icon.ico")
        self.trayMenu = (item('Audio Settings', lambda: self.show_window(None, "AUDIO SETTINGS")), item(
            'About Guide Play', lambda: self.show_window(None, "ABOUT")), item('Exit Guide Play', self.quit_tray), )

        self.trayIcon = pystray.Icon(
            "name", self.trayImage, "Guide Play", self.trayMenu)
        self.trayIcon.run_detached()

        # self.bindKeys()
        self.useOSC = False
        self.datamodel = []
        self.mywindow = None
        self.mywindowDev = None
        self.currentItems = []
        self.currentSubItem = None
        self.lastScreenRead = ""
        self.tabIndex = 0
        self.rootIndex = 0
        self.tabIndexSub = 0
        self.wavs = []
        self.messsageQ = []
        self.lastMessageQ = None
        self.lastScreenAddress = ""
        self.narratorTimer = None
        self.narratorIsOn = False
        self.debugStateFlow = self.devMode
        self._lastDebugSignature = {}
        self._lastDebugTime = {}

        self.menuItems = ["AUDIO SETTINGS", "SPATIAL TESTS", "ABOUT"]
        # if not devMode remove SPATIAL TESTS
        if self.devMode == False:
            self.menuItems.remove("SPATIAL TESTS")
            # self.menuItems.remove("VIDEO SETUP")

        self.currentMenu = None
        self.data = {}
        self.rootTabIndex = 0

        self.testLocked = False

        # services processess
        self.thereminStopCountDown = 5
        self.crashTimes = 0
        self.lastKeepAlive = -1
        self.lastKeepAliveMSG = -1
        self.serverIsAlive = False
        self.serverThread = None
        self.gameStateManagerThread = None
        self.bootDone = False
        self.captureFailCount = 0
        self.captureRetryBlockedUntil = 0
        self.captureDisabled = False

        # window webview
        self.HTMLPath = os.path.join(App.DIRPATH, "UI", "index.html")
        self.winIcon = 'images/app-icon-3x.png'

        # class init into mywindow as object with Appname AppVer targetwindow ...
        self.mywindow = windowinfo(self.title, self.version, 'targetwindow will self write from mywindow.targetwindow=targetwindow',
                                   self.devMode, self.HTMLPath, self.width, self.height, self.winIcon)

        # APi class in mr_API.py control window functions
        self.api = Api(self)
        self.apiDev = ApiDev(self)
        self.devWindow = None
        self.useDevWindow = False
        min_size = (self.mywindow.AppSizeW, self.mywindow.AppSizeH)
        targetwindow = webview.create_window(self.mywindow.Appname,
                                             self.mywindow.HTMLPath, focus=True,
                                             width=self.mywindow.AppSizeW, height=self.mywindow.AppSizeH,
                                             resizable=True,
                                             on_top=False,
                                             easy_drag=False,
                                             min_size=min_size,
                                             background_color="#000000",
                                             screen=data.defaultResolution,
                                             frameless=True, js_api=self.api)

        # Set window handler into mywindow Object
        self.mywindow.targetwindow = targetwindow

        # Trigger Events Tester optional can comment out all
        targetwindow.events.closed += lambda: on_closed(
            self.mywindow, self.quit_root)
        targetwindow.events.closing += lambda: on_closing(self.mywindow)
        targetwindow.events.shown += lambda: on_shown(self.mywindow)
        targetwindow.events.loaded += lambda: on_loaded(
            self.mywindow, self.on_loaded_boot)
        targetwindow.events.minimized += lambda: on_minimized(self.mywindow)
        targetwindow.events.maximized += lambda: on_maximized(self.mywindow)
        targetwindow.events.restored += lambda: on_restored(self.mywindow)

        # self.bootUp()

        tm.add_idle_callback(self.log_time, "app-ui-started")
        tm.add_start_callback(self.log_time, "app-ui-started-01")
        tm.add_stop_callback(self.log_time, "app-ui-started-02")

        self.log_time("app-ui-starting-webview")
        print("PRIVILEGE_STATUS", "admin" if self.isAdmin else "non-admin")

        try:
            # Close the splash screen.
            import pyi_splash
            pyi_splash.close()
        except ImportError:
            # Otherwise do nothing.
            pass

        # Window Start call. with Debug Server and User Agent
        webview.start(debug=False,
                      http_server=False, user_agent=None)

    def log_time(self, item: str):
        print(f"{time.time()} - {item}")
        logger.debug(item)

    def on_loaded_boot(self, window):
        print("on_loaded_boot", window)
        self.bootUp()

    def checkSteamPatch(self):
        try:
            print("================= CHECKING STEAM PATCH")
            cs2Found = False
            # get the steam path
            result = self.steamController.find_steam_path(self.devMode)
            print("================= CHECKING STEAM PATCH - steamPath found", result)
            if result is not None:
                cs2Found = True
                print("--- steamPath OK", result)

            if cs2Found == False:
                modalHTML = self.generateModalData("",
                                                   "Steam not found", "Steam not found, please install steam and try again", "Close", onQuit="pywebview.api.topbar('close')", say=True)
                self.stateTransfer("showModal", "showModal", True)
                self.stateTransfer("modalData", "modalData", modalHTML)
                return

            # get the libraryfolders.vdf path
            print("================= CHECKING STEAM PATCH - libraryfolder ")
            result = self.steamController.find_libraryfolders_vdf()
            if result is None:
                modalHTML = self.generateModalData(
                    "", "Steam Patch Failed", "libraryfolders.vdf not found", "Close")
                self.stateTransfer("showModal", "showModal", True)
                self.stateTransfer("modalData", "modalData", modalHTML)
                return
            print("--- libraryfolders.vdf OK", result)

            # get the localconfig.vdf path
            print("================= CHECKING STEAM PATCH - localconfig")
            result = self.steamController.find_localconfig_vdf()
            if result is None:
                modalHTML = self.generateModalData(
                    "", "Steam Patch Failed", "localconfig.vdf not found", "Close")
                self.stateTransfer("showModal", "showModal", True)
                self.stateTransfer("modalData", "modalData", modalHTML)
                return

            print("--- localconfig.vdf OK", len(result))
            print("================= CHECKING STEAM PATCH - update_autoexec", result)

            # read autoexec.cfg ORIGINAL
            # read autoexec.cfg from asset folder
            autoexecP = os.path.join(App.DIRPATH, "assets", "cfg", "autoexec.cfg")
            with open(autoexecP, "r") as f:
                autoexec = f.read()
                # replace {{VERSION}}
                autoexec = autoexec.replace("{{VERSION}}", "["+self.version+"]")

            # find the path of the Counter-Strike 2 folder
            result = self.steamController.find_cs2_path()
            if result is not None:
                print("--- Counter-Strike 2 path OK", result)

                # update autoexec.cfg
                result = self.steamController.update_autoexec(
                    result, autoexec, self.version)
                if result is not None:
                    print("--- autoexec.cfg updated", result)
                else:
                    print("--- autoexec.cfg not updated", result)
            else:
                print("--- Counter-Strike 2 path not found", result)
                modalHTML = self.generateModalData("", "Counter-Strike 2 not found",
                                                   "Counter-Strike 2 not found, please install and try again", "Close")
                self.stateTransfer("showModal", "showModal", True)
                self.stateTransfer("modalData", "modalData", modalHTML)
                return

            # parse result
            print("================= CHECKING STEAM PATCH - parse_localconfig", result)
            if result is not None:
                kv, parsed = self.steamController.parse_localconfig_vdf()
                if kv is None:
                    modalHTML = self.generateModalData(
                        "", "Steam Patch Failed", "Error parsing Steam local config", "Close")
                    self.stateTransfer("showModal", "showModal", True)
                    self.stateTransfer("modalData", "modalData", modalHTML)
                    return
                print(
                    "================= CHECKING STEAM PATCH - parse_localconfig_vdf", len(kv))

                # find steam apps
                # result = self.steamController.find_app_by_id(730)
                try:
                    apps = kv['UserLocalConfigStore']['Software']['Valve']['Steam']['apps']['730']
                    appIds = kv.dump(mapper=apps)
                    print("Counter-Strike 2 =============== \n\n", appIds)
                    # change LaunchOptions
                    # -threads 4
                    commands = [
                        "-novid",
                        "-nojoy",
                        # "-high",
                        # "-tickrate 128",
                        # "-console",
                        "-language english",
                        "-fullscreen",
                        "-w 1920 -h 1080",
                        # "-refresh 144",
                        # "-d3d9ex",
                        "-noaafonts",
                        "-noforcemaccel",
                        "-noforcemspd",
                        "-noforcemparms",
                        "-nojoystick",
                        "-nocrashdialog",
                        "-nohltv",
                        # "-nolockmouse",
                        # "-nomouse",
                        # "-nomicsettings",
                        # "-noplugins",
                        # "-norender",
                        # "-noshader",
                        "-softparticlesdefaultoff",
                        "+r_drawparticles 0",
                    ]
                    commandsStr = " ".join(commands)

                    apps['LaunchOptions'] = "+exec autoexec.cfg "+commandsStr+""
                    print("Counter-Strike 2 patched ============ \n\n",
                          kv.dump(mapper=apps))

                    self.steamController.update_localconfig_vdf(kv)
                    time.sleep(1)
                    if self.devMode:
                        print("CHECKING STEAM PATCH - SKIP_RESTART_STEAM_DEV_MODE")
                        self.stateTransfer(
                            "showModal", "showModal", False)
                        self.stateTransfer(
                            "modalData", "modalData", "")
                        return
                    # restart steam
                    restart = self.steamController.restart_steam()
                    print("restart", restart)
                    if restart:
                        print("Steam restarting...")
                        count = 0

                        while True:
                            if count > 4:
                                print("CHECKING STEAM PATCH - TIMEOUT")
                                modalHTML = self.generateModalData(
                                    "", "Steam Patch Timeout", "Steam restart timeout. Please open Steam manually and try again.", "Close")
                                self.stateTransfer(
                                    "showModal", "showModal", True)
                                self.stateTransfer(
                                    "modalData", "modalData", modalHTML)
                                break
                            result = self.steamController.check_if_steam_is_running()
                            count += 1
                            print("CHECKING STEAM PATCH - RESTARTING", count)
                            if result is not None:

                                print("Steam restarted")
                                print(
                                    "================= CHECKING STEAM PATCH --- COUNTER-STRIKE 2 FOUND")

                                time.sleep(4)
                                self.steamController.minimize_steam()
                                time.sleep(3)
                                try:
                                    self.set_focus("Guide Play")
                                    # self.steamController.focus_guideplay()

                                    self.stateTransfer(
                                        "showModal", "showModal", False)
                                    self.stateTransfer(
                                        "modalData", "modalData", "")

                                    self.say(
                                        "Guide Play started. Audio Settings", 0.5)
                                    break
                                except Exception as e:
                                    print("CHECKING STEAM PATCH - ERROR", e)
                                    self.say(
                                        "Error starting Guide Play. ", 0.5)
                                    self.stateTransfer(
                                        "showModal", "showModal", False)
                                    self.stateTransfer(
                                        "modalData", "modalData", "")

                                    break
                            time.sleep(1)
                    else:
                        time.sleep(2)
                        self.stateTransfer(
                            "showModal", "showModal", False)
                        self.stateTransfer(
                            "modalData", "modalData", "")

                except KeyError as e:
                    appIds = None
                    apps = None
                    print("ERROR-PARSING-COUNTER-STRIKE-CONFIGS", e, kv, parsed)
                    modalHTML = self.generateModalData("",
                                                       "Steam Patch Failed", "Error parsing Steam local config", "Close")
                    self.stateTransfer("showModal", "showModal", True)
                    self.stateTransfer("modalData", "modalData", modalHTML)
                    self.say("Error starting Guide Play. Steam Patch Failed", 0.5)
                # search for id 730

            else:
                modalHTML = self.generateModalData("",
                                                   "Steam Patch Failed", "Steam not found", "Close")
                self.stateTransfer("showModal", "showModal", True)
                self.stateTransfer("modalData", "modalData", modalHTML)
                self.say("Error starting Guide Play. Steam Patch Failed", 0.5)
                print("CHECKING STEAM PATCH - NOT FOUND", result)
        except Exception as e:
            print("CHECKING STEAM PATCH - FATAL", e)
            modalHTML = self.generateModalData(
                "", "Steam Patch Failed", "Unexpected error while checking Steam. Please restart Guide Play.", "Close")
            self.stateTransfer("showModal", "showModal", True)
            self.stateTransfer("modalData", "modalData", modalHTML)

    def generateModalData(self, title, sutitle, message, button, onQuit=None, say=False, spinner=False):

        if say is True:
            textToSay = ""+sutitle+" "+message+""
            self.say(textToSay, 0.5)

        clickClose = "$store.global.showModal = false"
        if onQuit is not None:
            clickClose = onQuit

        spinnerContent = ""
        if spinner is True:
            spinnerContent = """
            <div
                class="app-preloader w-full flex justify-center h-12"
            >
            <div class="app-preloader-inner fixed inline-block h-10 w-10 -ml-10"></div>
            </div>
            """

        if button == "Close":
            button = f"""
            <div class="w-full flex items-center justify-center">
                <button
                    @click="{clickClose}"
                    class="btn mt-6 bg-success font-medium text-white hover:bg-success-focus focus:bg-success-focus active:bg-success-focus/90">
                    Close
                </button>
            </div>
            """
        else:
            button = ""

        titleH = ""
        if title != "":
            titleH = f"""<h2>{title}</h2>"""

        html = f"""
        <div class='mt-2 relative flex flex-col min-w-[200px]'>
            <div class="w-full flex justify-center px-8 pb-4">
                <img
                src="images/guideplay-dark-logo.png"
                alt="Guide Play Logo"
                class="h-[70px] w-auto"
                />
            </div>
            {spinnerContent}
            {titleH}
            <h3>{sutitle}</h3> 
            <div class="w-full items-center justify-center">
                <p class="w-full text-center text-white">{message}</p>
            </div>
            {button}
        </div>
        """
        # minify html
        html = html.replace("\n", "")
        # remove double spaces
        html = " ".join(html.split())

        return html

    def checkResolutionCompatibility(self, resolution):

        listResolutions, passed = getVideoModes(resolution)
        print("CHECKING RESOLUTION COMPATIBILITY",
              resolution, listResolutions, passed)
        return passed

    def bootUp(self):

        self.machineResolution = get_screen_resolution_methods()

        self.processController = GameApp(self.sync_game, self.devMode, self)

        self.set_focus("Guide Play")

        self.checkNarratorTimer()

        self.serverThread = Thread(target=self.startServer, args=(
            False,),  name="serverThread", daemon=True)
        self.serverThread.start()

        self.stateTransfer("devMode", "devMode", self.devMode)

        modalHTML = self.generateModalData("",
                                           "Checking specs", "Please wait...", "None", spinner=True)
        self.stateTransfer("showModal", "showModal", True)
        self.stateTransfer("modalData", "modalData", modalHTML)

        time.sleep(2)

        resultRes = self.checkResolutionCompatibility((1920, 1080))

        print("RESOLUTION_COMPATIBILITY", resultRes)

        if resultRes == False:
            modalHTML = self.generateModalData("",
                                               "Resolution not compatible", "Your device does not support the resolution required to proceed", "Close", "pywebview.api.topbar('close')", True)
            self.stateTransfer("showModal", "showModal", True)
            self.stateTransfer("modalData", "modalData", modalHTML)
            return

        modalHTML = self.generateModalData("",
                                           "Updating configs", "Please wait...", "None", spinner=True)

        self.stateTransfer("showModal", "showModal", True)
        self.stateTransfer("modalData", "modalData", modalHTML)

        time.sleep(2)

        modalHTML = self.generateModalData("",
                                           "Checking Steam", "Please wait...", "None", spinner=True)
        self.stateTransfer("showModal", "showModal", True)
        self.stateTransfer("modalData", "modalData", modalHTML)

        # self.startWS()
        time.sleep(1)

        self.steamControllerThread = Thread(
            target=self.checkSteamPatch, name="checkSteamPatch", daemon=True)
        self.steamControllerThread.start()

        devWindows = []

        if self.devMode == False:
            devWindows = pyautogui.getWindowsWithTitle('DevTools')

            if len(devWindows) > 0:
                print("DEVTOOLS-FOUND", devWindows[0])
                devWindows[0].close()

        print("STARTING BOOTING UP")
        print("BOOTING UP")
        print("BOOTING UP - READING FILES")
        self.read_files('wav', self.wavs, "UI/sounds")
        time.sleep(1)
        print("BOOTING UP - READING DATABASE")
        self.read_database()
        time.sleep(1)
        print("BOOTING UP - TRANSFERING STATE")
        self.updateMenuTab(self.menuItems[self.rootTabIndex])
        time.sleep(1)
        # self.say("Welcome to Guide Play", 0.5)
        self.refresh()
        time.sleep(3)
        self.refresh()
        self.gameStateManagerThread = Thread(
            target=self.gameStateManagerLoop, name="gameStateManagerThread", daemon=True)
        self.gameStateManagerThread.start()

        if self.devMode == True and self.useDevWindow == True:
            dev_uri = os.path.join(App.DIRPATH, "UI", "dev.html")
            self.mywindowDev = windowinfo("debug", self.version, '',
                                          self.devMode, dev_uri, 1280, 720, self.winIcon)
            targetwindowDev = webview.create_window("debug",
                                                    dev_uri, focus=False,
                                                    width=1280, height=720,
                                                    resizable=True,
                                                    on_top=False,
                                                    easy_drag=False,

                                                    background_color="#000000",
                                                    frameless=False, js_api=self.apiDev)

            self.mywindowDev.targetwindow = targetwindowDev
            targetwindowDev.events.loaded += lambda: self.devWindowLoaded(
                "loaded_dev_2")
            time.sleep(3)
            self.devWindowTransfer("datamodel", "datamodel", self.datamodel)

        self.bootDone = True
        self.processController.serverReady = True

        # focus_guideplay()
        self.set_focus("Guide Play")
        # self.processController.cvFullCapture.startCapturePipes(
        #     self.processController.receiveFromCapture, self.processController.devMode)

    def devWindowLoaded(self, motif="loaded_dev_1"):
        print("DEV_WINDOW_LOADED", motif)

    def devUpdateProp(self, pipename, key, value):
        print("DEV_UPDATE_PROP", pipename, key, value)
        self.processController.cvFullCapture.updateProp(pipename, key, value)

    def devWindowTransfer(self, command, key=None, value=None, extras=None):
        if self.useDevWindow != True:
            return
        # self.targetwindowDev.hide()
        if self.mywindowDev is None or self.mywindowDev.targetwindow is None:
            return
        # print("DEV_WINDOW_TRANSFER", command, key, value, extras)

        if command == "binarymap":
            payload = json.dumps(value)
            self.mywindowDev.targetwindow.evaluate_js(
                f"""
                setState('{command}', '{payload}')
                """
            )
            return
        if command == "floorgrid":
            payload = json.dumps(value)
            self.mywindowDev.targetwindow.evaluate_js(
                f"""
                setState('{command}', '{payload}')
                """
            )
            return

        self.mywindowDev.targetwindow.evaluate_js(
            f"""
                setState('{key}', '{value}', '{extras}')
                """
        )

    def refresh(self):
        self.read_files('wav', self.wavs, "UI/sounds")
        self.read_database()
        self.stateTransfer("datamodel")
        self.stateTransfer("tabs")
        self.stateTransfer("menu")
        self.stateTransfer("tabIndex")
        self.stateTransfer("tabIndexSub")
        self.stateTransfer("tabIndexSubItem")
        self.stateTransfer("rootTabIndex")
        self.stateTransfer("menuTab")
        self.stateTransfer("subItemTabIndex")
        self.stateTransfer("wavs")
        self.stateTransfer("services")

    def unlockTest(self):
        self.testLocked = False

    def screenReader(self, text, delay=0.5, tag=""):
        # print("SCREEN READER", text)
        lastGameState = self.processController.getGameState()

        if self.lastScreenRead == text:
            return
        if tag == "address":
            if lastGameState == "gameplay":
                currentItemValue = self.get_subitem(
                    "ScreenReader", "InGameSectorVoice")
                if currentItemValue["value"] == "on":
                    self.say(text, delay)
            return
        if tag == "cardinal":
            currentItemValue = self.get_subitem(
                "ScreenReader", "InGameCompassVoice")
            if currentItemValue["value"] == "on":
                self.say(text, delay)
            return
        if tag == "theremin" or tag == "footeractions" or tag == "submenu" or tag == "topmenu" or tag == "subtopmenu" or tag == "topicons":
            currentItemValue = self.get_subitem(
                "ScreenReader", "InGameScreenReader")
            if currentItemValue["value"] == "on":
                self.say(text, delay)
            return

        self.say(text, delay)

    def checkNecessaryServices(self, service, lastGameState):
        # CV THEREMIN
        if service == "cv-theremin":
            if self.isQuitting == True:
                data.runTheremin = False
                self.toggle_service("cv-theremin", "stop")
                return False
            if data.runTheremin == True:
                if lastGameState != "home" and lastGameState != "ingame-menu":
                    data.runTheremin = False
                    self.toggle_service("cv-theremin", "stop")
                    return False
            # if self.processController is not None and self.processController.lastThereUpdate + 5 < time.time():
            #     data.runTheremin = False
            #     self.toggle_service("cv-theremin", "stop", reason="timeout")
            #     return False
            if lastGameState == "unknown" or lastGameState == "gameplay":
                data.runTheremin = False
                self.toggle_service("cv-theremin", "stop")
            return

        # CV FULL CAPTURE
        if service == "cv-radar":
            if data.runCV == True:
                if self.isQuitting == True:
                    data.runCV = False
                    data.runCVRadar = False
                    self.toggle_service("cv-radar", "stop")
                    return False
                if lastGameState == "home" or lastGameState == "ingame-menu":
                    self.toggle_service("cv-radar", "stop")
                elif lastGameState == "unknown" or lastGameState == "gameplay":
                    self.toggle_service("cv-radar", "start")
                else:
                    self.toggle_service("cv-radar", "stop")
            else:
                data.runCVRadar = False
                self.toggle_service("cv-radar", "stop")
            return

        if service == "cv-fullcapture":
            if self.isQuitting == True:
                data.runCV = False
                data.runCVRadar = False
                self.toggle_service("cv-fullcapture", "stop")
                return False
            if data.runCV == True:
                if lastGameState == "guideplay-ui" and lastGameState == "guideplay-exit":
                    data.runCV = False
            return

    def gameStateManagerLoop(self):
        print("gameStateManagerLoop-starting")
        devWindows = []
        if self.devMode == False:
            devWindows = pyautogui.getWindowsWithTitle('DevTools')

        time.sleep(10)
        print("gameStateManagerLoop-started")

        isLooping = True

        while isLooping:
            # check if current window is Counter Strike 2
            # if not start monitoring
            activeW = get_active_window()
            currentWindow = str(activeW[0])

            isCSOpen = "Counter-Strike 2" in currentWindow
            if self.devMode == False:
                devWindows = pyautogui.getWindowsWithTitle('DevTools')

                if len(devWindows) > 0:
                    # print("DEVTOOLS-FOUND", devWindows[0])
                    devWindows[0].close()

            lastGameState = self.processController.getGameState()

            secondsToRepeat = 3
            if isCSOpen == False:
                # print("********** \ngameStateManagerLoop-isCSOpen-FALSE", isCSOpen)
                # set_active_on_top(None, currentWindow)
                if data.runCV == True:
                    data.runCV = False
                    self.toggle_service("cv-fullcapture", "stop")
                if data.runTheremin == True:
                    data.runTheremin = False
                    self.toggle_service("cv-theremin", "stop")

                # set resolution to original machineResolution
                if self.machineResolution is not None and self.machineResolution != (1920, 1080):
                    currentResolution = get_screen_resolution_methods()
                    if currentResolution != self.machineResolution:
                        on_set_resolution(
                            self.machineResolution[0], self.machineResolution[1])
            else:
                # check if machineResolution is different from 1920, 1080
                # if different set it on_set_resolution(width, height)

                # self.checkNecessaryServices("cv-fullcapture", lastGameState)
                self.checkNecessaryServices("cv-radar", lastGameState)
                self.checkNecessaryServices("cv-theremin", lastGameState)

                if data.runCV == False and self.isQuitting == False:
                    if self.captureDisabled:
                        time.sleep(1)
                        continue
                    if time.time() < self.captureRetryBlockedUntil:
                        time.sleep(1)
                        continue
                    if self.isAdmin is False and self.warnedNonAdminCapture is False:
                        print(
                            "CAPTURE_WARNING current process is not elevated; if Steam or Counter-Strike 2 runs as admin, graphics capture may fail.")
                        self.warnedNonAdminCapture = True
                    print("GAME WINDOW DETECTED", currentWindow)
                    if self.devMode == False and self.machineResolution is not None and self.machineResolution != (1920, 1080):
                        try:
                            print("FORCING_RESOLUTION",
                                  self.machineResolution, (1920, 1080))
                            on_set_resolution(1920, 1080)
                            time.sleep(2)
                            self.toggle_service("cv-fullcapture", "start")
                        except Exception as e:
                            print("ERROR SETTING RESOLUTION", e)
                    else:

                        self.toggle_service("cv-fullcapture", "start")

                    # self.processController.startService("cv-theremin")
                # print("********** \ngameStateManagerLoop-isCSOpen-TRUE",
                #       isCSOpen, lastGameState)

            time.sleep(3)

    def sync_game(self, key, value, extras=None):
        # print("SYNC GAME", key, value)

        if self.processController is None:
            return

        lastGameState = self.processController.getGameState()

        # getters
        if key == "/getconfig":
            return self.get_subitem(value, extras)

        # setters
        if lastGameState != "guideplay-exit":

            # if key == "/screenreader/topmenu":
            if "/screenreader/" in key:
                tags = key.split("/")
                tag = tags[2]
                self.screenReader(value, 0.5, tag)

            if key == "/roundstate":
                self.stateTransfer("roundstate", key, value, extras)

            if key == "/aim_damage":
                self.stateTransfer("aim_damage", key, value)

            if key == "/aimplus":
                self.stateTransfer("aimplus", key, value)

            if key == "/obstacles":
                self.stateTransfer("obstacles", key, value)

            if key == "/trackeds":
                # self.sync_ultra(key, value)
                self.stateTransfer("trackeds", key, value)

            if key == "/binarymap":
                # self.sync_ultra(key, value)
                # self.stateTransfer("binarymap", key, value)
                self.devWindowTransfer("binarymap", key, value)

            if key == "/floorgrid":
                # self.sync_ultra(key, value)
                # self.stateTransfer("floorgrid", key, value)
                self.devWindowTransfer("floorgrid", key, value)

            if key == "/aim":
                # self.sync_ultra("", key, value)
                self.stateTransfer("aim", key, value)
            if key == "/address":
                # self.sync_ultra(key, value)
                self.steamController.focus_cs2()
                if value != self.lastScreenAddress:
                    self.lastScreenAddress = value
                    self.screenReader(value, 0.5, "address")
            if key == "/cardinal":
                # self.sync_ultra(key, value)
                self.screenReader(value, 0.5, "cardinal")

            if key == "/gamestate":
                # self.sync_ultra(key, value)

                # self.screenReader(value, 0.5, "gamestate")
                if value == "home" or value == "ingame-menu":
                    self.toggle_service("cv-theremin", "start")
                else:
                    self.toggle_service("cv-theremin", "stop")

                extras['bestTargets'] = self.processController.bestTargets

                self.stateTransfer("gamestate", key, value, extras)

    # def sync_ultra(self, key, value):
    #     # print("SYNC ULTRA", key, value)

    #     self.messsageQ.append(value)
    #     # slice 3 items
    #     if len(self.messsageQ) > 3:
    #         self.messsageQ = self.messsageQ[-3:]
    #     # iterate and send
    #     for i in self.messsageQ:
    #         # print("testRadarItem\n", i)
    #         # client.send_message('/trackeds', json.dumps(i))

    #         if cliController is not None:
    #             # print("PIPING =>>> \n", i)
    #             # cliController.send('detection '+str(i)+'')
    #             parsed = i
    #             if parsed["class"] == "friend":
    #                 update_friend(parsed)
    #             elif parsed["class"] == "enemy":
    #                 update_enemy(parsed)
    #             elif parsed["class"] == "aim":
    #                 sndString = update_aim(parsed)
    #                 if sndString is not None:
    #                     setState('sndString_aim', sndString)
    #         if self.useOSC:
    #             client.send_message('/test-trackeds', json.dumps(i))

    def toggle_service(self, key, value, withTimeoutOf=0, reason=""):
        # print("TOGGLE SERVICE", key, value, reason)

        if key == "cv-theremin":
            if value == "start":
                self.processController.startService("cv-theremin")
            elif value == "stop":
                self.processController.stopService("cv-theremin")

        if key == "cv-radar":
            if value == "start":
                data.runCVRadar = True
            elif value == "stop":
                data.runCVRadar = False

        if key == "cv-fullcapture":
            if value == "start":
                self.processController.startService("cv-fullcapture")

                if withTimeoutOf > 0:
                    # stop after withTimeoutOf
                    print("TOGGLE SERVICE TIMEOUT", withTimeoutOf, "seconds")
                    Timer(withTimeoutOf, lambda: self.toggle_service(
                        "cv-fullcapture", "stop")).start()

            elif value == "stop":
                self.processController.stopService("cv-fullcapture")

        time.sleep(0.3)
        self.stateTransfer("services")

    def sync_state(self, key, value):
        # receive changes from webview UI
        global cliController
        global testTimer

        useLock = True

        # print("SYNC STATE", key)

        if key == 'askSay':
            self.say(value, 0.5, tag="ui")
            return

        if key == 'bootup':
            print("SYNC BOOTING UP")
            self.bootUp()
            return

        if key == 'refresh':
            print("REFRESHING")
            self.refresh()

        if key == 'theremin':
            if value == 'start':
                self.toggle_service("cv-theremin", "start")
            elif value == 'stop':
                self.toggle_service("cv-theremin", "stop")

        if key == 'testRadarItem':

            if useLock:
                if self.testLocked:
                    # print("TEST LOCKED")
                    return
                self.testLocked = True

                # unlock after 0.3 second
                if testTimer is not None:
                    testTimer.cancel()
                testTimer = Timer(0.1, lambda: self.unlockTest())
                testTimer.start()

                # self.sync_ultra(key, value)

        if key == "subItemTabIndex":
            if value == "next":
                self.cycleTabIndex('next')
            elif value == "prev":
                self.cycleTabIndex('prev')
            elif value == "reset":
                print("RESETING_TABS")
                self.tabIndexSub = 0
                self.tabIndex = 0
                self.rootIndex = 0
                self.hightLightCurrentTab()
        if key == "tabIndex":
            self.setTabIndex(value)

        if key == "rootTabIndex":
            self.rootTabIndex = value
        if key == "menuTab":
            self.updateMenuTab(value)
        # print("SYNC STATE FULL PAYLOAD", key,  json.dumps(value, indent=4))

    def stateTransfer(self, command, key=None, value=None, extras=None):

        isValid = True
        lastGameState = ""
        motif = "0"

        if self.processController is None:
            isValid = False
            motif = "1"

        if self.isQuitting == True:
            isValid = False
            motif = "2"

        if isValid == True:
            lastGameState = self.processController.getGameState()
            if lastGameState == "guideplay-exit":
                isValid = False
                motif = "3"

        if isValid == False and value != "guideplay-exit":
            print("STATE TRANSFER BLOCKED", motif, command, key, value)
            return

        # send changes to webview UI
        # print("STATE TRASNFERING", lastGameState, command)
        isRetry = False

        if self.mywindow is None:
            isRetry = True
        if self.mywindow is not None and self.mywindow.targetwindow is None:
            isRetry = True

        if isRetry == True:
            print("STATE TRANSFER FAILED-NOT_READY")
            Timer(2, lambda: self.stateTransfer(
                command, key, value)).start()
            print("STATE TRANSFER CALLING 2 secs",
                  command, "FAILED-NOT_READY")
            return

        if self.debugStateFlow and command in ['devMode', 'showModal', 'modalData', 'menu', 'tabIndex', 'services', 'gamestate', 'roundstate', 'datamodel']:
            valuePreview = value
            if isinstance(valuePreview, str) and len(valuePreview) > 120:
                valuePreview = valuePreview[:120] + "..."
            sig = f"{command}|{key}|{valuePreview}|{lastGameState}"
            now = time.time()
            lastSig = self._lastDebugSignature.get(command, "")
            lastTs = self._lastDebugTime.get(command, 0)
            throttle = 0
            if command == "services":
                throttle = 5
            if sig != lastSig or (now - lastTs) >= throttle:
                print(
                    f"STATE_DEBUG command={command} key={key} value={valuePreview} lastGameState={lastGameState}")
                self._lastDebugSignature[command] = sig
                self._lastDebugTime[command] = now

        if command == 'devMode':
            setState('devMode', value)
            return

        if command == 'showModal':
            # return
            if value == True:
                setState('showModal', value)
            else:
                setState('hideModal', value)
            return

        if command == 'modalData':
            # return
            # print("MODAL DATA 2", value)
            self.api.modaldata(value)
            return

        if command == 'menu':
            setState('currentTab', self.currentMenu)
            setState('tabs', json.dumps(self.menuItems))
            return
        if command == 'tabIndex':
            setState('tabIndexSub', int(self.tabIndex))
            setState('tabIndexSubItem', int(self.tabIndexSub))
            setState('tabRootIndex', int(self.rootIndex))
            return
        if command == 'state':
            setState(key, value)
            return
        if command == 'wavs':
            setState('wavs', self.wavs)
            return
        if command == 'services':
            setStateJSON({
                "cv-fullcapture": data.runCV,
                "cv-radar": data.runCVRadar,
                "cv-damage": data.runCVRadar,
                "cv-aim": data.runCVRadar,
                "cv-cardinal": data.runCardinal,
                "cv-theremin": data.runTheremin,
            }, "serviceStates")
            return
        if command == 'trackeds':
            print("[STATE_DEBUG] trackeds count:", len(value) if value else 0, "gameState:", lastGameState)
            if lastGameState != "home" and lastGameState != "ingame-menu":
                setStateJSON(value, 'trackeds')

            # self.sendWebSocket('test')
            return
        if command == 'obstacles':
            # print("STATETRANSFER___OBSTACLES", value)
            if lastGameState != "home" and lastGameState != "ingame-menu":
                setStateJSON(value, 'obstacles')
            return
        if command == 'aim_damage':
            # print("STATETRANSFER___", value)
            if lastGameState != "home" and lastGameState != "ingame-menu":
                setStateJSON(value, 'aim_damage')
        if command == 'aimplus':
            # print("STATETRANSFER___", value)
            if lastGameState != "home" and lastGameState != "ingame-menu":
                setStateJSON(value, 'aimplus')
        if command == 'aim':
            # print("STATETRANSFER___", value)
            if lastGameState != "home" and lastGameState != "ingame-menu":
                setStateJSON(value, 'aim')
            return
        if command == 'gamestate':
            # print("STATETRANSFER___gamestate", value, extras)
            if value != "guideplay-exit":
                setStateJSON({
                    "gamestate": value,
                    "extras": extras
                }, 'gamestate')
            return

        if command == 'roundstate':
            # print("STATETRANSFER___roundstate", value, extras)
            if value != "guideplay-exit":
                setStateJSON({
                    "roundstate": value,
                    "extras": extras
                }, 'roundstate')
            return

        if command == 'datamodel':
            setStateJSON(self.datamodel, "datamodel")
            setStateJSON(self.wavs, "wavs")
            setStateJSON(self.menuItems, "tabs")

    async def send_receive_message(self, text="hello", uri='ws://localhost:8899'):
        async with websockets.connect(uri) as websocket:
            try:
                await websocket.send(text)
                reply = await websocket.recv()
                print(f"WEBSOCKETS______ The reply is: '{reply}'")
            except Exception as e:
                print("WEBSOCKETS______ ERROR", e)

    def sendWebSocket(self, payload):
        msg = json.dumps(payload)
        client = threading.Thread(
            target=self.senderWS, args=(msg,), daemon=True)
        client.start()
        client.join()

    def senderWS(self, msg):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.send_receive_message(msg))
        loop.close()

    def startWS(self):
        async def receiverWS(websocket, path):
            async for data in websocket:
                try:
                    print(f"WEBSOCKETS______ Received: '{data}'")
                    await websocket.send(""+str(data)+" returning!")
                except Exception as e:
                    print("WEBSOCKETS______ ERROR", e)

        def between_callback():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            ws_server = websockets.serve(receiverWS, 'localhost', 8899)

            loop.run_until_complete(ws_server)
            loop.run_forever()  # this is missing
            loop.close()

        server = threading.Thread(target=between_callback, daemon=True)
        server.start()
        client = threading.Thread(
            target=self.senderWS, args=("hello sending 456",), daemon=True)
        client.start()
        client.join()

    def startServer(self, forceDebug=False):

        if forceDebug:
            self.devMode = True

        def start_script(self):
            global cliController

            # prefix ../osc_tts_server/server.py
            if self.devMode:

                data.devMode = True
                data.monitorSelected = 1

                daemonPath = os.path.abspath(
                    os.path.join(App.DIRPATH, "..", "osc_tts_server", "server.py"))
                pythonInterpreter = sys.executable
                uiPath = os.path.join(App.DIRPATH, "UI")
                finalCOMMAND = f"\"{pythonInterpreter}\" \"{daemonPath}\" --path \"{uiPath}\" --port {data.port_server} --port_app {data.port_app}"

                print("start_script-dev-mode-FINAL COMMAND\n", finalCOMMAND)
            else:
                daemonPath = os.path.join(
                    App.DIRPATH, "server", "guide-play-services-cli.exe")
                uiPath = os.path.join(App.DIRPATH, "UI")
                finalCOMMAND = f"\"{daemonPath}\" --path \"{uiPath}\" --port {data.port_server} --port_app {data.port_app}"

                print("start_script-prod-mode-FINAL COMMAND\n", finalCOMMAND)
            try:
                # Make sure 'python' command is available
                print("start_script-TRYING-START\n\n", finalCOMMAND, "\n\n")
                if forceDebug is False:

                    # TO-DO: check if process is running
                    # if not running start it

                    if cliController is None:
                        print("start_script-cliController-start", finalCOMMAND)

                        cliController = SubStarter(finalCOMMAND, None)
                        cliController.start()
                        print("start_script-cliController-status", cliController)

                    elif cliController is not None:
                        print("start_script-cliController-running?", cliController)
                        # TO-DO: check if process is running
                        # if not running start it
                else:
                    print("start_script-START-MANNUALY", finalCOMMAND)
                self.crashTimes = 0

            except Exception as e:
                # Script crashed, lets restart it!
                # get exception and handle it
                # e = sys.exc_info()[0]
                handle_crash(cliController, finalCOMMAND, e)

        def handle_crash(e, cmd, exc):

            self.crashTimes += 1
            if e is not None:
                print("CRASHED", e.stdout, e.stderr)
                print("CRASHED_exc", exc)
            print("CRASHED_RESTARTING", self.crashTimes)
            print("CRASHED_CMD", cmd)

            self.lastKeepAlive = -1
            self.lastKeepAliveMSG = -1
            self.serverIsAlive = False

        def checkLiveness():
            while True:
                diff = time.time() - self.lastKeepAlive
                diffMSG = time.time() - self.lastKeepAliveMSG
                sleepSecs = 1

                if self.isQuitting:
                    print("SERVER IS QUITTING", diff)
                    print("SERVER IS QUITTING DIFF", diff)
                    # self.quit_root()
                    # if cliController is not None:
                    #     cliController.send('quit')
                    break

                # print("CHECK LIVENESS", diff,
                #       self.lastKeepAlive, self.serverIsAlive)
                if cliController is None and diff > 5:
                    print("SERVER DEAD", diff)
                    print("SERVER RECONNECTING", diff)
                    self.lastKeepAlive = -1
                    self.serverIsAlive = False
                    sleepSecs = 5
                    if self.crashTimes > 5:
                        print("SERVER CRASHED", diff)
                        print("SERVER CRASHED RESTARTING", diff)
                        self.crashTimes = 0
                        # exit app
                        self.quit_root()
                    else:
                        start_script(self)
                else:
                    # SUBPROCESS IS RUNNING
                    self.lastKeepAlive = time.time()

                    if self.isQuitting:
                        print("SERVER IS QUITTING", diff)
                        break

                    if diffMSG > 20:
                        print("SERVER IS ALIVE, ASKING FOR SYNC", diff)
                        cliController.send('startMessenger')
                        client.send_message('/asksync', "sync")

                    if self.lastKeepAliveMSG < 0:
                        print("STARTING MESSENGER 1st time")
                        cliController.send('startMessenger')

                    sleepSecs = 1

                time.sleep(sleepSecs)

        def keepalive(unused_addr, args, say):
            # print("\n\n\n\n__SYNC___server_alive", say)
            self.lastKeepAlive = time.time()
            self.lastKeepAliveMSG = time.time()
            self.serverIsAlive = True
            # diff = time.time() - self.lastKeepAlive

        def asksync(unused_addr, args, say):
            self.lastKeepAlive = time.time()
            self.lastKeepAliveMSG = time.time()
            self.serverIsAlive = True
            self.update_sfx()
            return

        dispatcher = Dispatcher()
        dispatcher.map("/keepalive", keepalive, "Keep Alive")
        dispatcher.map("/asksync", asksync, "Ask Sync")

        server = osc_server.ThreadingOSCUDPServer(
            ("127.0.0.1", data.port_app), dispatcher)
        print("serving-on {}".format(server.server_address))

        checkLivenessT = Thread(target=checkLiveness, args=(),
                                name="checkLiveness", daemon=True)
        checkLivenessT.start()

        server.serve_forever()

    def updateMenuTab(self, value):

        if self.currentMenu == value:
            return
        self.currentMenu = value
        self.say(value, 0.5, tag="ui")

        self.stateTransfer("menu")

    def clearLastSay(self):
        self.lastSay = ""

    def checkNarratorWrapper(self):
        if data.runCV == False:
            self.narratorIsOn = checkNarrator()[0]
        if self.devMode == True:
            self.narratorIsOn = checkNarrator()[0]
        self.checkNarratorTimer()

    def checkNarratorTimer(self):
        if self.narratorTimer is not None:
            self.narratorTimer.cancel()
        self.narratorTimer = Timer(
            5, lambda: self.checkNarratorWrapper())
        self.narratorTimer.start()
        print("NARRATOR_TIMER_STARTED", self.narratorTimer)

    def say(self, say, delay=2, reset=0, tag=""):

        if tag == "ui":
            if self.narratorIsOn == True:
                print("NARRATOR_IS_ON",  self.narratorIsOn)
                return

        if self.isQuitting:
            return
        # print("SAY-asking", say, delay)
        if say == "AUDIO SETTINGS" and self.lastSay == "welcome to guide play":
            say = "welcome to guide play.  please wait a moment."
        if self.lastSay == say:
            # print("SAY-asking-ALREADY", say, delay)
            return
        if self.sayTime is not None:
            self.sayTime.cancel()
        self.lastSay = say
        self.sayTime = Timer(delay, lambda: self.sendSay())
        # print("SAY-asking-timer", self.lastSay, self.sayTime)
        self.sayTime.start()
        # if reset > 0 clear last say after reset seconds
        if reset > 0:
            Timer(reset, lambda: self.clearLastSay()).start()

    def sayAndSet(self, say, topic, value, delay=2, tag=""):
        self.sayTime.cancel()
        self.lastSay = value
        self.sayTime = Timer(delay, lambda: self.sendSay(topic, say, tag=tag))
        self.sayTime.start()

    def treatSAY(self, say):
        # remove line breaks and returns
        # convert to string
        say = str(say)
        say = say.replace("\n", ".  ")
        say = say.replace("\r", "")
        say = say.replace(".wav", "")
        say = say.replace("  ", " ")

        return say

    def sendSay(self, topic="/saynow", nextSay=None, tag=""):
        print("SEND SAY", self.lastSay)
        if nextSay is not None:
            print("SEND SAY NEXT", nextSay)
        if cliController is not None:
            if nextSay is None:
                cliController.send('say '+self.treatSAY(str(self.lastSay))+'')
        if client is not None:
            print("SEND SAY COMMAND", topic, self.lastSay)
            print("SEND SAY COMMAND NEXT-0", nextSay)
            client.send_message(topic, self.lastSay)
            if nextSay is not None:
                print("SEND SAY COMMAND NEXT-1", nextSay)
                self.say(nextSay, 0, tag=tag)
        # self.lastSay = ""

    def checkTabIndex(self, text):
        nextTitle = self.datamodel[self.tabIndex]["name"]
        if text == nextTitle:
            return True
        else:
            for i in self.datamodel[self.tabIndex]["subitems"]:
                if i["tabIndex"] == self.tabIndexSub:
                    nextSubTitle = i["title"]
                    if text == nextSubTitle:
                        return True

            return False

    def cycleTabIndex(self, dir):

        print("CYCLE TAB INDEX", dir, self.currentMenu)

        if self.currentMenu == "VIDEO SETUP":
            return

        if self.currentMenu == "SPATIAL TESTS":
            return

        if self.currentMenu == "ABOUT":
            return

        # count all items self.datamodel and subitems
        totalItems = 0
        for i in self.datamodel:
            totalItems += 1
            for j in i["subitems"]:
                totalItems += 1

        if dir == 'next':
            if self.rootIndex+1 < totalItems+1:
                self.rootIndex += 1
            else:
                self.rootIndex = 1

        elif dir == 'prev':
            if self.rootIndex > 1:
                self.rootIndex -= 1
            else:
                self.rootIndex = totalItems

        self.hightLightCurrentTab()

    def cycleTabIndexLegacy(self, dir):

        if self.currentMenu == "VIDEO SETUP":
            return

        if self.currentMenu == "ABOUT":

            return

        if self.currentMenu == "SPATIAL TESTS":
            return

        if self.tabIndexSub == -3:
            nextTitle = self.datamodel[self.tabIndex]["name"]
            nextDesc = self.datamodel[self.tabIndex]["desc"]

            print("TAB INDEX NEGATIVE_TITLE",
                  nextTitle, self.tabIndexSub)

            self.say(nextTitle, 0.5, tag="ui")

            self.tabIndexSub = -2
        elif self.tabIndexSub == -2:
            nextTitle = self.datamodel[self.tabIndex]["name"]
            nextDesc = self.datamodel[self.tabIndex]["desc"]

            print("TAB INDEX NEGATIVE_TITLE",
                  nextTitle, self.tabIndexSub)

            self.say(nextDesc, 0.5, tag="ui")

            self.tabIndexSub = -1

        # prev states

        elif self.tabIndexSub == -5:
            nextTitle = self.datamodel[self.tabIndex]["name"]
            nextDesc = self.datamodel[self.tabIndex]["desc"]

            print("TAB INDEX NEGATIVE_REVERSE_TITLE",
                  nextTitle, self.tabIndexSub)

            self.say(nextTitle, 0.5, tag="ui")

            self.tabIndexSub = -4

        elif self.tabIndexSub == -4:
            nextTitle = self.datamodel[self.tabIndex]["name"]
            nextDesc = self.datamodel[self.tabIndex]["desc"]

            print("TAB INDEX NEGATIVE_REVERSE_DESC",
                  nextTitle, self.tabIndexSub)

            self.say(nextDesc, 0.5, tag="ui")

            self.tabIndexSub = len(
                self.datamodel[self.tabIndex]["subitems"])

        else:

            if dir == 'next':

                for i in self.datamodel:
                    if i["tabIndex"] == self.tabIndex:
                        # iterate to i subitems
                        if self.tabIndexSub+1 < len(i["subitems"]):
                            self.tabIndexSub += 1
                            # i["subitems"][self.tabIndexSub]["value"].focus_set()
                            break
                        else:

                            self.tabIndexSub = -3

                            if self.tabIndex+1 < len(self.datamodel):
                                self.tabIndex += 1
                            else:
                                self.tabIndex = 0
                            break

            elif dir == 'prev':

                for i in self.datamodel:

                    if i["tabIndex"] == self.tabIndex:
                        # iterate to i subitems
                        if self.tabIndexSub > 0:

                            self.tabIndexSub -= 1
                            # i["subitems"][self.tabIndexSub]["value"].focus_set()
                            break
                        else:

                            if self.tabIndex > 0:
                                self.tabIndex -= 1
                                # self.tabIndexSub = len(
                                #     self.datamodel[self.tabIndex]["subitems"])
                                self.tabIndexSub = -5
                            else:
                                self.tabIndex = len(self.datamodel) - 1
                                # self.tabIndexSub = len(
                                #     self.datamodel[self.tabIndex]["subitems"])
                                self.tabIndexSub = -5
                            break

            print("TAB INDEX IDS", dir, self.tabIndex, self.tabIndexSub)

            nextTitle = self.datamodel[self.tabIndex]["name"]
            nextDesc = self.datamodel[self.tabIndex]["desc"]

            for i in self.datamodel[self.tabIndex]["subitems"]:
                if i["tabIndex"] == self.tabIndexSub:
                    nextSubTitle = i["title"]
                    # i["value"].focus_set()
                    self.say(nextSubTitle, 0.5, tag="ui")
                    print("TAB INDEX TITLE", nextTitle, nextSubTitle)
                    break

        self.hightLightCurrentTab()

    def setTabIndex(self, newIndex):
        print("SET TAB INDEX", newIndex)

        rootIndex = 0
        for i in self.datamodel:
            if i["rootIndex"] == newIndex:
                rootIndex = i["rootIndex"]
            for j in i["subitems"]:
                if j["rootIndex"] == newIndex:
                    rootIndex = j["rootIndex"]

        self.rootIndex = rootIndex

        self.hightLightCurrentTab()

    def keyboardEvent(self, event):
        print("KEYBOARD CHANGES", event.keysym)

        # if event.keysym == "Escape":
        #     self.quit_root()
        if event.keysym == "Tab":
            self.cycleTabIndex('next')
        elif event.keysym == "Shift_L":
            self.cycleTabIndex('prev')

        if self.currentSubItem is not None:

            currentItemValue = self.get_subitem(
                self.currentSubItem["parentId"], self.currentSubItem["id"])

            currentVal = currentItemValue["value"]

            if event.keysym == "Up" or event.keysym == "Right":
                if self.currentSubItem["type"] == "spin":
                    newValue = int(currentVal) + 1
                    self.modify_subitem(self.currentSubItem["parentId"], self.currentSubItem["id"],
                                        self.currentSubItem["title"], newValue)
                    self.update_widget_value(self.currentSubItem["parentId"], self.currentSubItem["id"],
                                             self.currentSubItem["title"], newValue)
                elif self.currentSubItem["type"] == "switch":
                    self.modify_subitem(self.currentSubItem["parentId"], self.currentSubItem["id"],
                                        self.currentSubItem["title"], "on")
                    self.update_widget_value(self.currentSubItem["parentId"], self.currentSubItem["id"],
                                             self.currentSubItem["title"], "on")
                elif self.currentSubItem["type"] == "rate" or self.currentSubItem["type"] == "slider":
                    newValue = currentVal + 1
                    self.modify_subitem(self.currentSubItem["parentId"], self.currentSubItem["id"],
                                        self.currentSubItem["title"], newValue)
                    self.update_widget_value(self.currentSubItem["parentId"], self.currentSubItem["id"],
                                             self.currentSubItem["title"], newValue)
                elif self.currentSubItem["type"] == "combo":
                    # get current index
                    currentIndex = self.wavs.index(currentVal)
                    if currentIndex+1 < len(self.wavs):
                        newValue = self.wavs[currentIndex+1]
                        self.modify_subitem(self.currentSubItem["parentId"], self.currentSubItem["id"],
                                            self.currentSubItem["title"], newValue)
                        self.update_widget_value(self.currentSubItem["parentId"], self.currentSubItem["id"],
                                                 self.currentSubItem["title"], newValue)

            elif event.keysym == "Down" or event.keysym == "Left":
                if self.currentSubItem["type"] == "spin":
                    newValue = int(currentVal) - 1
                    self.modify_subitem(self.currentSubItem["parentId"], self.currentSubItem["id"],
                                        self.currentSubItem["title"], newValue)
                    self.update_widget_value(self.currentSubItem["parentId"], self.currentSubItem["id"],
                                             self.currentSubItem["title"], newValue)
                elif self.currentSubItem["type"] == "switch":
                    self.modify_subitem(self.currentSubItem["parentId"], self.currentSubItem["id"],
                                        self.currentSubItem["title"], "off")
                    self.update_widget_value(self.currentSubItem["parentId"], self.currentSubItem["id"],
                                             self.currentSubItem["title"], "off")
                elif self.currentSubItem["type"] == "slider" or self.currentSubItem["type"] == "rate":
                    newValue = currentVal - 1
                    self.modify_subitem(self.currentSubItem["parentId"], self.currentSubItem["id"],
                                        self.currentSubItem["title"], newValue)
                    self.update_widget_value(self.currentSubItem["parentId"], self.currentSubItem["id"],
                                             self.currentSubItem["title"], newValue)
                elif self.currentSubItem["type"] == "combo":
                    # get current index
                    currentIndex = self.wavs.index(currentVal)
                    if currentIndex > 0:
                        newValue = self.wavs[currentIndex-1]
                        self.modify_subitem(self.currentSubItem["parentId"], self.currentSubItem["id"],
                                            self.currentSubItem["title"], newValue)
                        self.update_widget_value(self.currentSubItem["parentId"], self.currentSubItem["id"],
                                                 self.currentSubItem["title"], newValue)

    def bindKeys(self):
        # self.bind('<Escape>', self.quit_root)
        self.bind('<Control-Tab>', lambda e: self.cycleTabIndex('next'))
        self.bind('<Control-Shift-Tab>', lambda e: self.cycleTabIndex('prev'))

        # keyboardEvent
        self.bind('<Key>', self.keyboardEvent)

    def createSpacer(self, frame):
        model = {}

        return model

    def add_item(self, name, desc, subitems, ref, id, tabIndex):
        """ add new package to the list """
        # print("--ITEMID____", id)

        titleRef = self.createTitle(ref, name)
        descRef = self.creteDescription(ref, name, desc, id)

        subItemRefs = []
        for i in subitems:
            itemRef = self.createSubItem(ref, i["title"], i, id, tabIndex)
            subItemRefs.append(itemRef)

        spacerRef = self.createSpacer(ref)

        self.currentItems.append({
            "id": id,
            "tabIndex": tabIndex,
            "title": titleRef,
            "desc": descRef,
            "subitems": subItemRefs,
            "spacer": spacerRef
        })

        """ remove all packages from the list """

        destroyList = []
        for i in self.currentItems:
            # print("** removing", i)
            # print("\n\n** removing start \n\n", i["title"])
            # # iterate i keys
            # print("\n\n** removing keys \n\n", i.keys())
            for x in i.keys():
                if x != "id":
                    # i[x].pack_forget()
                    # self.currentItems[i][x].pack_forget()
                    # print("**** removing key", x)
                    # print("**** getting", i[x])
                    # check if its dict
                    if isinstance(i[x], dict):
                        keys = i[x].keys()
                        if keys is not None:
                            for y in keys:
                                # print("**** removing sub key", y)
                                i[x][y].pack_forget()
                                i[x][y].destroy()
                    # else:
                    #     print("instance is not dict", isinstance(i[x], list))

            for s in i["subitems"]:
                # iterate s keys
                for y in s.keys():
                    # print("****start removing sub key", y)

                    if y == "frame":
                        for label in s[y].grid_slaves():
                            label.grid_forget()
                        s[y].pack_forget()
                        destroyList.append(s[y])
                        # s[y].destroy()
                        # print("**** removing sub key", s[y])
                    if y != "id" and y != "frame" and y != "tabIndex" and y != "title" and y != "type":
                        s[y].pack_forget()
                        s[y].destroy()
                        # print("**** removing sub key", s[y])

        # refresh self.iframe

        # self.iframe.update()
        # self.after(50, self.update)

        self.currentItems.clear()

        for i in destroyList:
            i.destroy()

    def hightLightCurrentTab(self):
        print("HIGHLIGHTING TABS", self.tabIndex)

        for i in self.datamodel:

            if i["rootIndex"] == self.rootIndex:
                nextTitle = i["name"]
                nextDesc = i["desc"]
                self.say(nextTitle, 0.5, tag="ui")
                print("TAB INDEX TITLE", nextTitle)
                self.tabIndexSub = 0
                self.tabIndex = i["tabIndex"]
                break

            for j in i["subitems"]:
                if j["rootIndex"] == self.rootIndex:
                    nextSubTitle = j["title"]
                    # i["value"].focus_set()
                    self.say(nextSubTitle, 0.5, tag="ui")
                    print("TAB INDEX SUBTITLE", nextSubTitle)
                    self.tabIndexSub = j["tabIndex"]
                    break

        self.stateTransfer("tabIndex")

    def creteDescription(self, frame, name, desc, id):
        return
        print("CREATE DESCRIPTION", name, desc, id)

    def createTitle(self, frame, title):
        return
        print("CREATE TITLE", title)

    def createSubItem(self, frame, name, item, parentId, parentTabIndex):
        model = {
            "id": ""+str(parentId)+"-"+str(item["id"])+"",
            "tabIndex": item["tabIndex"],
            "type": item["type"],
            "title": name,
        }

        return model

    def createFrame(self, name, icon):
        return
        print("CREATE FRAME", name, icon)

    def quit_window(self, icon, item):
        print("QUIT WINDOW", icon, item)

    def getSubProcess(self):
        global cliController
        # print("GETTING SUBPROCESS", cliController)
        return cliController

    def cliKiller(self, iteration=0, callback=None):
        global cliController
        if cliController is not None:
            cliController.send('quit')
            time.sleep(1)

            # time.sleep(1)
            if cliController is not None:
                poll_result = cliController.poll()
                if poll_result is None:
                    print("The subprocess is still running.", iteration)
                    cliController.terminate()
                    time.sleep(1)
                    self.cliKiller(iteration+1, callback)
                else:
                    print(
                        f"The subprocess has completed with exit code {poll_result}.")
                    callback()
            else:
                print("The subprocess is not running. 1")
                callback()
        else:
            print("The subprocess is not running. 2")
            callback()

    def quit_tray(self):
        self.api.quit()
        self.quit_root()

    def quit_root(self, key=None, iteration=0):

        print("QUIT ROOT", key, iteration)

        self.isQuitting = True

        if self.processController is not None:
            self.processController.setGameState("guideplay-exit")
            self.processController.stopService("cv-fullcapture")
            self.processController.stopService("cv-theremin")
            self.processController.isQuitting = True

        data.runCV = False
        data.runTheremin = False
        data.runCVRadar = False

        print("QUIT ROOT WAITING 5 SECONDS")
        time.sleep(5)

        cliController = self.getSubProcess()

        print("TERMINATING_START", cliController)

        # clearUltra()
        # time.sleep(1)

        if cliController is None:
            if client is not None:
                print("SENDING EXIT")
                # self.say("Exiting", 0.5)
                client.send_message("/exit", 1)
                time.sleep(3)
                # self.trayIcon.stop()
                # time.sleep(3)
                # os._exit(0)
                self.cliKiller(iteration+1, self.quit_now)
            else:
                self.quit_now()
        else:
            try:
                cliController.send('quit')
                time.sleep(1)
                self.cliKiller(iteration+1, self.quit_now)
                print("TERMINATING", cliController)
                time.sleep(1)
            except Exception as e:
                print("TERMINATING_ERROR", cliController, e)
                time.sleep(1)
                self.quit_root("retry", iteration+1)

    def quit_now(self):
        # self.destroy()
        print("QUIT NOW WINDOW")
        self.trayIcon.stop()
        time.sleep(0.3)
        os._exit(0)

    def set_focus(self, event):
        if self.mywindow is not None:
            self.mywindow.targetwindow.restore()

    def show_window(self, icon, item):
        self.set_focus(item)

        t = Timer(1, lambda: setState('currentTab', item))
        t.start()

        print("SHOW WINDOW", icon, item)

    def update_database(self):
        """ update the database containing package data """
        global documentsPath
        dbPath = os.path.join(documentsPath, "guideplay_config.json")

        self.set_datamodel(self.data)
        try:
            with open(dbPath, "w") as f:
                json.dump(self.data, f, indent=4)
        except:
            print("ERROR UPDATING DATABASE")
            # try again in 1 second
            t = Timer(1, lambda: self.update_database())
            t.start()

    def modify_item(self, id, name, desc, subitems):
        """ modify an existing package """
        self.data[id]["desc"] = name
        self.data[id]["full_desc"] = desc
        self.data[id]["subItems"] = subitems
        self.update_database()

    def modify_subitem(self, id, subitem_id, name, value):
        """ modify an existing package """
        # find subitem with subitem_id id and modify it
        print("MODIFY SUBITEM", id, subitem_id, name, value)
        # iterate datamodel and diff new value
        for i in self.datamodel:
            if i["id"] == id:
                for j in i["subitems"]:
                    if j["id"] == subitem_id:
                        if j["value"] != value:
                            if j["type"] == "switch":
                                if value == "on":
                                    self.say("Switch on", 0.5, 0.8, tag="ui")
                                else:
                                    self.say("Switch off", 0.5, 0.8, tag="ui")
                            elif j["type"] == "rate" or j["type"] == "slider":
                                currentValue = int(j["value"])
                                if value == "plus":
                                    if currentValue < 100:
                                        value = currentValue + 4
                                        # if value > 100:
                                        #     value = 100
                                        # if value < 0:
                                        #     value = 0
                                    else:
                                        value = 100
                                if value == "minus":
                                    if currentValue > 4:
                                        value = currentValue - 4
                                        # if value > 100:
                                        #     value = 100
                                        # if value < 0:
                                        #     value = 0
                                    else:
                                        value = 0

                                if j["id"] == "Volume" and id == "ScreenReader":
                                    valuePath = "" + \
                                        str(id)+"-"+str(subitem_id) + \
                                        "-"+str(value)+""
                                    self.sayAndSet(
                                        "Speech volume "+str(int(value)), "/changevolume", valuePath, 0.5, tag="ui")
                                elif j["id"] == "SfxVolume":
                                    valuePath = "" + \
                                        str(id)+"-"+str(subitem_id) + \
                                        "-"+str(value)+""
                                    self.sayAndSet(
                                        "SFX volume "+str(int(value)), "/changesfxvolume", valuePath, 0.5, tag="ui")
                                else:
                                    self.say(
                                        "Slider "+str(int(value)), 0.5, tag="ui")
                            elif j["type"] == "spin":
                                if j["id"] == "SpeechSpeed":
                                    self.sayAndSet(
                                        "Speech speed "+str(int(value)), "/changespeed", value, 0.5, tag="ui")
                                else:
                                    self.say("Spin "+str(int(value)),
                                             0.5, tag="ui")
                            elif j["type"] == "combo":
                                if j["id"] == "SfxSelect":
                                    valuePath = "" + \
                                        str(id)+"-"+str(subitem_id) + \
                                        "-"+str(value)+""

                                    # get index in self.wavs
                                    index = self.wavs.index(value)
                                    self.sayAndSet(
                                        "SFX Changed to Sound "+str(index+1)+"", "/changesfx", valuePath, 0.5, tag="ui")
                                else:
                                    self.say("Combo "+str(value),
                                             0.5, tag="ui")
        # apply new value
        for i in self.data[id]["subItems"]:
            if i["id"] == subitem_id:
                oldvalue = i["value"]
                i["value"] = value
                print("MODIFIED SUBITEM - OLD,NEW,TAG",
                      oldvalue, value, i["id"])

        self.update_database()

    def update_widget_value(self, id, subitem_id, name, value):
        """ modify an existing package """
        # find subitem with subitem_id id and modify it

        # find subitem with subitem_id id and modify it
        print("UPDATING SUBITEM WIDGET", id, subitem_id, name, value)
        # iterate currentItems and diff new value

    def get_subitem(self, id, subitem_id):
        """ get an existing subitem """
        # find subitem with subitem_id id and return it
        for i in self.data[id]["subItems"]:
            if i["id"] == subitem_id:
                return i
        return None

    def set_datamodel(self, data):
        self.datamodel = []

        # iterate over the data keys
        rootIndex = 0
        for index in range(len(data.keys())):

            # find key by index
            i = list(data.keys())[index]

            # if rootIndex == 0:
            #     rootIndex += 1
            # else:
            #     rootIndex += 2

            # rootIndexDescTitle = rootIndex + 1

            # print(i, data[i]["desc"], data[i]
            #       ["full_desc"], data[i]["subItems"])

            rootIndex += 1

            currentRootIndex = rootIndex

            subitems = []
            loadedSubItems = data[i]["subItems"]
            # sort by tabIndex
            loadedSubItems = sorted(
                loadedSubItems, key=lambda k: k['tabIndex'])

            rootIndex += 1

            subitems.append(
                {"rootIndex": rootIndex, "id": ""+i+"-desc", "tabIndex": data[i]["tabIndex"], "title": data[i]["full_desc"], "value": data[i]["desc"], "type": "desc"})

            for index2 in range(len(loadedSubItems)):

                j = loadedSubItems[index2]

                rootIndex += 1
                # rootIndexDescTitle += 1

                # print(j["title"], j["value"])
                if j["type"] == "switch":
                    subitems.append(
                        {"rootIndex": rootIndex, "id": j["id"], "tabIndex": j["tabIndex"], "title": j["title"], "value": j["value"], "type": "switch"})
                elif j["type"] == "rate":
                    subitems.append(
                        {"rootIndex": rootIndex, "id": j["id"], "tabIndex": j["tabIndex"], "title": j["title"], "value": j["value"], "type": "rate"})
                elif j["type"] == "slider":
                    subitems.append(
                        {"rootIndex": rootIndex, "id": j["id"], "tabIndex": j["tabIndex"], "title": j["title"], "value": j["value"], "type": "slider", "range": j["range"]})
                elif j["type"] == "spin":
                    subitems.append(
                        {"rootIndex": rootIndex, "id": j["id"], "tabIndex": j["tabIndex"], "title": j["title"], "value": j["value"], "type": "spin", "range": j["range"]})
                else:
                    subitems.append(
                        {"rootIndex": rootIndex, "id": j["id"], "tabIndex": j["tabIndex"], "title": j["title"], "value": j["value"], "type": j["type"]})

            self.datamodel.append(
                {"rootIndex": currentRootIndex, "id": i, "name": data[i]["desc"], "desc": data[i]["full_desc"], "tabIndex": data[i]["tabIndex"], "subitems": subitems})
        # print("DATA_MODEL\n", json.dumps(self.datamodel, indent=4))

        # if self.mywindow exists
        # send datamodel
        # else
        # wait 3 seconds and try again

        try:
            if self.mywindow is not None and self.mywindow.targetwindow is not None:
                self.stateTransfer("datamodel")
            else:
                print("DATAMODEL FAILED-NOT_READY")
                t = Timer(3, lambda: self.stateTransfer("datamodel"))
                t.start()

        except:
            print("DATAMODEL FAILED-NOT_READY-RETRY")
            t = Timer(3, lambda: self.stateTransfer("datamodel"))
            t.start()

        self.update_sfx()

    def refresh_items(self):
        ref = self.iframe
        for i in self.data.keys():
            self.add_item(name=self.data[i]["desc"],
                          desc=self.data[i]["full_desc"], subitems=self.data[i]["subItems"], ref=ref, id=i, tabIndex=self.data[i]["tabIndex"])

    def validate_database(self, dataLoaded):
        # check if the field are the same of defaultConfig
        # if not update the datamodel
        # print("validating database", json.dumps(dataLoaded, indent=4))
        passed = True
        for i in data.defaultConfig.keys():
            # print("validating database", i, data.defaultConfig.keys())
            # check if the field exist in self.data
            if i not in dataLoaded.keys():
                dataLoaded[i] = data.defaultConfig[i]
                passed = False
                # break

            # check if the subitems exist in dataLoaded
            subItens = dataLoaded[i]["subItems"]
            # sort by tabIndex
            subItens = sorted(subItens, key=lambda k: k['tabIndex'])
            # select id
            subItens = [x["id"] for x in subItens]
            # print("validating database", subItens, dataLoaded[i]["subItems"])

            for j in data.defaultConfig[i]["subItems"]:
                if j["id"] not in subItens:
                    dataLoaded[i]["subItems"].append(j)
                    passed = False
                    # break

        return passed, dataLoaded

    def read_database(self):
        """ read the database containing package data """
        global documentsPath
        dbPath = os.path.join(documentsPath, "guideplay_config.json")
        ref = ''
        if os.path.exists(dbPath):
            with open(dbPath) as f:
                dataLoaded = json.load(f)

                result, validated = self.validate_database(dataLoaded)
                if result is False:
                    self.data = validated
                    self.update_database()
                else:
                    self.data = dataLoaded
                    self.set_datamodel(self.data)
        else:
            self.data = data.defaultConfig
            self.update_database()

        for i in self.data.keys():
            self.add_item(name=self.data[i]["desc"],
                          desc=self.data[i]["full_desc"], subitems=self.data[i]["subItems"], ref=ref, id=i, tabIndex=self.data[i]["tabIndex"])
        self.tabIndex = 0
        self.tabIndexSub = 0

    def read_files(self, ext, repo, folder="sounds"):
        assets = os.path.join(App.DIRPATH, folder)
        # cleart repo
        repo.clear()
        for filename in os.listdir(assets):
            if ext == "wav":
                if filename.endswith("."+ext):
                    repo.append(filename)
        # remove duplicates
        repo = list(dict.fromkeys(repo))

    def update_sfx(self):
        # update sfx
        # print("UPDATE SFX")
        model = {}
        for i in self.datamodel:
            volume = 777
            file = ""
            speed = -1
            sectors = "not-set"
            compass = "not-set"
            screen = "not-set"

            # enemy props
            enemyReport = "not-set"
            for s in i["subitems"]:
                # print("UPDATE SFX", s["id"], s["value"])

                if "SfxVolume" in s["id"]:
                    volume = s["value"]

                # SCREEN READER PROPS

                if i["id"] == "ScreenReader" and s["id"] == "Volume":
                    volume = s["value"]

                if i["id"] == "ScreenReader" and s["id"] == "SpeechSpeed":
                    speed = s["value"]

                if i["id"] == "ScreenReader" and s["id"] == "InGameSectorVoice":
                    sectors = s["value"]

                if i["id"] == "ScreenReader" and s["id"] == "InGameCompassVoice":
                    compass = s["value"]

                if i["id"] == "ScreenReader" and s["id"] == "InGameScreenReader":
                    screen = s["value"]

                # ENEMY PROPS

                if i["id"] == "EnemyProximity" and s["id"] == "EnemyProximityAlerts":
                    enemyReport = s["value"]

                if s["id"] == "SfxSelect":
                    file = s["value"]

            itemModel = {"file": file, "volume": volume}
            if speed != -1:
                itemModel["speed"] = speed
            if sectors != "not-set":
                itemModel["sectors"] = sectors
            if compass != "not-set":
                itemModel["compass"] = compass
            if screen != "not-set":
                itemModel["screen"] = screen
            if enemyReport != "not-set":
                itemModel["enemyReport"] = enemyReport
            model[i["id"]] = itemModel

        if client is not None:
            client.send_message("/updatesfx", json.dumps(model))

        # print("UPDATE SFX MODEL", json.dumps(model, indent=4))


global cliController
global testTimer
testTimer = None
cliController = None


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--dev",
                        default="0", help="dev mode")

    parser.add_argument("--prod",
                        default="0", help="prod mode")

    args = parser.parse_args()

    devMode = False
    env = os.environ.get('GUIDEPLAYPROD', "0")

    if args.dev == "1":
        devMode = True
    if args.prod == "1":
        devMode = False
    if env == "1":
        devMode = False

    alreadyRunning = False
    alreadyRunning = checkRunningProcess("guide-play.exe")
    time.sleep(1)

    # if alreadyRunning is True:
    #     print("GUIDEPLAY ALREADY RUNNING")
    #     focus_guideplay()
    #     sys.exit(0)

    # def cb(result):
    #     if result is not None:
    #         print("GUIDEPLAY ALREADY RUNNING 2 ", result)
    #         focus_guideplay()
    #         sys.exit(0)

    # find_window_wildcard(".*Guide Play.*", cb)
    # time.sleep(2)

    # if alreadyRunning is True:
    #     print("GUIDEPLAY ALREADY RUNNING 3")
    #     focus_guideplay()
    #     sys.exit(0)
    app = App()

    try:
        # Close the splash screen.
        import pyi_splash
        pyi_splash.update_text("Guide Play is starting...")
    except ImportError:
        # Otherwise do nothing.
        pass
