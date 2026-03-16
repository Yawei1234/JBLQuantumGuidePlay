import sys
from PIL import Image
import base64
from io import BytesIO
import pytesseract
import os
import cv2
import numpy as np
import subprocess
import json
from subprocess import Popen, PIPE, STDOUT
from subStarter import SubStarter
import ast
import time
from threading import Timer
import random
import asyncio
# get relative path
DIR_PATH = os.path.dirname(os.path.realpath(__file__))

global img_str
img_str = ""
# import easyocr
# reader = easyocr.Reader(['en'])


class ReadCLI():
    def __init__(self, command, path, devMode):
        self.path = path
        self.command = command
        self.devMode = devMode
        self.params = []
        self.child = None
        self.started = False
        self.stdout = None
        self.stderr = None
        self.lastKeepAlive = None
        # self.sub = SubStarter(self.command, None,
        #                       "ocr_wrapper ->:", self.resultCallback)
        self.sub = None
        # self.setLiveness()
        self.lastRequest = ""
        self.lastCallBack = None

    def cleanString(self, string):
        newStr = string.replace("\n", "").replace("'", "").replace('"', "")
        newStr = newStr.replace("   ", " ").replace("  ", "")
        newStr = newStr.replace("\\", "").replace(",", "")
        newStr = newStr.replace("_", "")
        newStr = newStr.replace("#", "")
        newStr = newStr.replace(".", "")
        newStr = newStr.replace("!", "").replace(
            ":", "").replace(";", "").replace("?", "").replace("(", "").replace(")", "")
        newStr = newStr.replace("é", "e").replace("è", "e").replace(
            "à", "a").replace("ù", "u").replace("ç", "c").replace("ô", "o").replace("î", "i").replace("â", "a")
        return newStr

    def resultCallback(self, result):
        print("OCR_WRAPPER_RESULT", result)
        try:
            tag = result.split("]]")[1].split(",")[1]
        except Exception as e:
            tag = ""
        print("OCR_WRAPPER_RESULT_TAG", self.cleanString(tag))
        self.lastRequest = ""
        if self.lastCallBack is not None:
            self.lastCallBack(self.cleanString(tag))
            self.lastCallBack = None

    def setLiveness(self):
        if self.sub is not None:
            print("KEEP_ALIVE")
            self.sub.send('refresh')
            # repeat
            t = Timer(3, self.setLiveness)
            t.start()
        else:
            print("KEEP_ALIVE_STOPPED")

    def generateRandomId(self):
        string = "abcdefghijklmnopqrstuvwxyz01234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        return ''.join(random.choice(string) for i in range(10))

    def img_to_txt(img_str):
        msg = b"<plain_txt_msg:img>"

        msg = msg + img_str
        msg = msg + b"<!plain_txt_msg>"
        return msg

    def writer(self, img):
        global img_str
        # safe image to disk with cv2
        # img = cv2.imread(img)
        try:
            # overwrite the image
            print("OCR_WRAPPER_WRITER-SAVING-IMAGE", os.path.join(
                DIR_PATH, "ocr_wrapper", "temp.png"))
            # cv2.imwrite(os.path.join(
            #     DIR_PATH, "ocr_wrapper", "temp.png"), img)
            # convert cv2 image to base64
            img = Image.fromarray(img)
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue())

            # sleep for 1 second
            time.sleep(1)
            # check if file was saved
            if os.path.exists(os.path.join(DIR_PATH, "ocr_wrapper", "temp.png")):
                print("OCR_WRAPPER_WRITER-IMAGE-SAVED")
        except Exception as e:
            print("OCR_WRAPPER_WRITER-ERROR", e)

    def reader(self, rgb=None, gray=None, callback=None, forceRGB=False, shouldWrite=True):
        global img_str
        print("OCR_WRAPPER_STARTED")
        blankImage = None
        if rgb is not None:
            print("RGB", rgb.shape)
            # create blankImage same size
            blankImage = np.zeros(rgb.shape, np.uint8)
        if gray is not None:
            blankImage = np.zeros(rgb.shape, np.uint8)
            print("GRAY", gray.shape)

        finalSTR = ""

        def returnAndClear(finalSTR):

            if blankImage is not None:
                # return the output to callback
                # write blank image to disk
                cv2.imwrite(os.path.join(
                    DIR_PATH, "ocr_wrapper/temp.png"), blankImage)
            if callback is not None:
                print("OCR_WRAPPER-OUTPUT", finalSTR)
                callback(finalSTR)
                return finalSTR
        # safe image to disk with cv2
        # img = cv2.imread(img)
        if shouldWrite == False:
            finalSTR = ""
            try:
                if img_str != "":
                    print("OCR_WRAPPER-READER-IMAGE-EXISTS")

                    sub = Popen([os.path.join(DIR_PATH, "ocr_wrapper", "guide-play-ocr-wrapper.exe"),
                                "--base64", ""+str(img_str)+""], shell=True, close_fds=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                    stdout, err = sub.communicate()

                    # convert strt to json
                    stdout = stdout.replace(b"b'", b"'").replace(b"\\n'", b"'")

                    stdout = stdout.decode('utf-8')

                    if "text" in stdout:

                        stdout = stdout.replace("\n", "").replace("'',", "")
                        # REPLACE DOUBLE SPACE
                        stdout = stdout.replace("   ", " ")
                        stdout = stdout.replace("  ", "")
                        stdout = stdout.split("text")[1].split(
                            "[")[1].split("]")[0].split(",")

                        words = []
                        for word in stdout:
                            word = word.replace("'", "").replace(
                                '"', '').replace(" ", "")

                            words.append(word)
                        # decoded = ast.literal_eval(stdout)
                        finalSTR = " ".join(words)

                        # REMOVE SLASH COMMA UNDERSCORE
                        finalSTR = finalSTR.replace("\\", "").replace(",", "")
                        # remove underscore
                        finalSTR = finalSTR.replace("_", "")
                        # remove dots
                        finalSTR = finalSTR.replace(".", "")
                        # remove accented characters
                        finalSTR = finalSTR.replace("é", "e").replace("è", "e").replace(
                            "à", "a").replace("ù", "u").replace("ç", "c").replace("ô", "o").replace("î", "i").replace("â", "a")
                        # remove special characters
                        finalSTR = finalSTR.replace("!", "").replace(
                            ":", "").replace(";", "").replace("?", "").replace("(", "").replace(")", "")
                    else:
                        finalSTR = ""

                    sub.kill()
                    # return the output to callback
                    # clear
                    finalSTR = self.cleanString(finalSTR)
                    return returnAndClear(finalSTR)

                else:
                    print("OCR_WRAPPER-READER-IMAGE-NOT-EXISTS")
                    finalSTR = ""
            except Exception as e:
                print("OCR_WRAPPER-ERROR", e)
                return None

            return None

        try:
            write = False
            if gray is None:
                if rgb is not None:
                    if forceRGB is True:
                        gray = rgb
                        # # imshow
                        # cv2.imshow("OCR_WRAPPER_GRAY", gray)
                        # # waitkey
                        # cv2.waitKey(1)
                    else:
                        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
                    write = True
                else:
                    write = False
            else:
                write = True
            if write:
                # overwrite the image
                print("SAVING IMAGE", os.path.join(
                    DIR_PATH, "ocr_wrapper", "temp.png"))
                cv2.imwrite(os.path.join(
                    DIR_PATH, "ocr_wrapper", "temp.png"), gray)

                # sleep for 1 second
                time.sleep(1)
                # check if file was saved
                if os.path.exists(os.path.join(DIR_PATH, "ocr_wrapper", "temp.png")):
                    print("IMAGE SAVED")

                if self.sub is None:
                    read = os.path.join(DIR_PATH, "ocr_wrapper", "temp.png")
                    sub = Popen([os.path.join(DIR_PATH, "ocr_wrapper", "guide-play-ocr-wrapper.exe"),
                                "--image", ""+str(read)+""], shell=True, close_fds=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                    stdout, err = sub.communicate()

                    # convert strt to json
                    stdout = stdout.replace(b"b'", b"'").replace(b"\\n'", b"'")

                    stdout = stdout.decode('utf-8')

                    if "text" in stdout:

                        stdout = stdout.replace("\n", "").replace("'',", "")
                        # REPLACE DOUBLE SPACE
                        stdout = stdout.replace("   ", " ")
                        stdout = stdout.replace("  ", "")
                        stdout = stdout.split("text")[1].split(
                            "[")[1].split("]")[0].split(",")

                        words = []
                        for word in stdout:
                            word = word.replace("'", "").replace(
                                '"', '').replace(" ", "")

                            words.append(word)
                        # decoded = ast.literal_eval(stdout)
                        finalSTR = " ".join(words)

                        # REMOVE SLASH COMMA UNDERSCORE
                        finalSTR = finalSTR.replace("\\", "").replace(",", "")
                        # remove underscore
                        finalSTR = finalSTR.replace("_", "")
                        # remove dots
                        finalSTR = finalSTR.replace(".", "")
                        # remove accented characters
                        finalSTR = finalSTR.replace("é", "e").replace("è", "e").replace(
                            "à", "a").replace("ù", "u").replace("ç", "c").replace("ô", "o").replace("î", "i").replace("â", "a")
                        # remove special characters
                        finalSTR = finalSTR.replace("!", "").replace(
                            ":", "").replace(";", "").replace("?", "").replace("(", "").replace(")", "")
                    else:
                        finalSTR = ""

                    # kill sub
                    sub.kill()

                    print("OCR_WRAPPER_OUTPUT___", finalSTR)

                    if blankImage is not None:
                        # return the output to callback
                        # write blank image to disk
                        cv2.imwrite(os.path.join(
                            DIR_PATH, "ocr_wrapper/temp.png"), blankImage)

                    # return the output to callback
                    return returnAndClear(finalSTR)
                else:
                    reqId = self.generateRandomId()
                    cmd = "read " + \
                        os.path.join(DIR_PATH, "ocr_wrapper", "temp.png")
                    # cmd = "ping"
                    print("OCR_WRAPPER_CMD", cmd)

                    self.send(cmd, reqId, returnAndClear)

        except Exception as e:
            print("OCR_WRAPPER_ERROR", e)
            return None

    def start(self):
        if self.sub is None:
            return
        self.sub.start()

    def stop(self):
        self.sub.stop()

    def terminate(self):
        self.sub.terminate()

    def send(self, message, requestId="", callback=None):
        self.lastRequest = requestId
        self.lastCallBack = callback
        while self.lastRequest != "":
            self.sub.sendAndWait(message, self.lastRequest)
            time.sleep(3)

    def quit(self, key="quit", iteration=0):

        print("QUITTING_OCR", key,  iteration)

        if self.sub is None:
            return False

        try:
            self.sub.send('quit')
            time.sleep(1)
            self.cliKiller(iteration+1, self.quit)
            print("TERMINATING", self.sub)
            time.sleep(1)
        except Exception as e:
            print("TERMINATING_ERROR", self.sub, e)
            time.sleep(1)
            self.quit("retry", iteration+1)

    def cliKiller(self, iteration=0, callback=None):
        if self.sub is not None:
            self.sub.send('quit')
            time.sleep(1)

            # time.sleep(1)
            if self.sub is not None:
                poll_result = self.sub.poll()
                if poll_result is None:
                    print("The subprocess is still running.", iteration)
                    self.sub.terminate()
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


# reader()

# print("OCR_WRAPPER_STARTED", DIR_PATH)
# modelPath = os.path.join(DIR_PATH, "ocr_wrapper", "model")
# cliApp = os.path.join(DIR_PATH, "ocr_wrapper", "guide-play-services-ocr.exe")
# reader_cli = ReadCLI(""+cliApp+" --path "+modelPath+"",
#                      modelPath, True)
# reader_cli.start()
# reader_cli.setLiveness()


# reader_cli.send(
#     "read ocr_wrapper/debug.png", "20")
