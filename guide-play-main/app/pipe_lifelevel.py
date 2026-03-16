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
import random


class LIFELEVEL ():
    def __init__(self, callback=None, devMode=False):
        self.send = callback
        self.devMode = devMode
        self.currentLifePercent = 100
        self.lastDamage = -1
        self.totalDamages = 0
        self.damages = []
        self.isDead = False

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, item, value):
        return setattr(self, item, value)

    def sendOscMessage(self, topic, value):
        if self.send is not None:
            self.send(topic, value)

    def resetLife(self):
        self.currentLifePercent = 100
        self.lastDamage = -1
        self.totalDamages = 0
        self.isDead = False

    def checkDamage(self, percentage):
        newPercent = np.round(percentage, 2) * 100
        if self.currentLifePercent > newPercent:
            self.lastDamage = int(time.time() * 1000)
            self.totalDamages += 1
            self.damages.append(self.lastDamage)
            # sort the list by timestamp
            self.damages.sort()

            self.currentLifePercent = newPercent
            self.sendOscMessage("/lifelevel", {
                                "lifelevel": int(self.currentLifePercent),
                                "totalDamages": self.totalDamages,
                                "damages": self.damages,
                                })
        if self.currentLifePercent < 1:
            self.isDead = True
            self.sendOscMessage("/lifelevel", {
                                "lifelevel": 0,
                                "totalDamages": self.totalDamages,
                                "damages": self.damages,
                                }
                                )
            # reset life after 1 seconds
            t = Timer(1.0, self.resetLife)
            t.start()

    def processLifelevel(self, frameCropped, frameFull):

        # convert to grayscale
        img_gray = cv2.cvtColor(frameCropped, cv2.COLOR_BGR2GRAY)
        # apply thresholding
        img_thresh = cv2.threshold(
            img_gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

        # create empty 60x60 black image
        img = np.zeros(
            (frameCropped.shape[0] * 8, frameCropped.shape[1], 3), np.uint8)

        # convert to 2 channels
        img_thresh = cv2.cvtColor(img_thresh, cv2.COLOR_GRAY2BGR)

        barWidth = img_thresh.shape[1]
        barHeight = img_thresh.shape[0]
        percentage = 0
        totalWhitePixels = 0

        # append img_thresh to img
        img[0:img_thresh.shape[0], 0:barWidth] = img_thresh

        # barWidth = 100%
        # get the total width of white pixels
        # in each column of the image

        for i in range(barWidth):
            whitePixels = 0
            for j in range(img_thresh.shape[0]):
                if img_thresh[j][i][0] == 255:
                    whitePixels = 1

            totalWhitePixels += whitePixels
            # calculate the percentage of white pixels
            # in each column of the image
            if totalWhitePixels > 0:
                percentage = (totalWhitePixels / barWidth)
            else:
                percentage = 0
            # calculate the height of the bar

        if self.isDead == False:
            self.checkDamage(percentage)
        else:
            self.currentLifePercent = 0

        cv2.putText(img, ""+str(np.round(percentage, 2) * 100)+"_"+str(barWidth)+"_", (0, frameCropped.shape[0] * 3),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

        cv2.putText(img, "l_"+str(self.currentLifePercent)+"_", (0, frameCropped.shape[0] * 4 + 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        cv2.putText(img, "s_"+str(self.totalDamages)+"_", (0, frameCropped.shape[0] * 5 + 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        # show image
        # if self.devMode:
        #     cv2.imshow('lifevel_thresh', img)
