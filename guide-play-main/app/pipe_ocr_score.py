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
import data
import imutils
import sys
import random
import pytesseract
from pytesseract import Output
from utils import resource_path
# from ocrTools import reader
# pytesseract.pytesseract.tesseract_cmd = r'tesseract/tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = resource_path(
    'tesseract/tesseract.exe')


class OCR_SCORE ():
    def __init__(self, callback=None, devMode=False, ocrService=None):
        self.send = callback
        self.devMode = devMode
        self.ocrService = ocrService
        #
        self.clockDelta = 0
        self.clockDeltaMax = 10
        self.clockText = "8:88"
        #
        self.aliveADelta = 0
        self.aliveADeltaMax = 10
        self.aliveBDelta = 0
        self.aliveBDeltaMax = 12
        self.aliveA = "0"
        self.aliveB = "0"
        #
        self.scoreADelta = 0
        self.scoreADeltaMax = 50
        self.scoreBDelta = 0
        self.scoreBDeltaMax = 52
        self.scoreA = "0"
        self.scoreB = "0"
        self.useTesseract = True

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, item, value):
        return setattr(self, item, value)

    def sendOscMessage(self, topic, value):
        if self.send is not None:
            self.send(topic, value)

    def doOCR(self, img_thresh, delta, deltaMax, lastText):
        if delta > deltaMax:
            delta = 0
            found = self.findText(img_thresh, img_thresh)
            if found != None:
                if found != lastText and found != "   " and found != "  " and found != " " and found != "" and found != None:
                    return [found, delta]

        return [lastText, delta]

    def findText(self, img_rgb, img_gray):
        # found = pytesseract.image_to_string(img_rgb)

        if self.useTesseract == True:
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
                    # extract the OCR_SCORE text itself along with the confidence of the text localization
                    text = data['text'][i]
                    conf = int(data['conf'][i])
                    # filter out weak confidence text localizations
                    if conf > 0:
                        # display the confidence and text to our terminal
                        # print("Confidence: {}".format(conf))
                        # print("Text: {}".format(text))
                        # print("")
                        # strip out non-ASCII text so we can draw the text on the image using OpenCV, then draw a bounding box around the text along with the text itself

                        if conf > 50:
                            # sanitize text
                            text = "".join(
                                [c if ord(c) < 128 else "" for c in text]).strip()

                            newText = newText + " " + text

            found = newText
            if found != "" and found != None:
                # print("found", found)
                return found
            else:
                return None
        else:
            if len(img_rgb.shape) == 2:
                img_rgb = cv2.cvtColor(img_rgb, cv2.COLOR_GRAY2BGR)
            result = self.ocrService.reader(img_rgb)
            if result is not None and len(result) > 0:
                return result[0][1]
            else:
                return None

    def processScore(self, frameCropped, frameFull):

        # convert to grayscale
        img_gray = cv2.cvtColor(frameCropped, cv2.COLOR_BGR2GRAY)
        # apply thresholding
        img_thresh = cv2.threshold(
            img_gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

        # create a image same size as img_gray
        img_rgb = np.zeros((img_gray.shape[0], img_gray.shape[1], 3), np.uint8)
        # show image
        # crop 60x45
        img_thresh_CLOCK = img_thresh.copy()
        img_thresh_CLOCK = img_thresh_CLOCK[6:38, 70:140]
        img_thresh_A = img_thresh.copy()
        img_thresh_A = img_thresh_A[3:43, 2:59]
        img_thresh_A_s = img_gray.copy()
        img_thresh_A_s = img_thresh_A_s[46:74, 61:104]
        img_thresh_B = img_thresh.copy()
        img_thresh_B_s = img_gray.copy()
        img_thresh_B_s = img_thresh_B_s[46:74, 108:148]
        img_thresh_B = img_thresh_B[3:43, 154:210]

        # if self.devMode == True:
        #     cv2.imshow('ocr_thresh', img_thresh)
        #     cv2.imshow('ocr_thresh_gray', img_gray)
        #     cv2.imshow('ocr_thresh_A', img_thresh_A)
        #     cv2.imshow('ocr_thresh_A_s', img_thresh_A_s)
        #     cv2.imshow('ocr_thresh_B', img_thresh_B)
        #     cv2.imshow('ocr_thresh_B_s', img_thresh_B_s)
        #     cv2.imshow('ocr_thresh_CLOCK', img_thresh_CLOCK)

        # put text on img_rgb
        cv2.putText(img_rgb, 'A_'+str(self.aliveADelta)+'_'+str(self.aliveA)+'', (0, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

        cv2.putText(img_rgb, 'As_'+str(self.scoreADelta)+'_'+str(self.scoreA)+'', (0, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

        cv2.putText(img_rgb, 'B_'+str(self.aliveBDelta)+'_'+str(self.aliveB)+'', (152, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        cv2.putText(img_rgb, 'Bs_'+str(self.scoreBDelta)+'_'+str(self.scoreB)+'', (152, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        cv2.putText(img_rgb, 'C_'+str(self.clockDelta)+'_'+str(self.clockText)+'', (61, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # # show
        # if self.devMode == True:
        #     cv2.imshow('ocr_rgb', img_rgb)

        # ROUND CLOCK
        self.clockDelta += 1
        self.clockText, self.clockDelta = self.doOCR(
            img_thresh_CLOCK, self.clockDelta, self.clockDeltaMax, self.clockText)

        # ROUND SCORE ALIVES
        self.aliveADelta += 1
        self.aliveA, self.aliveADelta = self.doOCR(
            img_thresh_A, self.aliveADelta, self.aliveADeltaMax, self.aliveA)
        self.aliveBDelta += 1
        self.aliveB, self.aliveBDelta = self.doOCR(
            img_thresh_B, self.aliveBDelta, self.aliveBDeltaMax, self.aliveB)

        # MATCH SCORE VICTORIES
        self.scoreADelta += 1
        self.scoreA, self.scoreADelta = self.doOCR(
            img_thresh_A_s, self.scoreADelta, self.scoreADeltaMax, self.scoreA)
        self.scoreBDelta += 1
        self.scoreB, self.scoreBDelta = self.doOCR(
            img_thresh_B_s, self.scoreBDelta, self.scoreBDeltaMax, self.scoreB)

        self.sendOscMessage("/roundscores", {
            "aliveA": self.aliveA,
            "aliveB": self.aliveB,
            "scoreA": self.scoreA,
            "scoreB": self.scoreB,
            "clock": self.clockText
        })
