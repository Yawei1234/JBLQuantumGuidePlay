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
import sys
import pytesseract
from pytesseract import Output
import numpy as np
import matplotlib.pyplot as plt
import concurrent.futures
from skimage import data as skimage_data
from skimage.feature import match_template
from skimage.util import img_as_float
# from matplotlib import pyplot as plt
from imutils.object_detection import non_max_suppression  # pip install imutils
from utils import getRelativeCoords, resource_path
# from ocrTools import reader
# pytesseract.pytesseract.tesseract_cmd = r'tesseract/tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = resource_path(
    'tesseract/tesseract.exe')


class NumpyEncoder(json.JSONEncoder):
    """ Special json encoder for numpy types """

    def default(self, obj):
        if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
                            np.int16, np.int32, np.int64, np.uint8,
                            np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32,
                              np.float64)):
            return float(obj)
        elif isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


class GAMESTATES ():
    def __init__(self, callback=None, devMode=False, ocrService=None):
        self.send = callback
        self.devMode = devMode
        self.ocrService = ocrService
        self.lastText = None
        self.lastAddress = None
        self.dirname = os.path.dirname(__file__)

        # radar north arrow
        self.radarNorthArrow = False
        self.radarNorthArrowDelta = 0
        self.radarNorthArrowDeltaMax = 3
        # spectator deltas
        self.spectatorCheckDelta = 0
        self.spectatorCheckDeltaMax = 12
        self.spectatorCheck = False
        # matchresultCrops
        self.matchresultDelta = 0
        self.matchresultDeltaMax = 20
        self.matchresult = False
        # radar spectator
        self.radarSpectatorDelta = 0
        self.radarSpectatorDeltaMax = 30
        self.radarSpectator = False
        # teamside deltas
        self.Delta = 0
        self.teamSideDelta = 0
        self.teamSideDeltaMax = 35
        self.teamSide = "nf"
        self.teamSideThresholdParam1 = 170
        self.teamSideThresholdParam2 = 255
        # search gamestate deltas
        self.searchGameStateDelta = 0
        self.searchGameStateDeltaMax = 20

        # params
        self.h_radarsquare = 0
        self.s_radarsquare = 0
        self.v_radarsquare = 190
        self.h2_radarsquare = 190
        self.s2_radarsquare = 255
        self.v2_radarsquare = 255

        self.useTesseract = False

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, item, value):
        return setattr(self, item, value)

    def sendOscMessage(self, topic, value, extras=None):
        # print("GAMESTATE_SENDING_GAMESTATE", topic, value)
        if self.send is not None:
            self.send(topic, value, extras)

    def getRadarArrowLegacy(self, src, img_target="assets/matches/gameplay_radararrow_transp.png", plot=False):

        template = cv2.imread(img_target, cv2.IMREAD_COLOR)
        # srcImg = cv2.imread(src, cv2.IMREAD_COLOR)
        # bgr2
        srcImg = cv2.cvtColor(src, cv2.COLOR_BGR2RGB)

        image = img_as_float(srcImg)
        template = img_as_float(template)

        # image = skimage_data.arrows()
        image = image[0:40, 190:240]

        arrow = template

        result = match_template(image, arrow)
        ij = np.unravel_index(np.argmax(result), result.shape)
        x, y = ij[1], ij[0]

        # return true if found
        if x > 0 and y > 0:
            return True

        if plot == True:

            fig = plt.figure(figsize=(8, 3))
            ax1 = plt.subplot(1, 3, 1)
            ax2 = plt.subplot(1, 3, 2)
            ax3 = plt.subplot(1, 3, 3, sharex=ax2, sharey=ax2)

            ax1.imshow(arrow, cmap=plt.cm.gray)
            ax1.set_axis_off()
            ax1.set_title('template')

            ax2.imshow(image, cmap=plt.cm.gray)
            ax2.set_axis_off()
            ax2.set_title('image')
            # highlight matched region
            rect = plt.Rectangle((x, y), arrow.shape[1], arrow.shape[0],
                                 edgecolor='r', facecolor='none')
            ax2.add_patch(rect)

            ax3.imshow(result)
            ax3.set_axis_off()
            ax3.set_title('`match_template`\nresult')
            # highlight matched region
            ax3.autoscale(False)
            ax3.plot(x, y, 'o', markeredgecolor='r',
                     markerfacecolor='none', markersize=10)

            plt.show()
        return False

    def checkTemplateThread(self, frame, template, threshold=0.7):
        res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)

        loc = np.where(res >= threshold)
        return loc

    def checkTemplate(self, frame, templateFile=None, templateFiles=[], template=None, threshold=0.7):

        if len(templateFiles) > 0 and templateFile is None:
            # iterate templateFiles
            for file in templateFiles:
                try:
                    template = cv2.imread(os.path.join(
                        self.dirname, "assets/matches/"+file), 0)
                    # print("template_f", file)
                    # print("template_s", template.shape)
                    w, h = template.shape[::-1]
                    # print("w", w)
                    # print("h", h)

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            self.checkTemplateThread, frame, template, threshold)
                        loc = future.result()
                        for pt in zip(*loc[::-1]):
                            # print("pt", pt)
                            cv2.rectangle(
                                frame, (pt[0] + 1, pt[1] + 1), (pt[0] + w, pt[1] + h), (0, 0, 255), 1)
                            # print("found", item["tag"])
                            return file
                except Exception as e:
                    print("ERROR-PIPE_GAMESTATE_________ checkTemplate", e)
                    return "not-found"

                # res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
                # threshold = 0.7
                # loc = np.where(res >= threshold)
                # # print("loc", loc)
                # for pt in zip(*loc[::-1]):
                #     # print("pt", pt)
                #     cv2.rectangle(
                #         frame, (pt[0] + 1, pt[1] + 1), (pt[0] + w, pt[1] + h), (0, 0, 255), 1)
                #     # print("found", item["tag"])
                #     return file
            return "not-found"

        if template is None:
            template = cv2.imread(os.path.join(
                self.dirname, "assets/matches/"+templateFile), 0)
        # print("template", template.shape)
        # print("template", template)
        w, h = template.shape[::-1]
        # print("w", w)
        # print("h", h)
        res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        threshold = 0.7
        loc = np.where(res >= threshold)
        # print("loc", loc)
        for pt in zip(*loc[::-1]):
            # print("pt", pt)
            cv2.rectangle(
                frame, (pt[0] + 1, pt[1] + 1), (pt[0] + w, pt[1] + h), (0, 0, 255), 1)
            # print("found", item["tag"])
            return True
        return False

    def processGamestates(self, lastFrameFull, monitoring, parentRef=None):
        # cv2.imshow('gamestate', lastFrameFull)
        # print("GAMESTATE_PROCESSING", lastFrameFull.shape)

        stateFound = False

        if parentRef is not None:
            spectatorMSGCoords = getRelativeCoords(
                [778, 1062, 1140, 1076], lastFrameFull.shape[1], lastFrameFull.shape[0])

            spectatorMSG = lastFrameFull[spectatorMSGCoords[0][1]:spectatorMSGCoords[1]
                                         [1], spectatorMSGCoords[0][0]:spectatorMSGCoords[1][0]]

            # spectatorMSG threshold
            img_gray = cv2.cvtColor(spectatorMSG, cv2.COLOR_BGR2GRAY)
            # apply thresholding
            img_thresh = cv2.threshold(
                img_gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
            # show
            # cv2.imshow('gamestate_cropped', img_thresh)

            # create a 212x74 image
            img_results = np.zeros((74, 212, 3), np.uint8)

            # put text
            font = cv2.FONT_HERSHEY_SIMPLEX

            self.spectatorCheckDelta += 1
            if self.spectatorCheckDelta > self.spectatorCheckDeltaMax:
                self.spectatorCheck = self.checkTemplate(
                    img_thresh, "sr_ingame_spectator.png")
                self.spectatorCheckDelta = 0

            cv2.putText(img_results, 'spct_'+str(self.spectatorCheckDelta)+'_'+str(self.spectatorCheck)+'', (0, 30),
                        font, 0.5, (255, 255, 0), 1)

            if self.spectatorCheck == True:
                stateFound = True
            # show
            # cv2.imshow('gamestate_cropped_rgb', img_results)

            # RADAR NORTH ARROW

            try:

                radarNorthArrowCoords = getRelativeCoords(
                    [206, 0, 224, 26], lastFrameFull.shape[1], lastFrameFull.shape[0])

                radarNorthArrow = lastFrameFull[radarNorthArrowCoords[0][1]:radarNorthArrowCoords[1]
                                                [1], radarNorthArrowCoords[0][0]:radarNorthArrowCoords[1][0]]

                # keep only white pixels
                radarNorthArrow = cv2.cvtColor(
                    radarNorthArrow, cv2.COLOR_BGR2GRAY)
                radarNorthArrow = cv2.threshold(
                    radarNorthArrow, 200, 255, cv2.THRESH_BINARY)[1]

                expansion = 8

                radarNorthArrowExpanded = np.zeros(
                    (radarNorthArrow.shape[0]+expansion, radarNorthArrow.shape[1]+expansion), np.uint8)

                radarNorthArrowExpanded[expansion//2:radarNorthArrow.shape[0] +
                                        expansion//2, expansion//2:radarNorthArrow.shape[1]+expansion//2] = radarNorthArrow

                arrowTemplates = [
                    'sr_ingame_radarnortharrow.png',
                ]

                # use template as mask
                arrowOriginal = cv2.imread(os.path.join(
                    self.dirname, "assets/matches/"+arrowTemplates[0]), 0)

                # arrowOriginal = None
                # radarNorthArrowExpanded = None

                radarNorthArrowExpanded = cv2.bitwise_or(
                    radarNorthArrowExpanded, radarNorthArrowExpanded, mask=arrowOriginal)

                self.radarNorthArrowDelta += 1

                if self.radarNorthArrowDelta > self.radarNorthArrowDeltaMax:
                    checkArrowPresence = self.checkTemplate(
                        radarNorthArrowExpanded, None, arrowTemplates)

                    presence = checkArrowPresence
                    if presence == "sr_ingame_radarnortharrow.png":
                        presence = True
                    else:
                        presence = False

                    self.radarNorthArrowDelta = 0

                    self.radarNorthArrow = presence

                # # convert to bgr
                # radarNorthArrowExpanded = cv2.cvtColor(
                #     radarNorthArrowExpanded, cv2.COLOR_GRAY2BGR)

                if self.radarNorthArrow == True:
                    stateFound = True

                # put text
                font = cv2.FONT_HERSHEY_SIMPLEX
                cv2.putText(radarNorthArrowExpanded, ''+str(self.radarNorthArrowDelta)+'_'+str(self.radarNorthArrow)+'', (0, radarNorthArrowExpanded.shape[0] - 4),
                            font, 0.4, (255, 255, 0), 1)
            except Exception as e:
                print("ERROR-PIPE_GAMESTATE_________ radarNorthArrow", e)

            # show
            # cv2.imshow('gamestate_cropped_radarNorthArrow',
            #            radarNorthArrowExpanded)

        # iterate monitoring
        for crop in monitoring:
            # check crop evidences

            # radar spectator
            # check the existence of radar spectator
            if crop["id"] == "radar_spectator":
                self.radarSpectatorDelta += 1

                radarSpec = crop["frame"]
                radarSquareBase = crop["frame"].copy()
                # fill with black from 20 to 40 vertical pixels
                radarSquareBase[1:radarSquareBase.shape[0]-1, 1:radarSquareBase.shape[1]-1] = [
                    0, 0, 0]
                radarSquareBaseExpanded = np.zeros(
                    (radarSquareBase.shape[0]+4, radarSquareBase.shape[1]+4, 3), np.uint8)

                # put radarSquareBase in the center of radarSquareBaseExpanded
                radarSquareBaseExpanded[2:radarSquareBase.shape[0] +
                                        2, 2:radarSquareBase.shape[1]+2] = radarSquareBase

                if self.radarSpectatorDelta > self.radarSpectatorDeltaMax:
                    self.radarSpectatorDelta = 0
                    # Color segmentation
                    hsv = cv2.cvtColor(
                        radarSquareBaseExpanded, cv2.COLOR_BGR2HSV)
                    lower_lightBlue = np.array(
                        [self.h_radarsquare, self.s_radarsquare, self.v_radarsquare])
                    upper_lightBlue = np.array(
                        [self.h2_radarsquare, self.s2_radarsquare, self.v2_radarsquare])
                    mask = cv2.inRange(hsv, lower_lightBlue, upper_lightBlue)
                    res = cv2.bitwise_and(
                        radarSquareBaseExpanded, radarSquareBaseExpanded, mask=mask)

                    # Contour exctraction
                    imgray = cv2.cvtColor(res, cv2.COLOR_BGR2GRAY)
                    blurred = cv2.GaussianBlur(imgray, (5, 5), 0)
                    ret, thresholded = cv2.threshold(blurred, 50, 255, 0)
                    contours, h = cv2.findContours(thresholded, 1, 2)

                    # cv2.imshow('gamestate_crop_radarSpec_thresholded',
                    #         thresholded)

                    # Square detection
                    for cnt in contours:
                        approx = cv2.approxPolyDP(
                            cnt, 0.01 * cv2.arcLength(cnt, True), True)
                        # to discard noise from the color segmentation
                        if (len(approx) == 4) & (cv2.contourArea(cnt) > 25):
                            contour_poly = cv2.approxPolyDP(cnt, 3, True)
                            center, radius = cv2.minEnclosingCircle(
                                contour_poly)
                            color = (0, 0, 255)
                            cv2.circle(radarSquareBaseExpanded, (int(
                                center[0]), int(center[1])), int(radius), color, 2)
                            self.radarSpectator = True
                        else:
                            self.radarSpectator = False

                # cv2.imshow('gamestate_crop_radarSpec', radarSpec)
                if self.radarSpectator == True:
                    stateFound = True

                # put text radarSquareBaseExpanded
                font = cv2.FONT_HERSHEY_SIMPLEX
                cv2.putText(radarSquareBaseExpanded, 'rs_'+str(self.radarSpectatorDelta)+'_'+str(self.radarSpectator)+'', (4, radarSquareBaseExpanded.shape[0] - 6),
                            font, 0.4, (255, 255, 0), 1)

                # cv2.imshow('gamestate_crop_radarSpec_base',
                #            radarSquareBaseExpanded)
            # teamlogo
            # check the existence of any teamlogo
            if crop["id"] == "teamlogo":
                self.teamSideDelta += 1

                logo = crop["frame"]
                logoCircle = np.zeros(
                    (logo.shape[0], logo.shape[1], 3), np.uint8)
                # draw a circle in the center of the image
                cv2.circle(logoCircle, (logo.shape[1]//2, logo.shape[1]//2),
                           logo.shape[1]//2-4, (255, 255, 255), -1)

                # mask logo with logoCircle
                logo = cv2.bitwise_and(logo, logoCircle)
                # convert to grayscale
                logo_gray = cv2.cvtColor(logo, cv2.COLOR_BGR2GRAY)
                # apply thresholding
                # logo_thresh = cv2.threshold(
                #     logo_gray, self.teamSideThresholdParam1, self.teamSideThresholdParam2, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
                logo_thresh = cv2.threshold(
                    logo_gray, self.teamSideThresholdParam1, self.teamSideThresholdParam2, cv2.THRESH_BINARY)[1]
                # teamlogos templates
                logoTemplates = [
                    'sr_ingame_teamlogo_t.png',
                    'sr_ingame_teamlogo0_t.png',
                    'sr_ingame_teamlogo1_t.png',
                    'sr_ingame_teamlogo_ct.png',
                    'sr_ingame_teamlogo0_ct.png',
                    'sr_ingame_teamlogo1_ct.png',
                ]

                if self.teamSideDelta > self.teamSideDeltaMax:
                    checkSide = self.checkTemplate(
                        logo_thresh, None, logoTemplates, 0.5)

                    side = checkSide
                    if "_ct" in side:
                        side = "ct"
                    if "_t" in side:
                        side = "t"
                    if side == "sr_ingame_teamlogo_ct.png":
                        side = "ct"
                    if side == "sr_ingame_teamlogo_t.png":
                        side = "t"
                    if side == "not-found":
                        side = "nf"

                    self.teamSideDelta = 0

                    self.teamSide = side

                if self.teamSide == "ct" or self.teamSide == "t":
                    stateFound = True

                # put text
                # if self.devMode == True:
                #     font = cv2.FONT_HERSHEY_SIMPLEX
                #     # cv2.putText(logo_thresh, 'ts_'+str(self.teamSide)+'', (0, logo.shape[0] - 4),
                #     #             font, 0.4, (255, 255, 0), 1)

                #     cv2.imshow('teamside_crop', logo_thresh)
                #     cv2.imshow('teamside_crop_g', logo_gray)
                #     # on key press g save the image
                #     if cv2.waitKey(1) & 0xFF == ord('g'):
                #         cv2.imwrite(os.path.join(
                #             self.dirname, "assets/matches/sr_ingame_teamlogo_new.png"), logo_thresh)

            # matchresult
            # check the existence of matchresult
            # if crop["id"] == "matchresult":

        # if dont find the imperative evidences, search the gamestate
        if stateFound == False:
            self.searchGameStateDelta += 1
            if self.searchGameStateDelta > self.searchGameStateDeltaMax:
                self.searchGameStateDelta = 0
                # print("GAMESTATE_PROCESSING_FAIL_IMPERATIVE", lastFrameFull.shape)
                self.searchGameState(lastFrameFull, parentRef)
            # else:
            #     print("GAMESTATE_PROCESSING_FAIL_IMPERATIVE_ADDDELTA",
            #           self.searchGameStateDelta, self.devMode)
        else:
            stateConcluded = "gameplay"

            if self.radarSpectator is True or self.spectatorCheck is True:
                stateConcluded = "spectator"

            if self.teamSide == "nf" and (self.radarSpectator is True or self.spectatorCheck is True):
                stateConcluded = "spectator"

            # print("GAMESTATE_PROCESSING_FOUND_IMPERATIVE", stateConcluded)

            if self.radarNorthArrow == True:
                stateConcluded = "gameplay"

            self.sendOscMessage("/gamestate", stateConcluded,
                                {"operation": "found-imperative",
                                 "detail": stateConcluded,
                                 "arrowFound": self.radarNorthArrow,
                                 "radarSpectator": self.radarSpectator,
                                 "spectatorFound": self.spectatorCheck,
                                 "teamSide": self.teamSide})

    def searchGameState(self, lastFrameFull, parentRef=None):

        # print lastframe width and height
        # print("GAMESTATE_searchGameState", lastFrameFull.shape)

        evidences = [
            # {
            #     "name": "home",
            #     "detail": "home-settings",
            #     "template": "assets/matches/home_gamestate_settings.png",
            #     "coords": getRelativeCoords(
            #         [0, 0, 260, 64], lastFrameFull.shape[1], lastFrameFull.shape[0])
            # },
            {
                "name": "home",
                "detail": "home-home",
                "template": "assets/matches/home_home.png",
                "coords": getRelativeCoords(
                    [0, 0, 260, 64], lastFrameFull.shape[1], lastFrameFull.shape[0])
            },

            # {
            #     "name": "ingame-menu",
            #     "detail": "ingame-menu-home",
            #     "template": "assets/matches/ingame_menu.png",
            #     "coords": getRelativeCoords(
            #         [0, 0, 260, 64], lastFrameFull.shape[1], lastFrameFull.shape[0])
            # },
            # {
            #     "name": "select-side",
            #     "detail": "select-side-screen-ct",
            #     "template": "assets/matches/selectside_ct_icon.png",
            #     "coords": [(40, 120), (520, 600)]
            # },
            # {
            #     "name": "select-side",
            #     "detail": "select-side-screen-terror",
            #     "template": "assets/matches/selectside_terror_icon.png",
            #     "coords": [(40, 120), (1320, 1400)]
            # },
        ]

        image = lastFrameFull

        # iterate to evidences
        for evidence in evidences:

            evidenceName = evidence["name"]
            # print("GAMESTATE_searchGameState_1", evidenceName)

            template = cv2.imread(evidence["template"], cv2.IMREAD_GRAYSCALE)
            # convert to grayscale
            # template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

            # print("GAMESTATE_CHECKING_TEMPLATE", template.shape)

            image = lastFrameFull[evidence["coords"][0][1]:evidence["coords"][1]
                                  [1], evidence["coords"][0][0]:evidence["coords"][1][0]]

            # convert to grayscale
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # apply thresholding
            image_t = cv2.threshold(
                image, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

            # show
            # cv2.imshow('GAMESTATE_searchGameState', image)

            # if evidence["detail"] == "home-home":
            tag = "home_home"
            file = ""+str(tag)+""
            if self.devMode == True:
                if cv2.waitKey(1) & 0xFF == ord('x'):
                    print("saving", file)
                    cv2.imwrite(os.path.join(
                        self.dirname, "assets/matches/"+file+".png"), image)
                    cv2.imwrite(os.path.join(
                        self.dirname, "assets/matches/"+file+"_t.png"), image_t)

            if evidenceName != "select-side":

                try:
                    assert image_t is not None and image is not None, "file could not be read, check with os.path.exists()"
                    # Perform template matching
                    # print("GAMESTATE_searchGameState_t1",  template.shape)
                    # print("GAMESTATE_searchGameState_s1",  image.shape)
                    # print("GAMESTATE_searchGameState_s2",  image_t.shape)

                    resultGray = self.checkTemplate(
                        image, None, [], template)

                    resultThresh = self.checkTemplate(
                        image_t, None, [], template)

                    # resultThresh = cv2.matchTemplate(
                    #     image_t, template, cv2.TM_CCOEFF_NORMED)
                except:
                    print("GAMESTATE_searchGameState_CHECK_ERROR", evidenceName)

            # print("PASSED__", gamestate)

            found = False
            # if resultGray true or resultThresh true
            if resultGray == True or resultThresh == True:
                found = True
                operation = "found-onsearch"

            if found == True:
                print("GAMESTATE_searchGameState_FOUND", evidenceName)

                self.sendOscMessage("/gamestate", evidenceName,
                                    {"operation": operation,
                                     "detail": evidence["detail"],
                                     "arrowFound": self.radarNorthArrow,
                                     "radarSpectator": self.radarSpectator,
                                     "spectatorFound": self.radarSpectator,
                                     "teamSide": self.teamSide})
            else:
                print("GAMESTATE_searchGameState_WATCHING", evidenceName)

    def getGameStateMethods(self, lastFrame):
        # TM_CCORR method

        # print("GAMESTATE_CHECKING")

        lastFrame = cv2.cvtColor(lastFrame, cv2.COLOR_BGR2GRAY)
        # crop 65 vertical pixels
        lastFrame = lastFrame[0:65, 0:360]
        # show cropped image
        # cv2.imshow('img', lastFrame)
        # return
        assert lastFrame is not None, "file could not be read, check with os.path.exists()"
        img2 = lastFrame.copy()
        template = cv2.imread(
            'assets/matches/home_gamestate_settings.png', cv2.IMREAD_GRAYSCALE)
        assert template is not None, "file could not be read, check with os.path.exists()"
        w, h = template.shape[::-1]
        # All the 6 methods for comparison in a list
        methods = ['cv2.TM_CCORR']
        found = False
        for meth in methods:
            img = img2.copy()
            t1 = time.time()
            method = eval(meth)
            # Apply template Matching
            res = cv2.matchTemplate(img, template, method)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

            # print("GAMESTATE_CHECKING_RESULT_max_val", max_val)
            # print("GAMESTATE_CHECKING_RESULT_max_loc", max_loc)
            # print("GAMESTATE_CHECKING_RESULT_min_val", min_val)
            # print("GAMESTATE_CHECKING_RESULT_min_loc", min_loc)

            t2 = time.time()
            # If the method is TM_SQDIFF or TM_SQDIFF_NORMED, take minimum
            if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                top_left = max_loc
            else:
                top_left = max_loc
            bottom_right = (top_left[0] + w, top_left[1] + h)

            # print("GAMESTATE_CHECKING_RESULT_top_left", top_left)
            # print("GAMESTATE_CHECKING_RESULT_bottom_right", bottom_right)

            if int(min_val) > 40000000 and int(max_val) < 70000000 and top_left[0] == 0 and top_left[1] == 0:
                found = True
                gamestate = "ingame-menu"
                # print("GAMESTATE_FOUND")

            if int(min_val) > 45000000 and int(max_val) > 80000000 and top_left[0] == 0 and top_left[1] == 0:
                found = True
                gamestate = "home"
                # print("GAMESTATE_FOUND")

            if found == True:
                # print("max_val", max_val)
                dataPoint = {
                    "min_val": min_val,
                    "max_val": max_val,
                    "min_loc": min_loc,
                    "max_loc": max_loc,
                    "top_left": top_left,
                    "bottom_right": bottom_right
                }
                operation = json.dumps(dataPoint)

                return True
            else:
                return False

    def matchMethods(self, img_target, img_template):
        img = cv2.imread(img_target, cv2.IMREAD_GRAYSCALE)

        # crop 60 vertical pixels
        img = img[0:65, 0:360]
        # show cropped image
        # cv2.imshow('img', img)
        # return
        assert img is not None, "file could not be read, check with os.path.exists()"
        img2 = img.copy()
        template = cv2.imread(img_template, cv2.IMREAD_GRAYSCALE)
        assert template is not None, "file could not be read, check with os.path.exists()"
        w, h = template.shape[::-1]
        # All the 6 methods for comparison in a list
        methods = ['cv2.TM_CCOEFF', 'cv2.TM_CCOEFF_NORMED', 'cv2.TM_CCORR',
                   'cv2.TM_CCORR_NORMED', 'cv2.TM_SQDIFF', 'cv2.TM_SQDIFF_NORMED']
        for meth in methods:
            img = img2.copy()
            t1 = time.time()
            method = eval(meth)
            # Apply template Matching
            res = cv2.matchTemplate(img, template, method)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            t2 = time.time()
            # If the method is TM_SQDIFF or TM_SQDIFF_NORMED, take minimum
            if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                top_left = min_loc
            else:
                top_left = max_loc
            bottom_right = (top_left[0] + w, top_left[1] + h)
            cv2.rectangle(img, top_left, bottom_right, 255, 2)
            # plt.subplot(121), plt.imshow(res, cmap='gray')
            # plt.title('Matching Result:' + str(t2 - t1)
            #           ), plt.xticks([]), plt.yticks([])
            # plt.subplot(122), plt.imshow(img, cmap='gray')
            # plt.title('Detected Point'), plt.xticks([]), plt.yticks([])
            # plt.suptitle(meth)
            # plt.show()

    def matchFiltered(self, img_target, img_template):
        # Load the image and template
        image = cv2.imread(img_target, cv2.IMREAD_COLOR)

        image = image[0:65, 0:360]
        template = cv2.imread(img_template, cv2.IMREAD_COLOR)

        # Perform template matching
        result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)

        # Filter results to only good ones
        threshold = 0.90  # Larger values have less, but better matches.
        (yCoords, xCoords) = np.where(result >= threshold)

        # Perform non-maximum suppression.
        template_h, template_w = template.shape[:2]
        rects = []
        for (x, y) in zip(xCoords, yCoords):
            rects.append((x, y, x + template_w, y + template_h))
        pick = non_max_suppression(np.array(rects))

        # print("matchFiltered", pick, img_target)

        # Optional: Visualize the results
        for (startX, startY, endX, endY) in pick:
            cv2.rectangle(image, (startX, startY),
                          (endX, endY), (0, 255, 0), 2)
        # cv2.imshow('Results'+img_target.split("assets/matches/")[0], image)

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
                    # extract the gameStates text itself along with the confidence of the text localization
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
                        # cv2.imshow("gameStates_THRESH", img_gray)
                        # print("TESSERACT_DATA", data)

            found = newText
            if found != "" and found != None and found != self.lastText:
                # print("found", found)
                return found
            else:
                return None
        else:
            result = self.ocrService.reader(img_rgb)
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
        # cv2.imshow('gamestate_thresh', img_thresh)

        found = self.findText(img_rgb, img_thresh)
        if found != None:
            if found != self.lastText and found != "   " and found != "  " and found != " " and found != "" and found != None:
                self.lastText = found
                print("TEXT_FOUND", found)
                self.sendOscMessage("/menuitem", self.lastText)
        else:
            self.lastText = ""

    def FindSubImage(im1, im2):
        needle = cv2.imread(im1)
        haystack = cv2.imread(im2)

        result = cv2.matchTemplate(needle, haystack, cv2.TM_CCOEFF_NORMED)
        y, x = np.unravel_index(result.argmax(), result.shape)
        return x, y

    def debugCrop(self, img_target):
        # Load the image and template
        image = cv2.imread(img_target, cv2.IMREAD_COLOR)

        image = image[40:120, 520:600]

        # cv2.imshow('Results', image)


gameStates = GAMESTATES()


def debugger():
    # cv2 read file image as grayscale
    # img_bgr = cv2.imread('assets/gamestates_ref/143941_home.png')
    # # show image
    # cv2.imshow('gamestate_bgr', img_bgr)
    # # convert to rgb
    # img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    # # show image
    # cv2.imshow('gamestate_rgb', img_rgb)
    # # destroy all windows on key press

    # gameStates.debugCrop('assets/gamestates_ref/144303_sideselect.png')

    gameStates.getRadarArrowLegacy('assets/gamestates_ref/012532_gameplay_terror.png',
                                   'assets/matches/gameplay_radararrow_transp.png')

    # gameStates.matchFiltered(
    #     'assets/gamestates_ref/144012_home_settings_new.png', 'assets/matches/home_gamestate_settings.png')

    # gameStates.matchFiltered(
    #     'assets/gamestates_ref/144322_playing_menu_home.png', 'assets/matches/home_gamestate_settings.png')

    while True:
        # gameStates.processText(img_bgr, img_rgb)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()
    pass


# debugger()
