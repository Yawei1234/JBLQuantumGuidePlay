

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
from customtkinter import *
from subprocess import run
import customtkinter
from PIL import Image, ImageTk
from threading import Timer, Thread
import tkinter as tk
from widgets import *
import pyglet
import os
from pystray import MenuItem as item
import pystray
from pythonosc import udp_client, osc_server
from pythonosc.dispatcher import Dispatcher
import data
import json
import time
import logging
import argparse
# import game processes
from capture import *
from radar import *
from mss import mss
import ctypes.wintypes
CSIDL_PERSONAL = 5       # My Documents
SHGFP_TYPE_CURRENT = 0   # Get current, not default value
pathBUF = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
ctypes.windll.shell32.SHGetFolderPathW(
    None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, pathBUF)

os.chdir(os.path.dirname(os.path.abspath(__file__)))
PhotoImage = ImageTk.PhotoImage
currentDir = os.getcwd()
client = udp_client.SimpleUDPClient("127.0.0.1", data.port)

global devMode
global app
global documentsPath

documentsPath = pathBUF.value


class GameApp():

    def __init__(self):
        self.game = None
        self.radar = None
        self.gameThread = None
        self.radarThread = None
        self.gameIsAlive = False
        self.radarIsAlive = False
        self.threadCVGamePlay = None

        self.resolutions = []
        self.monitors = []

        self.getMonitors()

    def getMonitors(self):
        for i in range(len(mss().monitors)):
            monitor = mss().monitors[i]
            self.resolutions.append(
                (monitor["top"], monitor["left"], monitor["width"], monitor["height"]))
            self.monitors.append("Monitor " + str(i + 1))
        data.resolutions = self.resolutions
        data.monitors = self.monitors

    def startProcess(self, process):

        if process == "cv-gameplay":
            data.run = True
            logging.info('process_started')

            if self.threadCVGamePlay == None:
                self.threadCVGamePlay = threading.Thread(target=startRawCapture,
                                                         daemon=True, args=('kix',))
                self.threadCVGamePlay.start()
            elif self.threadCVGamePlay != None:
                self.threadCVGamePlay.start()

        # threading.Thread(target=findHandPos, daemon=True, args=(scaleMode.get(),)).start()
        # threading.Thread(target=signaler.run, daemon=True).start()
        # threading.Thread(target=sd_testing.run, daemon=True).start()

    def stopProcess():
        # window.destroy()

        data.run = False
        data.captureRunning = False
        data.radarRunning = False
        data.radarProcessing = False


class App(customtkinter.CTk):

    global devMode

    DIRPATH = os.path.join(os.path.dirname(__file__))
    LOADED_IMAGES = {}

    pyglet.font.add_file('fonts/RocGrotesk.ttf')
    pyglet.font.add_file('fonts/RocGrotesk-ExtraWide-Bold.ttf')
    pyglet.font.add_file('fonts/RocGrotesk-Bold.ttf')
    pyglet.font.add_file('fonts/kostic_.otf')

    def __init__(self):
        super().__init__()

        self.lastSay = "Welcome"
        self.sayTime = Timer(2, lambda: self.sendSay())
        self.sayTime.start()

        self.title("Guide Play (Alpha 0.0.3)")
        self.width = int(self.winfo_screenwidth()/2.5)
        self.height = int(self.winfo_screenheight()/2)
        self.geometry("1280x720")
        self.configure(background="#8DC7D5")
        self.resizable(False, False)
        self.wm_attributes('-transparentcolor', '#ff9900')
        # self.bind("<1>", lambda event: event.widget.focus_set())
        self.iconpath = ImageTk.PhotoImage(
            file=os.path.join("assets", "app-icon-3x.png"))
        self.wm_iconbitmap()
        self.iconphoto(False, self.iconpath)

        self.background_image = PhotoImage(file="assets/bg.png")
        self.background_label = tk.Label(self, image=self.background_image)
        self.background_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.background_label.photo = self.background_image

        self.trayImage = Image.open("assets/app-icon.ico")
        self.trayMenu = (item('Audio Settings', lambda: self.show_window(None, " AUDIO SETTINGS ")), item(
            'About Guide Play', lambda: self.show_window(None, " ABOUT ")), item('Exit Guide Play', self.hide_window), )

        self.trayIcon = pystray.Icon(
            "name", self.trayImage, "guide-play-beta-tray", self.trayMenu)
        self.trayIcon.run_detached()
        self.protocol('WM_DELETE_WINDOW', self.quit_root)

        self.iframe = self.createFrame("test", "test")

        self.bindKeys()
        # focus after 0.5 seconds to avoid focus stealing
        self.after(500, lambda: self.focus_force())

        self.datamodel = []
        self.currentItems = []
        self.currentSubItem = None
        self.tabIndex = 0
        self.tabIndexSub = -3
        self.wavs = []
        self.read_files('wav', self.wavs)

        self.menuItems = [" VIDEO SETUP ", " AUDIO SETTINGS ", " ABOUT "]
        self.currentMenu = None
        self.data = {}
        self.create_menu(self.menuItems[1])
        self.updateMenuTab(self.menuItems[1])

        # services processess
        self.crashTimes = 0
        self.lastKeepAlive = -1
        self.serverIsAlive = False
        self.serverThread = Thread(target=self.startServer, args=())
        self.serverThread.start()

        self.devMode = devMode

        # game processess

        self.processController = GameApp()

        self.processController.startProcess("cv-gameplay")

    def startServer(self):

        def start_script(self):
            global subprocessREF

            # prefix ../osc_tts_server/server.py
            if self.devMode:
                print("DEV MODE")

                data.devMode = True
                data.monitorSelected = 1

                daemonPath = "../osc_tts_server/server.py"
                pythonInterpreter = "../osc_tts_server/Scripts/python.exe"

                finalCOMMAND = ""+str(pythonInterpreter)+" "+str(daemonPath)+" --path "+str(App.DIRPATH) + \
                    " --port "+str(data.port)+" --appport " + \
                    str(data.appport)+""
            else:
                daemonPath = os.path.join(
                    App.DIRPATH, "server", "guide-play-services.exe")
                finalCOMMAND = ""+str(daemonPath)+" --path "+str(App.DIRPATH) + \
                    " --port "+str(data.port)+" --appport " + \
                    str(data.appport)+""
            try:
                # Make sure 'python' command is available
                subprocessREF = run(finalCOMMAND, check=True, shell=True)
                self.crashTimes = 0

            except:
                # Script crashed, lets restart it!
                # get exception and handle it
                # e = sys.exc_info()[0]
                handle_crash(subprocessREF, finalCOMMAND)

        def handle_crash(e, cmd):

            self.crashTimes += 1
            if e is not None:
                print("CRASHED", e.stdout, e.stderr)
            print("CRASHED_RESTARTING", self.crashTimes)
            print("CRASHED_CMD", cmd)

            self.lastKeepAlive = -1
            self.serverIsAlive = False

        def checkLiveness():
            while True:
                diff = time.time() - self.lastKeepAlive
                sleepSecs = 1
                print("CHECK LIVENESS", diff,
                      self.lastKeepAlive, self.serverIsAlive)
                if diff > 5:
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
                    self.serverIsAlive = True
                    sleepSecs = 1

                if "ABOUT" in self.currentMenu:
                    # update currentitems with keepalive id
                    # print("ABOUT FOUND", self.currentItems)

                    for i in self.currentItems:
                        if i["id"] == "keepalive":
                            print("KEEPALIVE FOUND", i["id"])
                            color = "#ff0000"
                            if self.serverIsAlive:
                                color = "#F9E681"
                            i["desc"]["label"].configure(
                                text="lastkeepAlive: "+str(self.lastKeepAlive)+" - "+str(diff)+"", text_color=color)
                            # break

                time.sleep(sleepSecs)

        def keepalive(unused_addr, args, say):
            # print("\n\n\n\nserver_alive", say)
            self.lastKeepAlive = time.time()
            self.serverIsAlive = True
            # diff = time.time() - self.lastKeepAlive

        def asksync(unused_addr, args, say):
            # print("\n\n\n\nasksync", say)
            self.update_sfx()
            return

        dispatcher = Dispatcher()
        dispatcher.map("/keepalive", keepalive, "Keep Alive")
        dispatcher.map("/asksync", asksync, "Ask Sync")

        server = osc_server.ThreadingOSCUDPServer(
            ("127.0.0.1", data.appport), dispatcher)
        print("Serving on {}".format(server.server_address))

        t = Thread(target=checkLiveness, args=())
        t.start()

        server.serve_forever()

    def updateMenuTab(self, value):

        if self.currentMenu == value:
            return
        self.currentMenu = value

        if self.currentMenu == " AUDIO SETTINGS ":
            self.remove_items()
            self.read_database()
            return

        if self.currentMenu == " VIDEO SETUP ":
            self.remove_items()
            self.add_video_items()
            return

        if self.currentMenu == " ABOUT ":
            self.remove_items()
            self.add_about_items()
            return

    def create_menu(self, startItem=None):

        def segmented_button_callback(value):
            self.updateMenuTab(value)

            print("segmented button clicked:", value)

        segemented_button = customtkinter.CTkSegmentedButton(self, values=self.menuItems,
                                                             command=segmented_button_callback, height=80, selected_color="#18173e", unselected_color="#000029", fg_color="#000029", bg_color="#000029", text_color="#f9e681", text_color_disabled="#18173e", font=("Segoe UI Semibold", 20))
        segemented_button.place(x=45, y=50)
        if startItem is not None:
            segemented_button.set(startItem)

    def say(self, say, delay=2):
        if self.lastSay == say:
            return
        self.sayTime.cancel()
        self.lastSay = say
        self.sayTime = Timer(delay, lambda: self.sendSay())
        self.sayTime.start()

    def sayAndSet(self, say, topic, value, delay=2):
        self.sayTime.cancel()
        self.lastSay = value
        self.sayTime = Timer(delay, lambda: self.sendSay(topic, say))
        self.sayTime.start()

    def sendSay(self, topic="/saynow", nextSay=None):
        print("SEND SAY", self.lastSay)
        if client is not None:
            client.send_message(topic, self.lastSay)
            if nextSay is not None:
                self.say(nextSay, 0)

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

        if self.currentMenu == " VIDEO SETUP ":
            return

        if self.currentMenu == " ABOUT ":
            return

        if self.tabIndexSub == -3:
            nextTitle = self.datamodel[self.tabIndex]["name"]
            nextDesc = self.datamodel[self.tabIndex]["desc"]

            print("TAB INDEX NEGATIVE_TITLE",
                  nextTitle, self.tabIndexSub)

            self.say(nextTitle, 0.5)

            self.tabIndexSub = -2
        elif self.tabIndexSub == -2:
            nextTitle = self.datamodel[self.tabIndex]["name"]
            nextDesc = self.datamodel[self.tabIndex]["desc"]

            print("TAB INDEX NEGATIVE_TITLE",
                  nextTitle, self.tabIndexSub)

            self.say(nextDesc, 0.5)

            self.tabIndexSub = -1

        # prev states

        elif self.tabIndexSub == -5:
            nextTitle = self.datamodel[self.tabIndex]["name"]
            nextDesc = self.datamodel[self.tabIndex]["desc"]

            print("TAB INDEX NEGATIVE_REVERSE_TITLE",
                  nextTitle, self.tabIndexSub)

            self.say(nextTitle, 0.5)

            self.tabIndexSub = -4

        elif self.tabIndexSub == -4:
            nextTitle = self.datamodel[self.tabIndex]["name"]
            nextDesc = self.datamodel[self.tabIndex]["desc"]

            print("TAB INDEX NEGATIVE_REVERSE_DESC",
                  nextTitle, self.tabIndexSub)

            self.say(nextDesc, 0.5)

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
                    self.say(nextSubTitle, 0.5)
                    print("TAB INDEX TITLE", nextTitle, nextSubTitle)
                    break

        self.hightLightCurrentTab()

    def setTabIndex(self, newIndex, newSubIndex):
        print("SET TAB INDEX", newIndex, newSubIndex)

        self.tabIndex = newIndex
        self.tabIndexSub = newSubIndex

        self.hightLightCurrentTab(True)

    def keyboardEvent(self, event):
        print("KEYBOARD CHANGES", event.keysym)

        if event.keysym == "Escape":
            self.quit_root()
        elif event.keysym == "Tab":
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
        spacerTop = tk.Canvas(frame, width=1180, height=65,
                              bg="#000029", highlightthickness=0)
        spacerTop.pack(anchor="w", expand=True, pady=0, padx=0, side="top")

        spacerHR = tk.Canvas(frame, width=1180, height=1,
                             bg="#1e1e47", highlightthickness=0)
        spacerHR.pack(anchor="w", expand=True, pady=0, padx=0, side="top")

        spacerBot = tk.Canvas(frame, width=1180, height=45,
                              bg="#000029", highlightthickness=0)
        spacerBot.pack(anchor="w", expand=True, pady=0, padx=0, side="top")

        model["spacerTop"] = spacerTop
        model["spacerHR"] = spacerHR
        model["spacerBot"] = spacerBot
        return model

    def add_video_items(self):
        """ add all packages to the list """
        self.remove_items()
        self.add_item("VIDEO SETUP", "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Quisque ut interdum augue, ac viverra sem. ", [
        ], self.iframe, 0, 0)

    def add_about_items(self):
        """ add all packages to the list """
        self.remove_items()
        self.add_item("GUIDE PLAY", "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Quisque ut interdum augue, ac viverra sem. \nCurabitur quis sollicitudin dui. In eget sapien ex. Sed mi dui, tincidunt quis molestie rutrum, varius at diam. \n\n In dolor purus, facilisis quis pretium vel, porttitor nec ipsum. \nPraesent odio ipsum, iaculis dignissim elementum id, ornare vel massa. \nEtiam ullamcorper nulla suscipit tristique venenatis. Suspendisse porta, tellus \nsit amet aliquet tempus, leo orci lacinia tortor, sit amet semper nulla \nligula a felis. Donec magna arcu, rhoncus in maximus at, sagittis ac elit. \n\nNam ac dictum tellus. Suspendisse ornare velit in molestie gravida. \nAenean velit tortor, porta et efficitur quis, lobortis ac odio. ", [], self.iframe, 0, 0)
        # add keep alive information
        diff = time.time() - self.lastKeepAlive
        descRef = self.creteDescription(
            self.iframe, "keepalive", "lastkeepAlive: "+str(self.lastKeepAlive)+" - "+str(diff)+"", "keepalive")
        isOnline = self.lastKeepAlive > 0 and diff < 5
        if isOnline:
            descRef["label"].configure(text_color="#F9E681")
        else:
            descRef["label"].configure(text_color="#ff0000")

        self.currentItems.append({
            "id": "keepalive",
            "tabIndex": 0,
            "subitems": [],
            "desc": descRef,
        })

        print("ABOUT ITEMS", self.currentItems)

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

    def remove_items(self):
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

        self.iframe.update()
        # self.after(50, self.update)

        self.currentItems.clear()

        for i in destroyList:
            i.destroy()
            self.iframe.update()
            # self.after(50, self.update)
        # time.sleep(1)
        # self.read_database()
        # self.refresh_items()
        self.scrollToY(0)

    def hightLightCurrentTab(self, say=False):
        for i in self.currentItems:

            if i["tabIndex"] == self.tabIndex:
                print("TRACK___ current tab found", i["id"], self.tabIndexSub)
                # get y position of the canvas
                y = i["title"]["canvas"].winfo_y()
                print("SCROLLING_TOy", y)
                self.scrollToY(y)

                if self.tabIndexSub > -3:

                    i["title"]["canvas"].config(
                        highlightthickness=3, highlightbackground="#F9E681")
                    if self.tabIndexSub == -1:
                        i["desc"]["label"].configure(
                            text_color="#F9E681")
                    else:
                        i["desc"]["label"].configure(
                            text_color="#ffffff")
            else:
                i["title"]["canvas"].configure(
                    highlightthickness=3, highlightbackground="#000029")
        # higjtlight subitems
        for i in self.currentItems:
            for s in i["subitems"]:

                if s["tabIndex"] == self.tabIndexSub and i["tabIndex"] == self.tabIndex:
                    print("current sub tab found", s["id"])
                    s["canvas"].config(
                        highlightthickness=3, highlightbackground="#F9E681")
                    # set focus
                    s["canvas"].focus_set()
                    self.currentSubItem = {
                        "parentId": i["id"],
                        "id": s["id"].split("-")[1],
                        "title": s["title"],
                        "type": s["type"]
                    }
                    if say:
                        self.say(s["title"], 0.5)
                else:
                    s["canvas"].config(
                        highlightthickness=3, highlightbackground="#000029")

    def creteDescription(self, frame, name, desc, id):
        model = {}
        label = CTkLabel(master=frame, text=desc, justify="left",
                         font=("Segoe UI Variable Small Light", 17))

        # def removeItemEvent():
        #     print("remove item", id)
        #     # self.data.pop(id)
        #     # self.update_database()
        #     self.remove_items()

        # btn = CTkButton(master=frame, text=name, command=removeItemEvent)
        # btn.pack(anchor="n", expand=True, padx=30, pady=20)
        # model["btn"] = btn

        label.pack(anchor="w", expand=True, pady=10, padx=10)
        model["label"] = label

        return model

    def createTitle(self, frame, title):
        model = {}
        borderSize = 0

        canvas = tk.Canvas(frame, width=890, height=70,
                           bg="#000029", highlightthickness=borderSize, relief="solid", highlightbackground="#F9E681")
        canvas.pack(anchor="w", expand=True, pady=0, padx=0, side="top")

        canvas.create_text(10, 40, anchor="nw", font=(
            "FSP DEMO - Roc Grotesk Bold", 18), fill="#ffffff", text=title)

        image = Image.open("assets/bg-slot.png")
        img = ImageTk.PhotoImage(image)
        canvas.create_image(0, 0, image=img)
        canvas.config()

        model["canvas"] = canvas
        return model

    def createSubItem(self, frame, name, item, parentId, parentTabIndex):
        model = {
            "id": ""+str(parentId)+"-"+str(item["id"])+"",
            "tabIndex": item["tabIndex"],
            "type": item["type"],
            "title": name,
        }

        # creata Frame
        frameROW = CTkFrame(frame, width=1180, height=70,
                            fg_color="#000029")
        # frameROW.grid(column=1)
        frameROW.pack(anchor="w", expand=True, pady=6, padx=0, side="top")
        model["frame"] = frameROW
        # on click set tabindex

        canvas = tk.Canvas(frameROW, width=890, height=70,
                           bg="#000029", highlightthickness=0)
        # canvas.pack(anchor="w", expand=True, pady=0, padx=0, side="top")

        canvas.grid(row=1, column=0, sticky='w')
        # self.name_entry.grid(row=1, column=1, sticky='w')

        canvas.create_text(10, 20, anchor="nw", font=(
            "FSP DEMO - Roc Grotesk Bold", 18), fill="#aec7fb", text=name)

        canvas.bind("<Button-1>", lambda e: self.setTabIndex(
            parentTabIndex, item["tabIndex"]))

        model["canvas"] = canvas

        if item["type"] == "spin":
            # print("spin", item["id"], item["value"], parentId)
            range = item["range"].split("-")

            def spin_event(value):
                if value > int(range[1]) or value < int(range[0]):
                    return
                spinbox.set(value)
                self.modify_subitem(parentId, item["id"], name, value)
                print("SPIN", value)
                # say value

            def spinFocus(value, event):
                print("SPIN FOCUS IN", value)
                spinbox.entry.delete(0, "end")
                spinbox.entry.insert(0, spinbox.get())

            spinbox = FloatSpinbox(
                frameROW, width=180, step_size=1, command=spin_event, max_value=int(range[1]), min_value=int(range[0]), value=item["value"])
            # spinbox.pack(anchor="w", padx=20, pady=20)
            spinbox.grid(row=1, column=1, sticky='w', padx=0, pady=0)
            spinbox.entry.bind(
                "<FocusIn>", lambda e: print("SPIN FOCUS IN", spinbox.get()))
            spinbox.entry.bind(
                "<FocusOut>", lambda e: print("SPIN FOCUS OUT", spinbox.get()))

        if item["type"] == "switch":
            # print("switch", item["id"], item["value"], parentId)
            switch_var = customtkinter.StringVar(value=item["value"])

            def switch_event():
                self.modify_subitem(
                    parentId, item["id"], name, switch_var.get())
                print("switch toggled, current value:", switch_var.get())

            switch = customtkinter.CTkSwitch(frameROW, text="", command=switch_event,
                                             button_hover_color="#3a04af", button_color="#3a04af", fg_color="#aec7fb", progress_color="#aec7fb",
                                             switch_width=256, switch_height=64, corner_radius=32,
                                             variable=switch_var, onvalue="on", offvalue="off", width=280)

            # on click say switch value

            # switch.pack(anchor="e", expand=True, padx=30, pady=0)
            switch.grid(row=1, column=1, sticky='e', padx=10)
            model["switch"] = switch

        if item["type"] == "rate":
            # print("rate", item["id"], item["value"], parentId)
            range = item["range"].split("-")

            def slider_event(value):
                slidervar.set(value)
                self.modify_subitem(parentId, item["id"], name, value)
                print(value)

            slidervar = customtkinter.IntVar(value=item["value"])
            slider = customtkinter.CTkSlider(frameROW, from_=int(
                range[0]), to=int(range[1]), progress_color="#aec7fb", button_hover_color="#3a04af", button_color="#aec7fb", variable=slidervar, command=slider_event, width=240)
            # slider.pack(anchor="e", expand=True, padx=30, pady=0)280
            # on change say slider value

            slider.grid(row=1, column=1, sticky='e', padx=20)
            model["slider"] = slider

        if item["type"] == "combo":
            # create combobox with wav files
            # print("combo", item["id"], item["value"], parentId)
            def combobox_callback(choice):
                self.modify_subitem(parentId, item["id"], name, choice)

            combobox = customtkinter.CTkComboBox(frameROW, values=self.wavs,
                                                 command=combobox_callback,  font=("FSP DEMO - Roc Grotesk Bold", 18), width=240, hover=False, height=55, corner_radius=32, dropdown_fg_color="#18173f", fg_color="#aec7fb", border_width=0, button_color="#3a04af", button_hover_color="#6852cd", text_color="#6852cd")
            combobox.grid(row=1, column=1, sticky='e', padx=20)
            try:
                combobox.set(item["value"])
            except:
                print("combobox set error", item["value"])
            model["combo"] = combobox

        image = Image.open("assets/bg-slot.png")
        img = ImageTk.PhotoImage(image)
        canvas.create_image(0, 0, image=img)
        canvas.config()

        return model

    def createFrame(self, name, icon):
        iframe = CTkScrollableFrame(master=self, bg_color="#000029", fg_color="#000029", border_color="", border_width=0,
                                    orientation="vertical", scrollbar_button_color="#18173f",  width=1180, height=560)
        iframe.place(x=40, y=130)

        return iframe

    def quit_window(self, icon, item):
        icon.stop()
        self.destroy()

    def getSubProcess(self):
        global subprocessREF
        # print("GETTING SUBPROCESS", subprocessREF)
        return subprocessREF

    def quit_root(self, key=None):

        subprocessREF = self.getSubProcess()

        print("TERMINATING_START", subprocessREF)

        if subprocessREF is None:
            if client is not None:
                print("SENDING EXIT")
                client.send_message("/exit", 1)

        # exit pyhon app
        if subprocessREF is not None:
            try:
                subprocessREF.terminate()
                print("TERMINATING", subprocessREF)
                time.sleep(1)
            except:
                print("TERMINATING_ERROR", subprocessREF)

        self.destroy()
        self.trayIcon.stop()

        os._exit(0)

    def show_window(self, icon, item):
        print("show window", icon, item)
        self.after(0, self.deiconify())
        self.focus_force()
        if item is not None:
            self.updateMenuTab(item)
        # icon.stop()

    def hide_window(self):
        self.withdraw()
        image = Image.open("assets/app-icon.ico")
        menu = (item('Audio settings', lambda: self.show_window(None, " AUDIO SETTINGS ")), item(
            'About Guide Play', lambda: self.show_window(None, " ABOUT ")), item('Exit Guide Play', self.quit_window))
        icon = pystray.Icon("name", image, "guide-play-beta-tray", menu)
        icon.run_detached()

    def update_database(self):
        """ update the database containing package data """
        database = os.path.join(documentsPath, "guideplay_config.json")

        self.set_datamodel(self.data)
        with open(database, "w") as f:
            json.dump(self.data, f, indent=4)

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
                                    self.say("Switch on", 0.5)
                                else:
                                    self.say("Switch off", 0.5)
                            elif j["type"] == "rate" or j["type"] == "slider":
                                if j["id"] == "Volume" and id == "ScreenReader":
                                    valuePath = "" + \
                                        str(id)+"-"+str(subitem_id) + \
                                        "-"+str(value)+""
                                    self.sayAndSet(
                                        "Speech volume "+str(int(value)), "/changevolume", valuePath, 0.5)
                                elif j["id"] == "SfxVolume":
                                    valuePath = "" + \
                                        str(id)+"-"+str(subitem_id) + \
                                        "-"+str(value)+""
                                    self.sayAndSet(
                                        "SFX volume "+str(int(value)), "/changesfxvolume", valuePath, 0.5)
                                else:
                                    self.say("Slider "+str(int(value)), 0.5)
                            elif j["type"] == "spin":
                                if j["id"] == "SpeechSpeed":
                                    self.sayAndSet(
                                        "Speech speed "+str(int(value)), "/changespeed", value, 0.5)
                                else:
                                    self.say("Spin "+str(int(value)), 0.5)
                            elif j["type"] == "combo":
                                if j["id"] == "SfxSelect":
                                    valuePath = "" + \
                                        str(id)+"-"+str(subitem_id) + \
                                        "-"+str(value)+""
                                    self.sayAndSet(
                                        "SFX Changed", "/changesfx", valuePath, 0.5)
                                else:
                                    self.say("Combo "+str(value), 0.5)
        # apply new value
        for i in self.data[id]["subItems"]:
            if i["id"] == subitem_id:
                i["value"] = value
                print("MODIFIED SUBITEM",  i["id"])

        self.update_database()

    def update_widget_value(self, id, subitem_id, name, value):
        """ modify an existing package """
        # find subitem with subitem_id id and modify it

        # find subitem with subitem_id id and modify it
        print("UPDATING SUBITEM WIDGET", id, subitem_id, name, value)
        # iterate currentItems and diff new value
        for i in self.currentItems:
            if i["id"] == id:
                for j in i["subitems"]:
                    if j["id"] == ""+str(id)+"-"+str(subitem_id)+"":

                        if j["type"] == "switch":
                            print("UPDATING-SWITCH", value)
                            if value == "on":
                                j["switch"].select()
                            else:
                                j["switch"].deselect()
                        elif j["type"] == "rate" or j["type"] == "slider":
                            print("UPDATING-RATE", value)
                            j["slider"].set(value)
                            print("SLIDER", value)
                        elif j["type"] == "spin":
                            print("SPIN", value)
                            j["spin"].set(value)
                        elif j["type"] == "combo":
                            print("COMBO", value)
                            j["combo"].set(value)
                        else:
                            print("OTHER", value)

    def get_subitem(self, id, subitem_id):
        """ get an existing subitem """
        # find subitem with subitem_id id and return it
        for i in self.data[id]["subItems"]:
            if i["id"] == subitem_id:
                return i
        return None

    def set_datamodel(self, data):
        # iterate over the data and create a new data model
        self.datamodel = []
        for i in data.keys():
            # print(i, data[i]["desc"], data[i]
            #       ["full_desc"], data[i]["subItems"])

            subitems = []
            for j in data[i]["subItems"]:
                # print(j["title"], j["value"])
                if j["type"] == "switch":
                    subitems.append(
                        {"id": j["id"], "tabIndex": j["tabIndex"], "title": j["title"], "value": j["value"], "type": "switch"})
                elif j["type"] == "rate":
                    subitems.append(
                        {"id": j["id"], "tabIndex": j["tabIndex"], "title": j["title"], "value": j["value"], "type": "rate"})
                elif j["type"] == "slider":
                    subitems.append(
                        {"id": j["id"], "tabIndex": j["tabIndex"], "title": j["title"], "value": j["value"], "type": "slider", "range": j["range"]})
                elif j["type"] == "spin":
                    subitems.append(
                        {"id": j["id"], "tabIndex": j["tabIndex"], "title": j["title"], "value": j["value"], "type": "spin", "range": j["range"]})
                else:
                    subitems.append(
                        {"id": j["id"], "tabIndex": j["tabIndex"], "title": j["title"], "value": j["value"], "type": j["type"]})

            self.datamodel.append(
                {"id": i, "name": data[i]["desc"], "desc": data[i]["full_desc"], "tabIndex": data[i]["tabIndex"], "subitems": subitems})
        # print("DATA_MODEL\n", json.dumps(self.datamodel, indent=4))
        self.update_sfx()

    def scrollToY(self, y):
        if self.iframe is not None:
            self.iframe._scrollToY(y)
            self.iframe.update()

    def refresh_items(self):
        ref = self.iframe
        for i in self.data.keys():
            self.add_item(name=self.data[i]["desc"],
                          desc=self.data[i]["full_desc"], subitems=self.data[i]["subItems"], ref=ref, id=i, tabIndex=self.data[i]["tabIndex"])

    def read_database(self):
        """ read the database containing package data """
        database = os.path.join(documentsPath, "guideplay_config.json")
        ref = self.iframe
        if os.path.exists(database):
            with open(database) as f:
                self.data = json.load(f)

                self.set_datamodel(self.data)
        else:
            self.data = data.defaultConfig
            self.update_database()

        for i in self.data.keys():
            self.add_item(name=self.data[i]["desc"],
                          desc=self.data[i]["full_desc"], subitems=self.data[i]["subItems"], ref=ref, id=i, tabIndex=self.data[i]["tabIndex"])
        self.tabIndex = 0
        self.tabIndexSub = -3

        # self.cycleTabIndex('next')

    def read_files(self, ext, repo):

        if ext == "wav":
            assets = os.path.join(App.DIRPATH, "sounds")
            for filename in os.listdir(assets):
                if filename.endswith("."+ext):
                    print("WAVS", filename)
                    repo.append(filename)
                    # print("WAVS", filename)
                    # self.wavs.append(filename)
                    # print("WAVS", self.wavs)
        # for filename in os.listdir("assets"):
        #     if filename.endswith("."+ext):
        #         repo.append(filename)

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


global subprocessREF
subprocessREF = None


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--dev",
                        default="0", help="dev mode")

    args = parser.parse_args()

    devMode = False
    if args.dev == "1":
        devMode = True

    app = App()
    app.mainloop()
