import json
import time
import sys
import numpy as np
# Imports for Window Handler and Window API
####################################
# window resize calc libs
from ctypes import windll, Structure, c_long, byref

# App imports
from AppComponents.mr_importer import *

global windowREF
windowREF = None

# App window info Object From main

####################################


# Window Resize classes and Functions
####################################
class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]


def queryMousePosition():
    pt = POINT()
    windll.user32.GetCursorPos(byref(pt))
    return {"x": pt.x, "y": pt.y}


def doresize(window):
    # Left button down = 0 or 1. Button up = -127 or -128
    state_left = windll.user32.GetKeyState(0x01)
    winWbefore = window.width
    winHbefore = window.height

    mouseactive = queryMousePosition()
    beforex = mouseactive['x']
    beforey = mouseactive['y']

    while True:
        a = windll.user32.GetKeyState(0x01)
        if a != state_left:  # Button state changed
            state_left = a
            print(a)
            if a < 0:
                print('Left Button Pressed')
                break
            else:
                print('Left Button Released')
                break

        mouseactive = queryMousePosition()
        afterx = mouseactive['x']
        aftery = mouseactive['y']
        try:
            totalx = int(beforex)-int(afterx)
            totaly = int(beforey)-int(aftery)

        except:
            print('fail')
        if totalx > 0:
            changerx = winWbefore+(totalx*-1)
        else:

            changerx = winWbefore+(totalx*-1)

        if totaly > 0:
            changerY = winHbefore+(totaly*-1)
        else:
            changerY = winHbefore+(totaly*-1)

        window.resize(changerx, changerY)

        time.sleep(0.01)

# Window Set size be %


def setsizer(window, perW, perH):
    user32 = windll.user32
    user32.SetProcessDPIAware()
    [w, h] = [user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)]

    window.move(10, 10)

    w = (w*(perW/100))  # resize to 80% of user screen W
    y = (h*(perH/100))  # resize to 80% of user screen H
    # print(w,y)
    window.resize(round(w), round(y))
####################################

# Event Triggers on window load/shown/close/closed ..
####################################
# On Load Events


def on_closed(window, callback):
    print('pywebview window is closed')
    callback()


def on_closing(window):
    print('pywebview window is closing')


def on_shown(window):
    print('pywebview window shown')


def on_minimized(window):
    print('pywebview window minimized')


def on_restored(window):
    print('pywebview window restored')


def on_maximized(window):
    print('pywebview window maximized')


def on_loaded(mywindow, onLoaded):
    global windowREF
    windowREF = mywindow

    print('DOM is ready')
    # Cancel window on_Top
    windowREF.on_top = False

    # Set Head
    dict = {'appname': windowREF.Appname,
            'appver': windowREF.AppVer, 'applogo': windowREF.winlogo}
    jsrunner('wintophandlers', 'innerHTML', "=", htmlread(
        'tophandlers.html').format(**dict), windowREF.targetwindow)

    # set main
    # wait for window to load
    # setState(windowREF.targetwindow, 'currentTab', "ABOUT")
    time.sleep(0.1)
    jsrunner('allmain', 'innerHTML', "=", htmlread(
        'wrap.html'), windowREF.targetwindow)

    jsrunner('winbothandlers', 'innerHTML', "=", htmlread(
        'bothandlers.html'), windowREF.targetwindow)

    # api.startappwindow()

    # unsubscribe event listener
    # webview.windows[0].events.loaded -= on_loaded
    # root.events.loaded -= on_loaded
    # filter lambda function from windowREF.targetwindow.events.loaded list
    windowREF.targetwindow.events.loaded._items.pop()

    print("LOADED_LIST", windowREF.targetwindow.events.loaded._items)

    onLoaded(windowREF)
    # windowREF.targetwindow.events.loaded -= onLoaded
####################################


def setStateJSON(data, key=None):
    global windowREF
    if windowREF == None:
        # print('windowREF is None')
        return

    def convert(o):
        if isinstance(o, np.generic):
            return o.item()
        raise TypeError

    json_string = json.dumps(data, indent=4, default=convert)
    try:
        if windowREF.targetwindow is None or windowREF.targetwindow.evaluate_js is None:
            return

        if key != None:
            result = windowREF.targetwindow.evaluate_js(
                f"""
                setStateJSON({json_string}, '{key}')
                """
            )
        else:
            result = windowREF.targetwindow.evaluate_js(
                f"""
                setStateJSON({json_string})
                """
            )
    except:
        print('fail to setStateJSON')


def setState(key, value):
    global windowREF
    if windowREF == None:
        # print('windowREF is None')
        return
    # print('setState', key, value)
    result = windowREF.targetwindow.evaluate_js(
        f"""
        setState('{key}', '{value}')
        """
    )


def jsrunner(mainid='', doter='', typer="=", valuer='', window=''):
    try:
        dict = {'id': mainid, 'doter': doter, 'valuer': valuer}

        if typer == "=":
            testvar = '''document.getElementById('{id}').{doter} = `{valuer}` '''.format(
                **dict)
        if typer == ".":
            testvar = '''document.getElementById('{id}').{doter}{valuer} '''.format(
                **dict)

        window.evaluate_js(testvar)
    except:
        print('fail to write jsrunner')


def htmlread(filename):
    HTMLFile = open("AppComponents\\HtmlParticles\\"+filename, "r")
    return HTMLFile.read()


class Api ():

    global windowREF

    def __init__(self, context=None):
        super().__init__()

        self.context = context

    def quit(self):
        if windowREF == None:
            return
        windowREF.targetwindow.destroy()
        sys.exit()

    def toggleService(self, key=None, state=None):
        if self.context == None:
            return
        else:
            self.context.toggle_service(key, state)

    def syncState(self, key=None, state=None):
        if self.context == None:
            return
        else:
            self.context.sync_state(key, state)

    def updateSubItemTab(self, tab, direction):
        # print('updateSubItemTab', tab, direction)
        if self.context == None:
            return
        else:
            self.context.sync_state('subItemTabIndex', direction)

    def updateSubItem(self, parentId, subItemId, title, value, type):

        print('updateSubItem', parentId, subItemId, title, value, type)

        if self.context == None:
            return
        else:
            newValue = value
            if type == 'switch':
                if value == 'off':
                    newValue = 'on'
                else:
                    newValue = 'off'
            if type == '-1':
                val = value.split('*')
                min = int(val[1].split('-')[0])
                if (int(val[0]) - 1) > int(min):
                    newValue = int(val[0]) - 1
                else:
                    newValue = int(min)
            if type == '+1':
                val = value.split('*')
                max = int(val[1].split('-')[1])
                if (int(val[0]) + 1) < int(max):
                    newValue = int(val[0]) + 1
                else:
                    newValue = max

            self.context.modify_subitem(parentId, subItemId, title, newValue)
            # self.context.stateTransfer('state', 'showModal', True)

    # allow to reload home page with logo and app name

            # set modal data
    def modaldata(self, modalData=None):
        global windowREF
        datademo = ''' 
        <div class='mt-2'> 
            <h2>Guide Play Beta</h2>  
            <h3 class="p-1">v1.0.1.16</h3> 
            <button
                @click="$store.global.showModal = false"
                class="btn mt-6 bg-success font-medium text-white hover:bg-success-focus focus:bg-success-focus active:bg-success-focus/90">
                Close
            </button>
        </div> 
        '''

        if modalData != None:
            datademo = modalData

        # print("generate modaldata", datademo)

        jsrunner('modalbody', 'innerHTML', "=",
                 datademo, windowREF.targetwindow)

    def refreshhome(self):
        global windowREF
        setState('showModal', True)
        self.modaldata()
        # global windowREF
        # windowREF.targetwindow.events.loaded += lambda: on_loaded(
        #     windowREF, windowREF.targetwindow)

    # Set window app icon and title
    def startappwindow(self):
        global windowREF
        print('Start startappwindow', self.Appname, self.AppVer)
        # Set title
        jsrunner('titleappname', 'innerHTML', "=", self.Appname +
                 ''' v'''+self.AppVer, windowREF.targetwindow)
        # set LOGO
        jsrunner('titleapplogo', 'src', "=",
                 self.winlogo, windowREF.targetwindow)

    # Handle Window Resize
    def resizedrag(self):
        global windowREF
        # utilcode/Frameless.py window is the target object window.
        doresize(windowREF.targetwindow)

    # Top Window Handlers mini / full screen , Exit
    def topbar(self, code):

        if code == "mini":
            windowREF.targetwindow.minimize()
        if code == "full":
            windowREF.targetwindow.toggle_fullscreen()
            # windowREF.targetwindow.move(0, 0)
        if code == "close":
            windowREF.targetwindow.destroy()
            sys.exit()

    # Link to Site Top window Handler
    def bottbar(self):
        print('page link')

    # set modal data

    def notidata(self, data):
        global windowREF
        # Demo .format(**dict) to use python vars into HTML code. you can pass any data to any element
        # our demo image
        myimg = 'images/app-icon.png'
        # img src to dict
        dict = {'myimg': myimg}
        # dict usage with {myimg} to pass our var to html
        jsrunner('msgimg', 'innerHTML', "=",
                 ''' <img
                        class="rounded-full mt-3"
                        src="{myimg}"
                        alt="avatar"
                    /> 
                '''.format(**dict), windowREF.targetwindow)
        jsrunner('msghead', 'innerHTML', "=",
                 ''' <h2 class='pt-1'> Checking </h2> ''', windowREF.targetwindow)
        jsrunner('msgbody', 'innerHTML', "=",
                 ''' <h3 class='pt-1'> </h3>looking for stuff behind you ''', windowREF.targetwindow)
        time.sleep(2.5)
        jsrunner('msghead', 'innerHTML', "=",
                 ''' <h2 class='pt-1'> Done Checking!! </h2> ''', windowREF.targetwindow)
        jsrunner('msgbody', 'innerHTML', "=",
                 ''' <h3 class='pt-1'> Relex, it was just a gaint spider </h3> ''', windowREF.targetwindow)

    # lottie player Demo
    def lottiebtn(self):
        global windowREF

        mydata = '''
                <h2 class="text-center p-1"> lottiefiles  </h2> 
                <p></p>
                <lottie-player id="lopper" src="js/dabar.json"  background="transparent"  speed="1"  style="width: 90%; height: 90%;"  loop  autoplay>
                </lottie-player> 
                '''
        jsrunner('emptydata', 'innerHTML', "=", mydata, windowREF.targetwindow)

    # Loading bar
    def loaderdemo(self):
        global windowREF
        mydata = '''
            <div class="text-center mt-4 gap-2 justify-center flex items-stretch py-2 pt-5" id="updatetext">
            <i>Checking</i>
            <i class="fa-brands fa-github"></i>
            <!-- <i class="fa-solid fa-dragon"></i> -->
            <i>For Client Update</i>
          </div>
         
          <div class="px-8 mt-4 pt-5 ">
            <div class="progress h-5 bg-slate-150 dark:bg-navy-500 ">
              <div
                class="is-active   overflow-hidden rounded-full bg-secondary " id="updatestatus" style="width: 0%"
              ></div>
            </div>
          </div>
        '''
        jsrunner('emptydata', 'innerHTML', "=", mydata, windowREF.targetwindow)
        time.sleep(1)
        jsrunner('updatestatus', 'setAttribute', ".",
                 ('style', 'width:25%'), windowREF.targetwindow)
        time.sleep(0.5)
        jsrunner('updatestatus', 'setAttribute', ".",
                 ('style', 'width:66%'), windowREF.targetwindow)
        time.sleep(1)
        jsrunner('updatestatus', 'setAttribute', ".",
                 ('style', 'width:100%'), windowREF.targetwindow)
        time.sleep(0.5)
        jsrunner('emptydata', 'innerHTML', "=",
                 ''' <h2 class="text-center"> All Done! </h2> ''', windowREF.targetwindow)
        time.sleep(1)
        self.emptydatareset()

    # Reset #emptydata
    def emptydatareset(self):
        global windowREF
        jsrunner('emptydata', 'innerHTML', "=", '', windowREF.targetwindow)
