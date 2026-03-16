from windows_capture import WindowsCapture, Frame, InternalCaptureControl
import data
import cv2
import numpy as np
import time
import os
import threading
from aimPlus import aimPlus
from pipe_radar import RADAR
from pipe_ocr import OCR
from pipe_ocr_score import OCR_SCORE
from pipe_gamestates import GAMESTATES
from pipe_aim_damage import AIM_DAMAGE
from pipe_lifelevel import LIFELEVEL
from pipe_screenreader import SCREENCREADER
from utils import getRelativeCoords

try:
    import dxcam as _dxcam
    _DXCAM_AVAILABLE = True
except ImportError:
    _DXCAM_AVAILABLE = False


class _DXCamControl:
    def __init__(self, stop_event):
        self._stop_event = stop_event

    def stop(self):
        self._stop_event.set()


global last_time
global lastBuffer
global capture

lastBuffer = None
last_time = time.time()
# Called Every Time A New Frame Is Available

# get relative path
DIR_PATH = os.path.dirname(os.path.realpath(__file__))


class fullCaptureWC:
    def __init__(self, parentRef, callback=None, captureRef=None, devMode=False):
        self.lastFrame = None
        self.lastGrayFrame = None
        self.lastThreshFrame = None
        self.lastPlayerFrame = None
        self.lastFullFrame = None
        self.captureControl = None
        self.capture = captureRef
        self.devMode = False
        self.showWindows = False
        self.useThreads = False

        self.callback = callback
        self.checker = None
        self.radarRadius = 0
        self.parentRef = parentRef
        # pipes
        self.pipe_radar = None
        self.pipe_ocr = None
        self.pipe_aim = None
        self.pipe_gamestates = None
        self.pipe_aimplus = None
        self.pipe_lifelevel = None
        self.pipe_screenreader = None
        # deltas
        self.ocr_address_delta = 0
        self.ocr_interval_secs = 6
        self.ocr_last_time = time.time()
        self.ocrService = lambda x: []
        self.ocrServiceLoaded = False
        self.damageClearTimer = None

        self.debugOCR = False
        self.useWriterCache = False
        self.useScoreProcess = True

        self.lastDamageAngle = None

        # round params
        self.roundParams = {
            "lifelevel": 100,
            "damages": [],
            "lastDamageAngle": None,
            "time_left": 0,
            "aliveA": 0,
            "aliveB": 0,
            "team": "ct",
            "roundId": time.time(),
            "lastChange": -1,
        }
        self.gameStateParams = {
            "detail": "home",
            "playerOnRadar": False,
            "pinOnRadar": False,
            "aimaligned": False,
            "name": "home",
            "operation": "",
            "arrowFound": False,
            "radarSpectator": False,
            "teamLogoFound": False,
            "spectatorFound": False,
        }
        # core params
        self.dirname = os.path.dirname(__file__)
        self.damageMask = os.path.join(
            self.dirname, 'assets/masks/damage_sectors_full.png')
        self.trackbarsCreated = False
        self.trackbars = []

        self.croppedLocks = {
            "radar_spectator": False,
            "spectator": False,
            "aim": False,
            "score": False,
            "address": False,
            "teamlogo": False,
            "matchresult": True,
            "lifelevel": False
        }
        # crops coords
        self.cropDicts = [{
            "id": "radar",
            "x": 35,
            "y": 35,
            "x2": 395,
            "y2": 395,
            "frame": None,
            "show": False
        },
            {
            "id": "radar_spectator",
            "x": 7,
            "y": 7,
            "x2": 422,
            "y2": 422,
            "frame": None,
            "show": False
        },
            {
            "id": "aim",
            "x": 800,
            "y": 380,
            "x2": 1120,
            "y2": 700,
            "frame": None,
            "show": False
        },
            {
            "id": "score",
            "x": 854,
            "y": 0,
            "x2": 1066,
            "y2": 74,
            "frame": None,
            "show": False
        },
            {
            "id": "lifelevel",
            "x": 588,
            "y": 1044,
            "x2": 658,
            "y2": 1051,
            "frame": None,
            "show": False
        },
            {
            "id": "address",
            "x": 35,
            "y": 425,
            "x2": 535,
            "y2": 460,
            "frame": None,
            "show": False
        },
            {
            "id": "teamlogo",
            "x": 926,
            "y": 988,
            "x2": 994,
            "y2": 1065,
            "frame": None,
            "show": False
        },
            {
            "id": "matchresult",
            "x": 100,
            "y": 0,
            "x2": 210,
            "y2": 48,
            "frame": None,
            "show": False
        }
        ]

    def on_closed(self):
        print("Capture Session Closed")

    def startCapture(self):
        capture.start()

    def on_frame_arrived(self, frame: Frame, capture_control: InternalCaptureControl):
        global last_time
        global lastBuffer
        # print("New Frame Arrived", frame.width, frame.height)

        # Save The Frame As An Image To The Specified Path
        # frame.save_as_image("lastframe.png")
        # frame.convert_to_bgr().save_as_image("lastframe_bgr.png")

        newframe = frame.convert_to_bgr()

        #
        # show the frame
        lastBuffer = newframe.frame_buffer
        self.processCrops(newframe.frame_buffer, capture_control)
        # resize 50% of the original frame

        # print(image)
        # Gracefully Stop The Capture Thread
        # capture_control.stop()

        # Called When The Capture Item Closes Usually When The Window Closes, Capture
        # Session Will End After This Function Ends

    def defineCapture(self, monitorIndex, primary, monitorsList):

        print("CAPTURE_MONITORS", monitorsList, primary, monitorIndex)
        global capture
        # Every Error From on_closed and on_frame_arrived Will End Up Here
        capture = WindowsCapture(
            capture_cursor=False,
            draw_border=True,
            monitor_index=monitorIndex if monitorIndex is not None else 0,
            window_name=None,
        )
        # define event decorators on_frame_arrived Event Handler
        capture.event(self.on_frame_arrived)
        # on_closed Event Handler
        capture.event(self.on_closed)
        # Start The Capture Thread
        # capture.start()

        # @capture.event

        # @capture.event

        self.capture = capture

        # Detect dxcam device/output as fallback
        self._dxcam_device_idx = None
        self._dxcam_output_idx = None
        if _DXCAM_AVAILABLE and primary is not None:
            try:
                target_w, target_h = (int(x) for x in primary[1].split('x'))
                found = False
                for dev_idx in range(4):
                    if found:
                        break
                    for out_idx in range(4):
                        try:
                            cam = _dxcam.create(device_idx=dev_idx, output_idx=out_idx, output_color="BGR")
                            frame = cam.grab()
                            cam.release()
                            del cam
                            if frame is not None and frame.shape[1] == target_w and frame.shape[0] == target_h:
                                self._dxcam_device_idx = dev_idx
                                self._dxcam_output_idx = out_idx
                                found = True
                                print(f"DXCAM_DEVICE device={dev_idx} output={out_idx} res={target_w}x{target_h}")
                                break
                        except Exception:
                            break
                if not found:
                    print("DXCAM_DEVICE not found, dxcam fallback unavailable")
            except Exception as e:
                print("defineCapture_dxcam_error", e)

    def loadOCRReader(self):
        if self.ocrServiceLoaded == True:
            return
        self.ocrServiceLoaded = True
        # load ocr reader
        from ocrTools import ReadCLI

        modelPath = os.path.join(DIR_PATH, "ocr_wrapper", "model")
        cliApp = os.path.join(DIR_PATH, "ocr_wrapper",
                              "guide-play-services-ocr.exe")
        self.ocrService = ReadCLI(
            ""+cliApp+" --path "+modelPath+"", modelPath, True)

        self.ocrService.start()
        self.ocrService.setLiveness()

        self.pipe_ocr = OCR(self.callbackTransfer,
                            self.devMode, self.ocrService)
        self.pipe_ocr_score = OCR_SCORE(
            self.callbackTransfer, self.devMode, self.ocrService)
        self.pipe_gamestates = GAMESTATES(
            self.callbackTransfer, self.devMode, self.ocrService)

    def startCapturePipes(self, callback, devMode=False):
        self.callback = callback
        self.devMode = devMode
        self.pipe_radar = RADAR(self.callbackTransfer, devMode)
        self.pipe_aim = AIM_DAMAGE(self.callbackTransfer, devMode)
        self.pipe_lifelevel = LIFELEVEL(self.callbackTransfer, devMode)
        self.pipe_screenreader = SCREENCREADER(
            self, self.callbackTransfer, devMode, self.ocrService)
        self.pipe_ocr = OCR(self.callbackTransfer, devMode, self.ocrService)
        self.pipe_ocr_score = OCR_SCORE(
            self.callbackTransfer, devMode, self.ocrService)
        self.pipe_gamestates = GAMESTATES(
            self.callbackTransfer, devMode, self.ocrService)
        self.pipe_aimplus = aimPlus(True, self, self.callbackTransfer, devMode)

    def resetRoundParams(self, param):

        if self.roundParams["lastChange"] != self.roundParams["roundId"]:

            print("resetRoundParams", param)

            updateTime = time.time()

            self.roundParams = {
                "lifelevel": 100,
                "damages": [],
                "lastDamageAngle": None,
                "time_left": 0,
                "aliveA": 0,
                "aliveB": 0,
                "team": "nf",
                "roundId": updateTime,
                "lastChange": updateTime,
            }

        else:
            print("resetRoundParams", "lastChange == roundId")

    def clearDamages(self):
        self.roundParams["damages"] = []
        self.roundParams["lastDamageAngle"] = None
        self.roundParams["lastChange"] = time.time()
        self.damageClearTimer = None
        self.lastDamageAngle = None

    def updateDamages(self, damages=[]):

        # filter only new damages
        incomingDamages = [
            x for x in damages if x not in self.roundParams["damages"]]
        # append incoming damages to newDamages
        newDamages = self.roundParams["damages"] + incomingDamages
        # filter only damages in last 3 seconds
        newDamages = [x for x in newDamages if (
            time.time() * 1000) - x < 3000]

        self.roundParams["damages"] = newDamages
        self.roundParams["lastDamageAngle"] = self.lastDamageAngle
        self.roundParams["lastChange"] = time.time()

        if self.damageClearTimer is not None:
            self.damageClearTimer.cancel()
        self.damageClearTimer = threading.Timer(
            0.3, self.clearDamages, args=[])

    def callbackTransfer(self, *data):
        if data[0] == "/aim_cross":
            # todo - (Green Percent AIM) another evidence for round playing
            return
        if data[0] == "/aim_damage":
            if self.gameStateParams["playerOnRadar"] == True and self.gameStateParams["pinOnRadar"]:
                self.lastDamageAngle = data[1]
                self.callback(*data)
            return
        if data[0] == "/aim":
            if self.gameStateParams["playerOnRadar"] == True and self.gameStateParams["pinOnRadar"]:
                self.callback(*data)
            return
        if data[0] == "/aimplus":
            if self.gameStateParams["aimaligned"] == True and self.gameStateParams["playerOnRadar"] == True and self.gameStateParams["pinOnRadar"]:
                self.callback(*data)
            return

        if data[0] == "/aimaligned":
            if self.gameStateParams["playerOnRadar"] == True and self.gameStateParams["pinOnRadar"]:
                self.gameStateParams["aimaligned"] = data[1]
            return

        if data[0] == "/roundscores":
            if self.gameStateParams["playerOnRadar"] == True and self.gameStateParams["pinOnRadar"]:
                self.roundParams["aliveA"] = data[1]["aliveA"]
                self.roundParams["aliveB"] = data[1]["aliveB"]
                self.roundParams["scoreA"] = data[1]["scoreA"]
                self.roundParams["scoreB"] = data[1]["scoreB"]
                self.roundParams["time_left"] = data[1]["clock"]
                self.roundParams["lastChange"] = time.time()
                self.callback(
                    "/roundstate", self.roundParams["roundId"], self.roundParams)
                return
        if data[0] == "/lifelevel":
            if self.gameStateParams["playerOnRadar"] == True and self.gameStateParams["pinOnRadar"]:
                if self.roundParams["lifelevel"] != data[1]["lifelevel"]:
                    if data[1]["lifelevel"] < 100 and data[1]["lifelevel"] < self.roundParams["lifelevel"]:
                        self.roundParams["lifelevel"] = data[1]["lifelevel"]
                        self.roundParams["lastChange"] = time.time()
                        self.updateDamages(data[1]["damages"])
                        if data[1]["lifelevel"] < 1:
                            self.resetRoundParams(
                                "lifelevel__"+str(data[1]["lifelevel"])+"")
                        self.callback(
                            "/roundstate", self.roundParams["roundId"], self.roundParams)
            return

        if data[0] == "/obstacles":
            if self.gameStateParams["playerOnRadar"] == True and self.gameStateParams["pinOnRadar"]:
                self.callback(*data)
            return

        if data[0] == "/trackeds":
            print("[CAPTURE_DEBUG] /trackeds count:", len(data[1]) if len(data)>1 else '?', "playerOnRadar:", self.gameStateParams["playerOnRadar"], "pinOnRadar:", self.gameStateParams["pinOnRadar"])
            if self.gameStateParams["playerOnRadar"] == True and self.gameStateParams["pinOnRadar"]:
                self.callback(*data)
            return

        if data[0] == "/cardinal":
            if self.gameStateParams["playerOnRadar"] == True and self.gameStateParams["pinOnRadar"]:
                if self.gameStateParams["name"] != "gameplay":
                    # self.callback("/cardinal", "not in game", {})
                    print("callbackTransfer ----- ", "not in game")
                else:
                    self.callback(*data)
            return
        if data[0] == "/aimpolar":
            return
        if data[0] == "/pin-radar":
            self.gameStateParams["pinOnRadar"] = data[1]
            return
        if data[0] == "/player-radar":
            self.gameStateParams["playerOnRadar"] = data[1]
            return
        if data[0] == "/gamestate":

            if data[1] == "spectator" or data[1] == "home":
                self.resetRoundParams("gamestate")

            # gamestate params
            self.gameStateParams["name"] = data[1]
            self.gameStateParams["operation"] = data[2]["operation"]
            self.gameStateParams["detail"] = data[2]["detail"]
            self.gameStateParams["arrowFound"] = data[2]["arrowFound"]
            self.gameStateParams["radarSpectator"] = data[2]["radarSpectator"]
            self.gameStateParams["teamLogoFound"] = data[2]["teamSide"]
            self.gameStateParams["spectatorFound"] = data[2]["spectatorFound"]
            self.callback(
                "/gamestate", self.gameStateParams["name"], self.gameStateParams)
            # round params
            self.roundParams["team"] = data[2]["teamSide"]
            self.roundParams["lastChange"] = time.time()
            self.callback(
                "/roundstate", self.roundParams["roundId"], self.roundParams)
            return
        print("callbackTransfer ----- ", data[0])
        self.callback(*data)

    def stopRawCapture(self):
        if self.captureControl is not None:
            print("stopRawCapture_stopping")
            self.captureControl.stop()
        else:
            print("stopRawCapture_captureControl is None")

    def _startDXCamCapture(self):
        print("startRawCapture_dxcam_starting device={} output={}".format(
            self._dxcam_device_idx, self._dxcam_output_idx))

        # Release any previous singleton instance
        if getattr(self, '_dxcam_camera_instance', None) is not None:
            try:
                del self._dxcam_camera_instance
            except Exception:
                pass
            self._dxcam_camera_instance = None

        camera = _dxcam.create(
            device_idx=self._dxcam_device_idx,
            output_idx=self._dxcam_output_idx,
            output_color="BGR"
        )
        self._dxcam_camera_instance = camera

        stop_event = threading.Event()
        control = _DXCamControl(stop_event)
        self.captureControl = control

        def capture_loop():
            while not stop_event.is_set() and data.runCV:
                try:
                    frame = camera.grab()
                    if frame is not None:
                        self.processCrops(frame, control)
                    else:
                        time.sleep(0.001)
                except Exception as e:
                    print("dxcam_frame_error", e)
                    if stop_event.is_set():
                        break
                    time.sleep(0.033)
            try:
                del self._dxcam_camera_instance
                self._dxcam_camera_instance = None
            except Exception:
                pass
            print("dxcam_capture_stopped")

        t = threading.Thread(target=capture_loop, daemon=True, name="dxcam-capture")
        t.start()

    def startRawCapture(self, checker, devMode=False):
        print("startRawCapture_starting", checker, devMode)
        self.checker = checker
        self.devMode = devMode
        self.loadOCRReader()
        try:
            self.capture.start()
            if self.parentRef is not None:
                self.parentRef.captureFailCount = 0
                if getattr(self.parentRef, "parentRef", None) is not None:
                    self.parentRef.parentRef.captureFailCount = 0
        except Exception as e:
            print("startRawCapture_error", e)
            if _DXCAM_AVAILABLE and self._dxcam_device_idx is not None:
                try:
                    self._startDXCamCapture()
                    if self.parentRef is not None:
                        self.parentRef.captureFailCount = 0
                        if getattr(self.parentRef, "parentRef", None) is not None:
                            self.parentRef.parentRef.captureFailCount = 0
                    return
                except Exception as e2:
                    print("startRawCapture_dxcam_error", e2)
            data.runCV = False
            if self.parentRef is not None:
                self.parentRef.captureFailCount += 1
                if getattr(self.parentRef, "parentRef", None) is not None:
                    self.parentRef.parentRef.captureFailCount = self.parentRef.captureFailCount
                if self.parentRef.captureFailCount >= 3:
                    self.parentRef.captureRetryBlockedUntil = time.time() + 30
                    if getattr(self.parentRef, "parentRef", None) is not None:
                        self.parentRef.parentRef.captureRetryBlockedUntil = self.parentRef.captureRetryBlockedUntil
                        self.parentRef.parentRef.captureDisabled = True
                    print(
                        "startRawCapture_backoff", self.parentRef.captureFailCount, "retry_in_secs", 30)

    def updateProp(self, windowName, prop, value):

        print("updateProp", windowName, prop, value)

        if cv2.getWindowProperty(windowName, cv2.WND_PROP_VISIBLE):
            cv2.setTrackbarPos(prop, windowName, value)

        if windowName == "aimparams":
            self.pipe_aim[prop] = value

        if windowName == "radarsquare":
            self.pipe_gamestates[prop] = value

        if windowName == "sr_params":
            self.pipe_gamestates[prop] = value

        if windowName == "screenreader":
            self.pipe_screenreader[prop] = value

        if windowName == "radar":
            self.pipe_radar[prop] = int(value)

        if windowName == "radar_float":
            self.pipe_radar[prop] = float(value*0.1)

        if windowName == "polarThresh1":
            self.pipe_radar[prop] = value

        if windowName == "gs_team":
            self.pipe_gamestates[prop] = value

        if windowName == "floorRadar":
            if prop == "add":
                self.pipe_radar.floorRanges.append(
                    value
                )
            if prop == "remove":
                self.pipe_radar.floorRanges.remove(
                    value
                )
            if prop == "reset":
                self.pipe_radar.floorRanges = []
                self.pipe_radar.floorRanges.append(
                    value
                )
            if prop == "test":
                self.pipe_radar.floorRangesTest = []
                self.pipe_radar.floorRangesTest.append(
                    value
                )

    def createTrackbars(self, windowName, name, size=255):

        if self.devMode == False:
            return
        # if not exist create window
        if not cv2.getWindowProperty(windowName, cv2.WND_PROP_VISIBLE):
            cv2.namedWindow(windowName)
            self.trackbars.append(windowName)
        cv2.resizeWindow(windowName, 400, 300)
        cv2.createTrackbar(name, windowName, 0, size,
                           lambda x: self.updateProp(windowName, prop=name, value=x))
        # on key press y save values
        if cv2.waitKey(1) & 0xFF == ord("y"):
            # iterate self.trackbars and save values
            valuesTXT = ""
            for trackbar in self.trackbars:
                for name in self.trackbars:
                    value = cv2.getTrackbarPos(name, trackbar)
                    valuesTXT += name + " " + str(value) + "\n"
            print("SAVING ===================== valuesTXT", valuesTXT)
            with open('trackbars.txt', 'w') as f:
                f.write(valuesTXT)

        # wait for key and destroy all windows
        if cv2.waitKey(1) & 0xFF == ord("q"):
            cv2.destroyAllWindows()
            return

    def pipelineFrame(self, frame, croppeds):

        # IF ROUND NOT RUNNING PROCESS SCREEN READERS

        if self.checker is not None and self.checker("roundRunning") == False:
            # process screenreader full screen

            if self.checker("isHomeScreen") == True:
                # print("processScreenReader", "isHomeScreen")
                self.pipe_screenreader.processScreenReader(frame)

            # GAME STATE FULL SCREEN DETECTOR
            self.pipe_gamestates.processGamestates(
                frame, [], self)

            # reset radar frames
            # self.pipe_radar.last_frame_full = None
            # self.pipe_radar.last_frame_radar = None

        # IF ROUND RUNNING PROCESS GAME SCREEN READERS

        else:

            # RADAR PIPE
            # find radar dict by id
            radarCrops = next(
                (item for item in croppeds if item["id"] == "radar"), None)

            aimCrops = next(
                (item for item in croppeds if item["id"] == "aim"), None)

            if radarCrops is not None and radarCrops["frame"] is not None:
                # print("radarCrops", radarCrops["frame"].shape)
                # self.pipe_radar.last_frame_full = frame
                # self.pipe_radar.last_frame_radar = radarCrops["frame"]

                self.pipe_radar.processRadar(
                    radarCrops["frame"], frame, self)

            if self.devMode == True and self.useThreads == False:
                self.processCroppeds(frame.copy(), croppeds)
                if self.gameStateParams["name"] == "gameplay":
                    self.pipe_aimplus.processFrame(
                        aimCrops["frame"], frame)
            else:
                croppedsT = threading.Thread(target=self.processCroppeds, args=[
                    frame.copy(), croppeds], name="croppedsT", daemon=True)
                croppedsT.start()

                if aimCrops is not None and aimCrops["frame"] is not None:
                    # print("aimCrops", aimCrops["frame"].shape)
                    if self.gameStateParams["name"] == "gameplay":
                        aimPlusT = threading.Thread(target=self.pipe_aimplus.processFrame, args=[
                            aimCrops["frame"], frame], name="aimPlus", daemon=True)
                        aimPlusT.start()

    def processCroppeds(self, frame, croppeds):
        # print("\n\n ---- PIPELINE -----  processCroppeds", len(croppeds))

        # iterate croppeds
        monitoring = []
        for cropDict in croppeds:
            # print("cropDict", cropDict["id"], cropDict["frame"].shape)
            if cropDict["frame"] is not None:
                # show cropif self.gameStateParams["name"] == "gameplay":
                # cropDict["show"] == True and
                if self.devMode == True and self.showWindows == False:
                    cv2.imshow(cropDict["id"], cropDict["frame"])

                # OCR SCORE
                if cropDict["id"] == "score" and self.gameStateParams["playerOnRadar"] == True and self.gameStateParams["pinOnRadar"]:
                    if self.gameStateParams["name"] == "gameplay":
                        if self.croppedLocks["score"] == False:
                            if self.debugOCR == False and self.useScoreProcess:
                                self.pipe_ocr_score.processScore(
                                    cropDict["frame"], frame)

                # OCR ADDRESS
                ocrServiceStatus = self.parentRef.serverCallback(
                    "/getconfig", "ScreenReader", "InGameSectorVoice")

                if ocrServiceStatus["value"] == "on":
                    if cropDict["id"] == "address" and self.gameStateParams["playerOnRadar"] == True and self.gameStateParams["pinOnRadar"]:
                        if self.gameStateParams["name"] == "gameplay":
                            if self.croppedLocks["address"] == False:
                                if self.debugOCR == False:
                                    if self.useWriterCache == True and (time.time() - self.ocr_last_time) > self.ocr_interval_secs / 2:
                                        t = threading.Thread(target=self.pipe_ocr.writeCache, args=[
                                            cropDict["frame"]], name="ocrWriteThread")
                                        t.start()

                                    if (time.time() - self.ocr_last_time) > self.ocr_interval_secs:
                                        self.ocr_last_time = time.time()
                                        t = threading.Thread(target=self.pipe_ocr.processText, args=[
                                            cropDict["frame"], cropDict["frame"]], name="ocrThread")
                                        t.start()
                                        self.ocr_address_delta = 0
                                    else:
                                        self.ocr_address_delta += 1
                                        print("startRawCapture-ocr-delta",
                                              self.ocr_address_delta)

                # AIM
                if cropDict["id"] == "aim" and self.gameStateParams["playerOnRadar"] == True and self.gameStateParams["pinOnRadar"]:
                    if self.gameStateParams["name"] == "gameplay":
                        if self.croppedLocks["aim"] == False:
                            # AIM GREEN RED DAMAGE
                            self.pipe_aim.processAim(
                                cropDict["frame"], frame, self.damageMask)
                            # # AIM PLUS PIPE
                            # self.pipe_aimplus.processFrame(
                            #     cropDict["frame"], frame)

                # LIFELEVEL
                if cropDict["id"] == "lifelevel" and self.gameStateParams["playerOnRadar"] == True and self.gameStateParams["pinOnRadar"]:
                    if self.gameStateParams["name"] == "gameplay":
                        if self.croppedLocks["lifelevel"] == False:
                            self.pipe_lifelevel.processLifelevel(
                                cropDict["frame"], frame)

                # GAME STATE MONITORING
                # search for deterministic evidence of round running

                # arrow north == True
                # radar square == True
                # Team logo == True
                # spectator message

                # TEAM LOGO
                if cropDict["id"] == "teamlogo" and self.gameStateParams["playerOnRadar"] == True and self.gameStateParams["pinOnRadar"]:
                    if self.gameStateParams["name"] == "gameplay":
                        if self.croppedLocks["teamlogo"] == False:
                            monitoring.append(cropDict)

                # RADAR SPECTATOR
                if cropDict["id"] == "radar_spectator":
                    if self.gameStateParams["name"] == "gameplay":
                        if self.croppedLocks["radar_spectator"] == False:
                            monitoring.append(cropDict)

                # MATCH RESULT
                if cropDict["id"] == "matchresult" and self.gameStateParams["name"] == "gameplay":
                    if self.croppedLocks["matchresult"] == False:
                        monitoring.append(cropDict)

        # GAME STATE FULL SCREEN DETECTOR
        try:
            self.pipe_gamestates.processGamestates(
                frame, monitoring, self)
        except Exception as e:
            print("error processing gamestates", e)

        return

        # OCR SCORE
        # find score dict by id
        if self.gameStateParams["playerOnRadar"] == True and self.gameStateParams["pinOnRadar"]:
            if self.gameStateParams["name"] == "gameplay":
                if self.croppedLocks["score"] == False:
                    scoreCrops = next(
                        (item for item in croppeds if item["id"] == "score"), None)

                    if self.debugOCR == False and self.useScoreProcess:
                        if scoreCrops is not None and scoreCrops["frame"] is not None:
                            self.pipe_ocr_score.processScore(
                                scoreCrops["frame"], frame)

                if self.debugOCR == False:
                    ocrServiceStatus = self.parentRef.serverCallback(
                        "/getconfig", "ScreenReader", "InGameSectorVoice")

                    if ocrServiceStatus["value"] == "on":

                        if self.croppedLocks["address"] == False:
                            # OCR ADDRESS
                            # find address dict by id
                            addressCrops = next(
                                (item for item in croppeds if item["id"] == "address"), None)

                            if addressCrops is not None and addressCrops["frame"] is not None:

                                self.ocr_address_delta += 1

                                print("startRawCapture-ocr-delta",
                                      self.ocr_address_delta)

                                if self.useWriterCache == True and (time.time() - self.ocr_last_time) > self.ocr_interval_secs / 2:

                                    print("startRawCapture-ocr-writting",
                                          self.ocr_address_delta, time.time())
                                    t = threading.Thread(target=self.pipe_ocr.writeCache, args=[
                                        addressCrops["frame"]], name="ocrWriteThread")
                                    t.start()

                                if (time.time() - self.ocr_last_time) > self.ocr_interval_secs:

                                    self.ocr_address_delta = 0
                                    self.ocr_last_time = time.time()

                                    print("startRawCapture-ocr-starting",
                                          self.ocr_address_delta, self.ocr_last_time)

                                    t = threading.Thread(target=self.pipe_ocr.processText, args=[
                                        addressCrops["frame"], addressCrops["frame"]], name="ocrThread")
                                    t.start()
                                    print("startRawCapture-ocr-running")

                if self.croppedLocks["aim"] == False:
                    # AIM
                    # find aim dict by id
                    aimCrops = next(
                        (item for item in croppeds if item["id"] == "aim"), None)

                    if aimCrops is not None and aimCrops["frame"] is not None:
                        # print("aimCrops", aimCrops["frame"].shape)

                        # AIM PLUS PIPE

                        # if self.devMode == True and self.useThreads == False:
                        self.pipe_aimplus.processFrame(
                            aimCrops["frame"], frame)

                        self.pipe_aim.processAim(
                            aimCrops["frame"], frame, self.damageMask)

                if self.croppedLocks["lifelevel"] == False:
                    # LIFELEVEL
                    # find lifelevel dict by id
                    lifelevelCrops = next(
                        (item for item in croppeds if item["id"] == "lifelevel"), None)

                    if lifelevelCrops is not None and lifelevelCrops["frame"] is not None:
                        # print("aimCrops", aimCrops["frame"].shape)
                        self.pipe_lifelevel.processLifelevel(
                            lifelevelCrops["frame"], frame)

        # GAME STATE MONITORING
            # search for deterministic evidence of round running

            # arrow north == True
            # radar square == True
            # Team logo == True
            # spectator message

        monitoring = []

        # TEAM LOGO
        # find teamlogo dict by id
        if self.gameStateParams["playerOnRadar"] == True and self.gameStateParams["pinOnRadar"]:
            if self.gameStateParams["name"] == "gameplay":
                teamlogoCrops = next(
                    (item for item in croppeds if item["id"] == "teamlogo"), None)

                if teamlogoCrops is not None and self.croppedLocks["teamlogo"] == False:
                    monitoring.append(teamlogoCrops)

        # RADAR SPECTATOR
        # find radar dict by id
        radarSpectatorCrops = next(
            (item for item in croppeds if item["id"] == "radar_spectator"), None)

        if radarSpectatorCrops is not None and self.croppedLocks["radar_spectator"] == False:
            monitoring.append(radarSpectatorCrops)

        # MATCH RESULT
        # find matchresult dict by id
        if self.gameStateParams["name"] == "gameplay":
            matchresultCrops = next(
                (item for item in croppeds if item["id"] == "matchresult"), None)
            if matchresultCrops is not None and self.croppedLocks["matchresult"] == False:
                monitoring.append(matchresultCrops)

        # GAME STATE FULL SCREEN DETECTOR
        try:
            self.pipe_gamestates.processGamestates(
                frame, monitoring, self)
        except Exception as e:
            print("error processing gamestates", e)

    def processCrops(self, frame, capture_control):
        self.captureControl = capture_control
        global last_time
        current_time = time.time()
        fps = 1 / (current_time - last_time)
        # print("FPS: ", fps)
        #       newframe.height, newframe.frame_buffer.shape)
        last_time = current_time

        # iterate through cropDicts
        for cropDict in self.cropDicts:

            pixelCoords = getRelativeCoords(
                [cropDict["x"], cropDict["y"], cropDict["x2"], cropDict["y2"]], frame.shape[1], frame.shape[0])

            frameCropped = frame[pixelCoords[0][1]:pixelCoords[1]
                                 [1], pixelCoords[0][0]:pixelCoords[1][0]]

            # set dict frame
            cropDict["frame"] = frameCropped
            # show crop
            # if cropDict["show"] == True and self.devMode == True:
            # cv2.imshow(cropDict["id"], frameCropped)

        self.pipelineFrame(frame, self.cropDicts)

        if self.trackbarsCreated == False:
            # self.createTrackbars('radar', 'h_polarRadar', 180)
            # self.createTrackbars('radar', 's_polarRadar')
            # self.createTrackbars('radar', 'v_polarRadar')
            # self.createTrackbars('radar', 'h2_polarRadar', 180)
            # self.createTrackbars('radar', 's2_polarRadar')
            # self.createTrackbars('radar', 'v2_polarRadarradar

            # self.createTrackbars('sr_params', 'medianBlur', 255)
            # self.createTrackbars('polarThresh1', 'polarFloorthreshParam1', 255)
            # self.createTrackbars('polarThresh1', 'polarFloorthreshParam2', 255)
            # self.createTrackbars('polarThresh1', 'polarContrast', 3)
            # self.createTrackbars('polarThresh1', 'polarBrightness', 100)

            # self.createTrackbars('gs_team', 'teamSideThresholdParam1', 255)
            # self.createTrackbars('gs_team', 'teamSideThresholdParam2', 255)

            # self.createTrackbars('radar', 'floorTolerance', 300)
            # self.createTrackbars('radar_float', '_alpha1', 100)
            # self.createTrackbars('radar_float', '_alpha2', 100)
            # self.createTrackbars('radar_float', '_beta1', 100)

            self.trackbarsCreated = True

        if cv2.waitKey(1) & 0xFF == ord("q") and self.devMode == True:
            capture_control.stop()
            cv2.destroyAllWindows()
            return


cvFullCapture = fullCaptureWC(
    None, callback=None, captureRef=None, devMode=False)
