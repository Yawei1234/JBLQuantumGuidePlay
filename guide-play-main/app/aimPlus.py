import sys
import time
import timeit
from termcolor import colored
from math import atan2, cos, sin, sqrt, radians, pi
# from utils.grab import screen
import cv2
# import imutils
# import mss
# import _thread
# import ctypes
import os
# import signal
import numpy as np
# import pynput
# import keyboard
from pynput.mouse import Listener
# import winsound
# sct = mss.mss()
# Wd, Hd = sct.monitors[1]["width"], sct.monitors[1]["height"]
# SendInput = ctypes.windll.user32.SendInput

Wd, Hd = 320, 320  # screen width and height
# relative path
DIRNAME = os.path.dirname(__file__)


class aimPlus:

    def __init__(self, enablePoint=True, parentRef=None, callback=None, devMode=False):
        self.enablePoint = enablePoint

        self.parentRef = parentRef
        self.devMode = devMode
        self.send = callback

        self.YOLO_DIRECTORY = os.path.join(
            DIRNAME, "models")  # yolo model path
        self.CONFIDENCE = 0.36
        self.THRESHOLD = 0.22

        self.aimPointer_paused = True  # make aimPointer off on startup

        self.GREEN = '\033[92m'  # dont touch it
        self.RED = '\033[91m'  # dont touch it
        self.RESET = '\033[0m'  # dont touch it

        # box in the center of your screen, lower value of pixel makes the capture faster, for example 250 mean 250x250 pixel box.
        self.ACTIVATION_RANGE = 320

        self.labelsPath = os.path.sep.join(
            [self.YOLO_DIRECTORY, "coco-dataset.labels"])
        self.LABELS = open(self.labelsPath).read().strip().split("\n")
        np.random.seed(42)
        self.COLORS = np.random.randint(0, 255, size=(len(self.LABELS), 3),
                                        dtype="uint8")

        self.weightsPath = os.path.sep.join(
            [self.YOLO_DIRECTORY, "yolov3-tiny.weights"])  # yolo path weights
        self.configPath = os.path.sep.join(
            [self.YOLO_DIRECTORY, "yolov3-tiny.cfg"])  # yolo path models
        time.sleep(0.4)

        print("\033[1;36m[Status] loading objects detector..")
        self.net = cv2.dnn.readNetFromDarknet(
            self.configPath, self.weightsPath)  # load objects detector

        # check if cpu and gpu cuda is working or disable.
        build_info = str("".join(cv2.getBuildInformation().split()))
        if cv2.ocl.haveOpenCL():
            cv2.ocl.setUseOpenCL(True)
            cv2.ocl.useOpenCL()
            print(colored("[CPU] OpenCL is enabled..", "green"))
        else:
            print(
                colored("[WARNING-CPU] OpenCL is disabled..", "yellow"))
        if "CUDA:YES" in build_info:
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
            print(colored("[GPU] CUDA is enabled..", "green"))
        else:
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            print(
                colored("[WARNING-GPU] CUDA is disabled..", "yellow"))

        self.ln = self.net.getLayerNames()
        self.ln = [self.ln[i - 1] for i in self.net.getUnconnectedOutLayers()]

        print("\033[1;36m[Status] Define screen capture area..")
        self.W = None
        self.H = None
        self.origbox = (int(Wd/2 - self.ACTIVATION_RANGE/2),  # gui box capture
                        int(Hd/2 - self.ACTIVATION_RANGE/2),
                        int(Wd/2 + self.ACTIVATION_RANGE/2),
                        int(Hd/2 + self.ACTIVATION_RANGE/2))

        if not enablePoint:
            print(
                colored("[Status] aimPointer disabled, only objects detector works...", "red"))
        else:
            print(colored("[AI] AimPLUS enabled..", "green"))

        print()

    def distance(self, x, y, x1, y1):
        return sqrt((x - x1)**2 + (y - y1)**2)

    def setAimPosition(self, x, y):

        CENTER = (Wd/2, Hd/2)

        if x < CENTER[0]:
            x = CENTER[0] - x
            x = -x
        else:
            x = x - CENTER[0]

        if y < CENTER[1]:
            y = CENTER[1] - y
            y = -y
        else:
            y = y - CENTER[1]

        # y = 0

        newposition = (x, y)
        angle = np.arctan2(y, x) * 180 / np.pi
        distFromZero = self.distance(x, y, 0, 0)

        maxDist = Wd/2
        angleDistance = 0
        silence = 0 + (distFromZero / maxDist)

        if x < 0:
            distFromZeroReal = distFromZero
        else:
            distFromZeroReal = -distFromZero

        model = {
            'id': str(time.time()),
            'uniqueId': str(time.time()),
            'position': newposition,
            'px': int(x),
            'py': int(y),
            'x': int(x),
            'y': int(y),
            'angle': int(angle),
            'angleP': int(angleDistance),
            'angleRoot': int(0),
            'dist': int(distFromZeroReal),
            'emissionDist': int(distFromZero),
            'silence': silence,
        }
        self.aimList.append(model)

        # sort by emissionDist
        self.aimList = sorted(
            self.aimList, key=lambda x: x['emissionDist'], reverse=True)
        # slice 1
        self.aimList = self.aimList[:1]

        self.sendCallback("/aimplus", self.aimList)

        return model

    def sendCallback(self, topic, value):
        if self.send is not None:
            self.send(topic, value)

    def processFrame(self, frame, fullFrame):

        # print("aimplus___processFrame", frame.shape)

        start_time = timeit.default_timer()

        if self.W is None or self.H is None:
            (self.H, self.W) = frame.shape[: 2]

        try:

            frame = cv2.UMat(frame)
            blob = cv2.dnn.blobFromImage(frame, 1 / 260, (160, 160),
                                         swapRB=False, crop=False)
            self.net.setInput(blob)
            layerOutputs = self.net.forward(self.ln)
            boxes = []
            confidences = []
            classIDs = []
            self.aimList = []
            for output in layerOutputs:
                for detection in output:
                    scores = detection[5:]
                    # classID = np.argmax(scores)
                    # confidence = scores[classID]
                    classID = 0  # person = 0
                    confidence = scores[classID]
                    if confidence > self.CONFIDENCE:
                        box = detection[0: 4] * \
                            np.array([self.W, self.H, self.W, self.H])
                        (centerX, centerY, width, height) = box.astype("int")
                        x = int(centerX - (width / 2))
                        y = int(centerY - (height / 2))
                        boxes.append([x, y, int(width), int(height)])
                        confidences.append(float(confidence))
                        classIDs.append(classID)
            idxs = cv2.dnn.NMSBoxes(
                boxes, confidences, self.CONFIDENCE, self.THRESHOLD)

            if len(idxs) > 0:

                bestMatch = confidences[np.argmax(confidences)]

                for i in idxs.flatten():
                    (x, y) = (boxes[i][0], boxes[i][1])
                    (w, h) = (boxes[i][2], boxes[i][3])
                    cv2.circle(frame, (int(x + w / 2), int(y + h / 5)),
                               5, (0, 0, 255), -1)  # draw target dot
                    color = [int(c) for c in self.COLORS[classIDs[i]]]
                    cv2.rectangle(frame, (x, y),  # draw a box rectangle
                                  (x + w, y + h), (0, 255, 0), 2)
                    text = "Target {}%".format(int(confidences[i] * 100))
                    cv2.putText(frame, text, (x, y - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                    if self.enablePoint and bestMatch == confidences[i]:
                        # mouseX = self.origbox[0] + (x + w/1.5)
                        # mouseY = self.origbox[1] + (y + h/5)
                        mouseX = int((x + w/1.5))
                        mouseY = int((y + h/5))
                        posTXT = self.setAimPosition(mouseX, mouseY)

                        text = "A_"+str(posTXT['angle']) + \
                            "_X_" + str(posTXT['x']) + "" \
                            "_Y_" + str(posTXT['y']) + "" \
                            "_mx_" + str(mouseX) + "_" \
                            "_my_" + str(mouseY) + "_" \
                            "_D_" + str(posTXT['dist']) + "px"
                        cv2.putText(frame, text, (mouseX-5, mouseY-5),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                self.sendCallback("/aimaligned", True)
            else:
                self.aimList = []
                self.sendCallback("/aimplus", [])
                self.sendCallback("/aimaligned", False)

            if self.devMode:
                cv2.imshow("aimPlus", frame)
                elapsed = timeit.default_timer() - start_time
                sys.stdout.write(
                    "\033[1;33m\rFPS:{1} MS:{0}\t".format(int(elapsed*1000), int(1/elapsed)))
                sys.stdout.flush()
                # wait key q
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    # destroy all windows
                    cv2.destroyAllWindows()
        except Exception as e:
            print("aimplus___error", e)
            # return frame

        # return frame


# def setAimPosition(x, y):

#     print("POINTER", "x: ", x, "y: ", y)

#     # x = 1 + int(x * 65536./Wd)
#     # y = 1 + int(y * 65536./Hd)
#     # extra = ctypes.c_ulong(0)
#     # ii_ = pynput._util.win32.INPUT_union()
#     # ii_.mi = pynput._util.win32.MOUSEINPUT(
#     #     x, y, 0, (0x0001 | 0x8000), 0, ctypes.cast(ctypes.pointer(extra), ctypes.c_void_p))
#     # command = pynput._util.win32.INPUT(ctypes.c_ulong(0), ii_)
#     # SendInput(1, ctypes.pointer(command), ctypes.sizeof(command))


# def aimPointer(enablePoint=True):

#     YOLO_DIRECTORY = "models"  # yolo model path

#     CONFIDENCE = 0.36

#     THRESHOLD = 0.22

#     aimPointer_paused = True  # make aimPointer off on startup

#     GREEN = '\033[92m'  # dont touch it

#     RED = '\033[91m'  # dont touch it

#     RESET = '\033[0m'  # dont touch it

#     # box in the center of your screen, lower value of pixel makes the capture faster, for example 250 mean 250x250 pixel box.
#     ACTIVATION_RANGE = 250

#     labelsPath = os.path.sep.join([YOLO_DIRECTORY, "coco-dataset.labels"])
#     LABELS = open(labelsPath).read().strip().split("\n")
#     np.random.seed(42)
#     COLORS = np.random.randint(0, 255, size=(len(LABELS), 3),
#                                dtype="uint8")

#     weightsPath = os.path.sep.join(
#         [YOLO_DIRECTORY, "yolov3-tiny.weights"])  # yolo path weights
#     configPath = os.path.sep.join(
#         [YOLO_DIRECTORY, "yolov3-tiny.cfg"])  # yolo path models
#     time.sleep(0.4)

#     print("\033[1;36m[Status] loading objects detector..")
#     net = cv2.dnn.readNetFromDarknet(
#         configPath, weightsPath)  # load objects detector
#     net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
#     net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
#     ln = net.getLayerNames()
#     ln = [ln[i - 1] for i in net.getUnconnectedOutLayers()]

#     print("\033[1;36m[Status] Define screen capture area..")
#     W, H = None, None
#     origbox = (int(Wd/2 - ACTIVATION_RANGE/2),  # gui box capture
#                int(Hd/2 - ACTIVATION_RANGE/2),
#                int(Wd/2 + ACTIVATION_RANGE/2),
#                int(Hd/2 + ACTIVATION_RANGE/2))

#     if not enablePoint:
#         print(
#             colored("[Status] aimPointer disabled, only objects detector works...", "red"))
#     else:
#         print(colored("[AI] Aimbot enabled..", "green"))

#     def signal_handler(sig, frame):
#         print("\n[Exit] cleaning up...")
#         sct.close()  # quit and clear terminal
#         cv2.destroyAllWindows()
#         sys.exit(0)
#     signal.signal(signal.SIGINT, signal_handler)

#     # check if cpu and gpu cuda is working or disable.
#     build_info = str("".join(cv2.getBuildInformation().split()))
#     if cv2.ocl.haveOpenCL():
#         cv2.ocl.setUseOpenCL(True)
#         cv2.ocl.useOpenCL()
#         print(colored("[CPU] OpenCL is enabled..", "green"))
#     else:
#         print(
#             colored("[WARNING-CPU] OpenCL is disabled..", "yellow"))
#     if "CUDA:YES" in build_info:
#         print(colored("[GPU] CUDA is enabled..", "green"))
#     else:
#         print(
#             colored("[WARNING-GPU] CUDA is disabled..", "yellow"))

#     print()

#     def toggle_aimPointer():
#         nonlocal aimPointer_paused
#         aimPointer_paused = not aimPointer_paused
#         status = "hold mode" if aimPointer_paused else "always on"
#         color = RED if aimPointer_paused else GREEN
#         print("\nAimbot : " + color + status + RESET)
#         if not aimPointer_paused:
#             duration = 100
#             freq = 440
#             winsound.Beep(freq, duration)
#     keyboard.add_hotkey('F1', toggle_aimPointer)

#     def on_click(x, y, button, pressed):

#         if button == button.x2:
#             nonlocal aimPointer_paused
#             aimPointer_paused = not aimPointer_paused
#             if pressed:
#                 print("")
#             else:
#                 print("")
#     with Listener(on_click=on_click) as listener:

#         while True:
#             if aimPointer_paused:
#                 time.sleep(0.1)
#                 continue
#             start_time = timeit.default_timer()
#             frame = np.array(screen(region=origbox))
#             frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
#             if W is None or H is None:
#                 (H, W) = frame.shape[: 2]

#             frame = cv2.UMat(frame)
#             blob = cv2.dnn.blobFromImage(frame, 1 / 260, (150, 150),
#                                          swapRB=False, crop=False)
#             net.setInput(blob)
#             layerOutputs = net.forward(ln)
#             boxes = []
#             confidences = []
#             classIDs = []
#             for output in layerOutputs:
#                 for detection in output:
#                     scores = detection[5:]
#                     # classID = np.argmax(scores)
#                     # confidence = scores[classID]
#                     classID = 0  # person = 0
#                     confidence = scores[classID]
#                     if confidence > CONFIDENCE:
#                         box = detection[0: 4] * np.array([W, H, W, H])
#                         (centerX, centerY, width, height) = box.astype("int")
#                         x = int(centerX - (width / 2))
#                         y = int(centerY - (height / 2))
#                         boxes.append([x, y, int(width), int(height)])
#                         confidences.append(float(confidence))
#                         classIDs.append(classID)
#             idxs = cv2.dnn.NMSBoxes(boxes, confidences, CONFIDENCE, THRESHOLD)

#             if len(idxs) > 0:

#                 bestMatch = confidences[np.argmax(confidences)]

#                 for i in idxs.flatten():
#                     (x, y) = (boxes[i][0], boxes[i][1])
#                     (w, h) = (boxes[i][2], boxes[i][3])
#                     cv2.circle(frame, (int(x + w / 2), int(y + h / 5)),
#                                5, (0, 0, 255), -1)  # draw target dot
#                     color = [int(c) for c in COLORS[classIDs[i]]]
#                     cv2.rectangle(frame, (x, y),  # draw a box rectangle
#                                   (x + w, y + h), (0, 255, 0), 2)
#                     text = "Target {}%".format(int(confidences[i] * 100))
#                     cv2.putText(frame, text, (x, y - 8),
#                                 cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
#                     if enablePoint and bestMatch == confidences[i]:
#                         mouseX = origbox[0] + (x + w/1.5)
#                         mouseY = origbox[1] + (y + h/5)
#                         setAimPosition(mouseX, mouseY)

#             cv2.imshow("aimPlus", frame)
#             elapsed = timeit.default_timer() - start_time
#             sys.stdout.write(
#                 "\033[1;33m\rFPS:{1} MS:{0}\t".format(int(elapsed*1000), int(1/elapsed)))
#             sys.stdout.flush()
#             if cv2.waitKey(1) & 0xFF == ord('0'):
#                 break

#     signal_handler(0, 0)
#     listener.join()
