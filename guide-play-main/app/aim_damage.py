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

#  TODO_


class AIM_DAMAGE ():
    def __init__(self, callback=None):
        self.send = callback
        self.h_damage = 0
        self.s_damage = 150
        self.v_damage = 130
        self.h2_damage = 50
        self.s2_damage = 255
        self.v2_damage = 255
        #
        self.h_aimcross = 0
        self.s_aimcross = 200
        self.v_aimcross = 200
        self.h2_aimcross = 90
        self.s2_aimcross = 255
        self.v2_aimcross = 255

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, item, value):
        return setattr(self, item, value)

    def sendOscMessage(self, topic, value):
        if self.send is not None:
            self.send(topic, value)

    def getColorIntensity(self, frame, rangeA, rangeB):
        # convert to hsv
        img_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # define range of green color in HSV
        lower = rangeA
        upper = rangeB
        # Threshold the HSV image to get only green colors
        mask = cv2.inRange(img_hsv, lower, upper)
        # Bitwise-AND mask and original image
        maskColors = cv2.bitwise_and(
            frame, frame, mask=mask)
        # get percentage of green pixels
        ratio_green = cv2.countNonZero(mask)/(frame.size/3)
        # get percentage of green pixels
        colorPercent = (ratio_green * 100)
        # print the percentage of green pixels
        # put text
        cv2.putText(frame, str(np.round(colorPercent, 2)), (10, 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return [colorPercent, frame]

    def getColorIntensityLegacy(self, frame, color=[22, 229, 16]):
        # Read image

        img = frame

        # Here, you define your target color as
        # a tuple of three values: RGB
        green = color

        # You define an interval that covers the values
        # in the tuple and are below and above them by 20
        diff = 20

        # Be aware that opencv loads image in BGR format,
        # that's why the color values have been adjusted here:
        boundaries = [([green[2], green[1]-diff, green[0]-diff],
                       [green[2]+diff, green[1]+diff, green[0]+diff])]

        # Scale your BIG image into a small one:
        scalePercent = 0.3

        # Calculate the new dimensions
        width = int(img.shape[1] * scalePercent)
        height = int(img.shape[0] * scalePercent)
        newSize = (width, height)

        # Resize the image:
        img = cv2.resize(img, newSize, None, None, None, cv2.INTER_AREA)

        # check out the image resized:
        # cv2.imshow("img resized", img)
        # cv2.waitKey(0)

        # for each range in your boundary list:
        for (lower, upper) in boundaries:

            # You get the lower and upper part of the interval:
            lower = np.array(lower, dtype=np.uint8)
            upper = np.array(upper, dtype=np.uint8)

            # cv2.inRange is used to binarize (i.e., render in white/black) an image
            # All the pixels that fall inside your interval [lower, uipper] will be white
            # All the pixels that do not fall inside this interval will
            # be rendered in black, for all three channels:
            mask = cv2.inRange(img, lower, upper)

            # Check out the binary mask:
            # cv2.imshow("binary mask", mask)
            # cv2.waitKey(0)

            # Now, you AND the mask and the input image
            # All the pixels that are white in the mask will
            # survive the AND operation, all the black pixels
            # will remain black
            output = cv2.bitwise_and(img, img, mask=mask)

            # Check out the ANDed mask:
            # cv2.imshow("ANDed mask", output)
            # cv2.waitKey(0)

            # You can use the mask to count the number of white pixels.
            # Remember that the white pixels in the mask are those that
            # fall in your defined range, that is, every white pixel corresponds
            # to a green pixel. Divide by the image size and you got the
            # percentage of green pixels in the original image:
            ratio_green = cv2.countNonZero(mask)/(img.size/3)

            # This is the color percent calculation, considering the resize I did earlier.
            colorPercent = (ratio_green * 100) / scalePercent

            # Print the color percent, use 2 figures past the decimal point
            print('green pixel percentage:', np.round(colorPercent, 2))

            # numpy's hstack is used to stack two images horizontally,
            # so you see the various images generated in one figure:
            # cv2.imshow("images", np.hstack([img, output]))
            # cv2.waitKey(0)

    def processAim(self, frameCropped, frameFull, maskFile, devMode=False):

        # filter green color

        # convert to hsv
        img_hsv = cv2.cvtColor(frameCropped, cv2.COLOR_BGR2HSV)
        # define range of green color in HSV
        lower_damage = np.array([self.h_damage, self.s_damage, self.v_damage])
        upper_damage = np.array(
            [self.h2_damage, self.s2_damage, self.v2_damage])

        lower_aimcross = np.array(
            [self.h_aimcross, self.s_aimcross, self.v_aimcross])
        upper_aimcross = np.array(
            [self.h2_aimcross, self.s2_aimcross, self.v2_aimcross])

        # Threshold the HSV image to get only green colors
        maskDamage = cv2.inRange(img_hsv, lower_damage, upper_damage)
        maskAimCross = cv2.inRange(img_hsv, lower_aimcross, upper_aimcross)

        # Bitwise-AND mask and original image
        maskDamageColors = cv2.bitwise_and(
            frameCropped, frameCropped, mask=maskDamage)
        maskAimCrossColors = cv2.bitwise_and(
            frameCropped, frameCropped, mask=maskAimCross)

        # apply png mask
        maskDamgeFile = cv2.imread(maskFile, 0)
        # convert to bgr

        # apply mask
        damageMasked = cv2.bitwise_or(
            maskDamageColors, maskDamageColors, mask=maskDamgeFile)

        # show image
        # cv2.imshow('aim_damage', damageMasked)

        # crop 61x61 at the cente of maskAimCrossColors
        # get center
        height, width, channels = maskAimCrossColors.shape
        center = (int(width/2), int(height/2))
        # get crop size
        cropSize = 61
        # get crop coords
        cropCoords = [center[0]-cropSize/2, center[1]-cropSize/2,
                      center[0]+cropSize/2, center[1]+cropSize/2]
        # crop
        aimCrossCropped = maskAimCrossColors[int(cropCoords[1]):int(cropCoords[3]),
                                             int(cropCoords[0]):int(cropCoords[2])]
        # show image

        # get the percentage of green pixels in the cropped image
        rangeA = np.array([self.h_aimcross, self.s_aimcross, self.v_aimcross])
        rangeB = np.array(
            [self.h2_aimcross, self.s2_aimcross, self.v2_aimcross])

        greenPercent, maskAimCrossColors = self.getColorIntensity(
            maskAimCrossColors, rangeA, rangeB)
        greenPercentCropped, aimCrossCropped = self.getColorIntensity(
            aimCrossCropped, rangeA, rangeB)

        # totalGreenPercent
        totalGreenPercent = (greenPercent + greenPercentCropped) / 2

        self.sendOscMessage("/aim_cross", totalGreenPercent)

        # cv2.imshow('aim_cross', maskAimCrossColors)
        # cv2.imshow('aim_cross_cropped', aimCrossCropped)

        # convert to grayscale
        img_gray = cv2.cvtColor(frameCropped, cv2.COLOR_BGR2GRAY)
        # apply thresholding
        img_thresh = cv2.threshold(
            img_gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        # show image
        # cv2.imshow('aim_thresh', img_thresh)
