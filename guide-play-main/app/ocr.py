from PIL import Image, ImageEnhance, ImageFilter
from math import atan2, cos, sin, sqrt, radians, pi, sqrt
from threading import Timer, Thread
import math
import numpy as np
import scipy.signal as ss
import cv2
import json
import os
import time
import sys
import data
import imutils
import random
import pytesseract
from pytesseract import Output
from utils import resource_path
from ocrTools import reader
# pytesseract.pytesseract.tesseract_cmd = r'tesseract/tesseract.exe'

pytesseract.pytesseract.tesseract_cmd = resource_path(
    'tesseract/tesseract_cli.exe')


class OCR ():
    def __init__(self, callback=None):
        self.send = callback
        self.lastText = None
        self.lastAddress = None

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, item, value):
        return setattr(self, item, value)

    def sendOscMessage(self, topic, value):
        if self.send is not None:
            self.send(topic, value)

    def findText(self, img_rgb, img_gray):
        # found = pytesseract.image_to_string(img_rgb)

        useTesseract = True

        if useTesseract:

            try:
                data = pytesseract.image_to_data(
                    img_rgb, output_type=Output.DICT, lang='eng', config='--psm 7')
            except Exception as e:
                with open("error.txt", "w") as e:
                    e.write(sys.exc_info()[1])

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
                return found
            else:
                return None

        else:
            result = reader(img_rgb)
            if len(result) > 0:
                return result[0][1]
            else:
                return None

    def processText(self, img_bgr, img_rgb):
        # convert to grayscale
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        # apply thresholding
        img_thresh = cv2.threshold(
            img_gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        # show image
        # cv2.imshow('ocr_thresh', img_thresh)

        found = self.findText(img_rgb, img_thresh)
        if found != None:
            if found != self.lastText and found != "   " and found != "  " and found != " " and found != "" and found != None:
                self.lastText = found
                print("TEXT_FOUND", found)
                self.sendOscMessage("/address", self.lastText)
        else:
            self.lastText = ""


# read the image sr_home_submenu_game_590_654

img = cv2.imread("assets/matches/sr_home_submenu_game_590_654.png")
# convert the image to RGB
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
# use easyocr to read the text
result = reader(img_rgb)

# print the result
print(result)
# draw the text on the image
for detection in result:
    top_left = tuple([int(val) for val in detection[0][0]])
    bottom_right = tuple([int(val) for val in detection[0][2]])
    text = detection[1]
    font = cv2.FONT_HERSHEY_SIMPLEX
    img = cv2.rectangle(img, top_left, bottom_right, (0, 255, 0), 5)
    img = cv2.putText(img, text, top_left, font, 2, (0, 0, 0), 5)

# show the image
    # convert tobgr
img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
cv2.imshow('img', img)
cv2.waitKey(0)
