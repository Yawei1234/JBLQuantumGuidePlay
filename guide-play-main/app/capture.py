from mss import mss
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import scipy.signal as ss
import data
import time
import cv2
from pipe_radar import RADAR
from ocr import OCR
from pipe_gamestates import GAMESTATES
import threading
import gc
import pyautogui
import sys
import logging

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                    level=logging.DEBUG,
                    stream=sys.stdout)


# radar.createTrackbars('threshold_polar')
# radar.createTrackbars('blur_polar')
# radar.createTrackbars('dilate_polar')
# radar.createTrackbars('erode_polar')

# radar.createTrackbars('polarFov', 300)
# radar.createTrackbars('cannyParam1_polar', 500)
# radar.createTrackbars('cannyParam2_polar', 500)

# radar.createTrackbars('h')
# radar.createTrackbars('s')
# radar.createTrackbars('v')
# radar.createTrackbars('h2')
# radar.createTrackbars('s2')
# radar.createTrackbars('v2')

# radar.createTrackbars('threshold_formask', 300)
# radar.createTrackbars('blur_polar_mask')


class cvFullCaptureLegacy ():
    def __init__(self, parentRef, callback=None):
        self.lastFrame = None
        self.lastGrayFrame = None
        self.lastThreshFrame = None
        self.lastPlayerFrame = None
        self.lastFullFrame = None
        self.selected = data.resolutions[data.monitorSelected]
        self.callback = callback
        self.parentRef = parentRef
        self.radar = RADAR(self.callback)
        self.ocr = OCR(self.callback)
        self.gamestates = GAMESTATES(self.callback)
        self.radarRadius = 0

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, item, value):
        return setattr(self, item, value)

    def getPercent(self, ref, value):
        return int((value / ref))

    def startRawCapture(self, checker, devMode=False):

        sct = mss()

        # print("monitors_resolutions", data.resolutions)
        # print("monitors", data.monitors)

        useWindowCapture = False
        w, h = 1920, 1080
        m0 = sct.monitors[0]

        if self.selected is not None:

            t = int(self.selected[0])
            l = int(self.selected[1])
            width = int(self.selected[2])
            height = int(self.selected[3])

            monitor = {'top': t, 'left': l, 'width': width, 'height': height}

            # useWindowCapture = True
        else:
            width = w
            height = h
            monitor = {'top': 0, 'left': 0, 'width': w, 'height': h}

        print("\n *** starting on monitor", monitor)

        # radar absolute values
        radarCropX = 35
        radarCropY = 35
        radarCropW = 395
        radarCropH = 395

        # radar relative values (percent of monitor)
        radarCropXpercet = self.getPercent(w, radarCropX)
        radarCropYpercet = self.getPercent(h, radarCropY)
        radarCropWpercet = self.getPercent(w, radarCropW)
        radarCropHpercet = self.getPercent(h, radarCropH)

        # address absolute values
        addressCropX = 35
        addressCropY = 425
        addressCropW = 535
        addressCropH = 460

        # address relative values (percent of monitor)
        addressCropXpercet = self.getPercent(w, addressCropX)
        addressCropYpercet = self.getPercent(h, addressCropY)
        addressCropWpercet = self.getPercent(w, addressCropW)
        addressCropHpercet = self.getPercent(h, addressCropH)

        self.radarRadius = int(radarCropW / 2)

        data.captureRunning = True

        delta = 0
        lastOCR_TIME = time.time()
        lastGAMESTATE_TIME = time.time()
        every_x_seconds = 1

        while data.runCV == True:

            # print("startRawCapture-frame", delta)

            if data.captureRunning == False:
                # print('startRawCapture-capture stopped 3')
                cv2.destroyAllWindows()
                break

            img = Image.frombytes('RGB', (w, h), sct.grab(monitor).rgb)

            cropAddress = img.crop(
                (addressCropX, addressCropY, addressCropW, addressCropH))

            # crop radar
            cropRadar = img.crop(
                (radarCropX, radarCropY, radarCropW, radarCropH))

            lastFrameAddress = cv2.cvtColor(
                np.array(cropAddress), cv2.COLOR_RGB2BGR)

            # convert to bgr
            lastFrameRadar = cv2.cvtColor(
                np.array(cropRadar), cv2.COLOR_RGB2BGR)
            lastFrameFull = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

            delta += 1

            if data.runCVRadar == True and checker is not None:
                if checker("roundRunning") == True:
                    self.radar.processFrame(
                        lastFrameRadar, lastFrameFull, devMode)
                else:
                    print("startRawCapture-game not running")
                    # if self.radar.lastRadarPlot is not None:
                    #     if devMode == True:

                    # cv2.imshow('radarPlot', self.radar.lastRadarPlot)

            # get fps from opencv

            # print fps

            # SCREEN READING PROCESSES
            # EVERY X SECONDS

            # OCR EVERY 1 SECOND

            if (time.time() - lastOCR_TIME) > every_x_seconds:

                ocrServiceStatus = self.parentRef.serverCallback(
                    "/getconfig", "ScreenReader", "InGameSectorVoice")

                if ocrServiceStatus["value"] == "on":

                    if checker is not None:
                        if checker("roundRunning") == True:
                            delta = 0
                            lastOCR_TIME = time.time()

                            t = threading.Thread(target=self.ocr.processText, args=[
                                lastFrameAddress, cropAddress], name="ocrThread")
                            t.start()
                            print("startRawCapture-ocr running")

            # GAMESTATE EVERY 1 SECOND
            if (time.time() - lastGAMESTATE_TIME) > 0.5:

                delta = 0
                lastGAMESTATE_TIME = time.time()

                t = threading.Thread(target=self.gamestates.getGameState, args=[
                    lastFrameFull], name="gameStateThread")
                t.start()
                print("startRawCapture-getting-gamestate")

            # print("startRawCapture-frame-end", delta)

            gc.collect()

            # SHOW WINDOWS

            # if self.radar.lastFrame is not None:
            #     cv2.imshow('radarCrop', self.radar.lastFrame)

            # if self.radar.lastGrayFrame is not None:
            #     cv2.imshow('radarCropGray', self.radar.lastGrayFrame)

            # if self.radar.lastThreshFrame is not None:
            #     cv2.imshow('radarCropThresh', self.radar.lastThreshFrame)

            # if self.radar.lastPlayerFrame is not None:
            #     cv2.imshow('radarCropPlayer', self.radar.lastPlayerFrame)

            # DESTROY WINDOWS

            if cv2.waitKey(25) & 0xFF == ord('q'):
                data.captureRunning = False
                cv2.destroyAllWindows()
                break
            # When everything done, release the capture
            if data.captureRunning == False:
                print('capture stopped 1')
                cv2.destroyAllWindows()
                break
        else:
            print('capture stopped 2')
            cv2.destroyAllWindows()
