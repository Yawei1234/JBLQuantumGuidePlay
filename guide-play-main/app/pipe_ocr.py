from PIL import Image, ImageEnhance, ImageFilter
from math import atan2, cos, sin, sqrt, radians, pi, sqrt
from threading import Timer, Thread
import math
import numpy as np
import scipy.signal as ss
import cv2
import json
import os
import sys
import time
import data
import imutils
import random
import logging
import pytesseract
from pytesseract import Output
from utils import resource_path, set_active_on_top
from screenInfo import hideConsole
# from ocrTools import reader
# pytesseract.pytesseract.tesseract_cmd = r'tesseract/tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = resource_path(
    'tesseract/tesseract.exe')

logger = logging.getLogger(__name__)


class OCR ():
    def __init__(self, callback=None, devMode=False, ocrService=None):
        self.send = callback
        self.lastText = None
        self.lastAddress = None
        self.devMode = devMode
        self.useTesseract = True
        self.ocrService = ocrService

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, item, value):
        return setattr(self, item, value)

    def sendOscMessage(self, topic, value):
        if self.send is not None:
            self.send(topic, value)

    def writeCache(self, img_rgb):
        self.ocrService.writer(img_rgb)

    def findText(self, img_thresh, img_gray, callback=None):
        # found = pytesseract.image_to_string(img_thresh)
        logger.info("OCR_FIND_TEXT")
        print("OCR_FIND_TEXT_STARTED")

        def listenOutput(data):
            print("OCR_SERVICE_RESUL___listenOutput", data)
            if callback is not None:
                callback("/address", data)

        # return
        if self.useTesseract == True:
            try:

                if self.devMode == True:
                    cv2.imshow('ocr_thresh', img_thresh)

                data = pytesseract.image_to_data(
                    img_thresh, output_type=Output.DICT, lang='eng', config='--psm 7')

                # hideConsole()
                # set_active_on_top(None, "Counter-Strike 2")
                # logger.info("TESSERACT_DATA_RAW", data)
                print("TESSERACT_DATA_RAW", data)
            except Exception as e:
                print("TESSERACT_ERROR", e)
                # with open("error.txt", "w") as f:
                #     # logger.error("OCR_FIND_TEXT_ERROR", sys.exc_info()[1])
                #     # print("OCR_FIND_TEXT_ERROR", sys.exc_info()[1])
                #     f.write(sys.exc_info()[1])
                #     f.write("\n")
                #     f.write(str(e))
                #     f.write("\n")
                #     f.write(str(e.args))
                #     f.write("\n")
                #     # end of file
                return None
            # print("TESSERACT_DATA_RAW", data)

            newText = ""

            if data['text'] != None and len(data['text']) > 0:
                # iterate over each of the text
                for i in range(0, len(data['text'])):
                    # extract the bounding box coordinates of the text region from the current result
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    # extract the OCR text itself along with the confidence of the text localization
                    text = data['text'][i]
                    conf = int(data['conf'][i])
                    # filter out weak confidence text localizations
                    if conf > 0:
                        # display the confidence and text to our terminal
                        # print("Confidence: {}".format(conf))
                        # print("Text: {}".format(text))
                        # print("")
                        # strip out non-ASCII text so we can draw the text on the image using OpenCV, then draw a bounding box around the text along with the text itself

                        if conf > 65:
                            text = "".join(
                                [c if ord(c) < 128 else "" for c in text]).strip()
                            # remove special characters
                            text = text.replace(":", "")
                            text = text.replace("#", "")
                            text = text.replace(";", "")
                            text = text.replace("!", "")
                            text = text.replace("?", "")
                            text = text.replace(".", "")
                            text = text.replace(",", "")
                            text = text.replace("'", "")
                            text = text.replace('"', "")
                            text = text.replace("(", "")
                            text = text.replace(")", "")
                            text = text.replace("[", "")
                            text = text.replace("]", "")
                            text = text.replace("{", "")
                            text = text.replace("}", "")
                            text = text.replace("-", "")
                            text = text.replace("_", "")
                            text = text.replace("=", "")
                            text = text.replace("+", "")
                            text = text.replace("*", "")
                            text = text.replace("/", "")
                            text = text.replace("\\", "")
                            text = text.replace("|", "")
                            text = text.replace("<", "")
                            text = text.replace(">", "")
                            text = text.replace("  ", "")
                            text = text.replace("   ", "")
                            text = text.replace("    ", "")
                            text = text.replace("     ", "")
                            text = text.replace("      ", "")
                            text = text.replace("       ", "")
                            text = text.replace("        ", "")
                            newText = newText + " " + text

                        cv2.rectangle(img_gray, (x, y),
                                      (x + w, y + h), (0, 255, 0), 2)
                        cv2.putText(img_gray, text, (x, y - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
                        # show the output image
                        # cv2.imshow("OCR_THRESH", img_gray)
                        # print("TESSERACT_DATA", data)

            found = newText
            if found != "" and found != None and found != self.lastText:
                # print("found", found)
                listenOutput(found)
                return found
            else:
                return None
        else:
            print("OCR_SERVICE_RESULT___WAITING")
            result = self.ocrService.reader(
                img_thresh, None, listenOutput, True, False)
            print("OCR_SERVICE_RESULT", result)
            if result is not None:
                return result
            else:
                return None

    def processText(self, img_bgr, img_rgb):
        print("STARTING_PROCESS_OCR")
        # convert to grayscale
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        # apply thresholding
        img_thresh = cv2.threshold(
            img_gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

        # gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        # # blur = cv2.GaussianBlur(gray, (3, 3), 0)
        # thresh = cv2.threshold(
        #     gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        # # Remove noise using morphological operations and invert the image
        # kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        # opening = cv2.morphologyEx(
        #     thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        # invert = 255 - opening
        # show image
        if self.devMode == True:
            cv2.imshow('address', img_thresh)

        try:
            found = self.findText(img_thresh, img_gray, self.sendOscMessage)
        except Exception as e:
            print("OCR_PROCESS_TEXT_ERROR_A", e)
            logger.error("OCR_PROCESS_TEXT_ERROR_A", e)
            found = None
            return
        if found != None:
            if found != self.lastText and found != "   " and found != "  " and found != " " and found != "" and found != None:
                self.lastText = found
                print("OCR_PIPE_TEXT_FOUND", found)
                self.sendOscMessage("/address", self.lastText)
        else:
            print("OCR_PIPE_TEXT_NOT_FOUND")
            self.lastText = ""
