from PIL import Image, ImageEnhance, ImageFilter
from math import atan2, cos, sin, sqrt, radians, pi, sqrt
from threading import Timer, Thread
import math
import numpy as np
import scipy.signal as ss
import cv2
import json
import sys
import os
import time
import data
import imutils
import random
import pytesseract
from pytesseract import Output
import pyautogui
import re
import textdistance
from utils import getRelativeCoords, resource_path


class SCREENCREADER ():
    def __init__(self, parentREF, callback=None, devMode=False, ocrService=None):
        self.send = callback
        self.devMode = devMode
        self.ocrService = ocrService
        self.showWindows = False
        self.lastText = "None"
        self.clearTimer = None
        self.lastAddress = None
        self.parentREF = parentREF
        self.medianBlur = 5
        self.threshParam1 = 180
        self.threshParam2 = 255
        self.dirname = os.path.dirname(__file__)
        self.topMenu = []
        self.subTopMenu = []
        self.topIcons = []
        self.subMenu = []
        self.footerMenu = []
        self.ocrThreads = []
        self.useOCR = False
        self.useTemplate = True
        self.getTags()
        self.engine = None
        self.useTemplateMap = True
        self.categories = [
            {
                "name": "topmenu",
                "items": self.topMenu,
                "selected": "None",
                "coords": None,
                "cropped": None
            },
            {
                "name": "subtopmenu",
                "items": self.subTopMenu,
                "selected": "None",
                "coords": None,
                "cropped": None
            },
            {
                "name": "topicons",
                "items": self.topIcons,
                "selected": "None",
                "coords": None,
                "cropped": None
            },
            {
                "name": "submenu",
                "items": self.subMenu,
                "selected": "None",
                "coords": None,
                "cropped": None
            },
            {
                "name": "footeractions",
                "items": self.footerMenu,
                "selected": "None",
                "coords": None,
                "cropped": None
            }
        ]

        self.h_screenreader = 60
        self.s_screenreader = 110
        self.v_screenreader = 0
        self.h2_screenreader = 140
        self.s2_screenreader = 140
        self.v2_screenreader = 255

        self.currentTemplate = None

        self.pathToTesseract = os.path.join(
            self.dirname, "tesseract")
        # pytesseract.pytesseract.tesseract_cmd = r'' + \
        #     str(self.pathToTesseract)+'/tesseract.exe'
        pytesseract.pytesseract.tesseract_cmd = resource_path(
            'tesseract/tesseract.exe')

        self.useTesseract = False

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, item, value):
        return setattr(self, item, value)

    def updateCategoryByIndex(self, index, value):
        self.categories[index] = value

    def getTags(self):
        # list all files in directory
        files = os.listdir(os.path.join(self.dirname, "assets/matches"))
        # filter results
        files = [f for f in files if f.endswith(".png")]
        for file in files:
            split = file.split("_")
            # print("SPLIT::::", split)
            # check if topmenu file
            if split[0] != "sr":
                continue
            if split[1] != "home":
                continue
            if split[2] == "topmenu":
                tag = split[3]
                model = {
                    "tag": tag,
                    "x": split[4],
                    "y": split[5],
                    "file": file
                }
                self.topMenu.append(model)
                # print("TAGS_MODEL", model)
            if split[2] == "subtopmenu":
                tag = split[3]
                model = {
                    "tag": tag,
                    "x": split[4],
                    "y": split[5],
                    "file": file
                }
                self.subTopMenu.append(model)
                # print("TAGS_MODEL", model)
            if split[2] == "topicons":
                tag = split[3]
                model = {
                    "tag": tag,
                    "x": split[4],
                    "y": split[5],
                    "file": file
                }
                self.topIcons.append(model)
                # print("TAGS_MODEL", model)
            if split[2] == "submenu":
                tag = split[3]
                model = {
                    "tag": tag,
                    "x": split[4],
                    "y": split[5],
                    "file": file
                }
                self.subMenu.append(model)
                # print("TAGS_MODEL", model)
            if split[2] == "footeractions":
                tag = split[3]
                model = {
                    "tag": tag,
                    "x": split[4],
                    "y": split[5],
                    "file": file
                }
                self.footerMenu.append(model)
                # print("TAGS_MODEL", model)
        # return list
        return files

    def doOCR(self, frame, category):

        if self.useTesseract:
            # convert to rgb
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            try:
                data = pytesseract.image_to_data(
                    img_rgb, output_type=Output.DICT, lang='eng', config='--psm 7')
            except Exception as e:
                with open("error.txt", "w") as e:
                    e.write(sys.exc_info()[1])

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
                    if conf > 50:
                        print("Confidence: {}".format(conf))

                        text = ' '.join(re.findall(r'\b(\w+)\b', text.lower()))
                        print("Text: {}".format(text))
                        # check if tag exists in self.topMenu
                        for item in self.topMenu:
                            if item["tag"] == text:
                                print("found", item["tag"])
                                self.concludeDetection(
                                    "/screenreader/"+str(category)+"", item["tag"])
                                return True
                            distance = textdistance.hamming.normalized_similarity(
                                item["tag"], text)
                            if distance > 0.5:
                                print("distance", distance, text, item["tag"])
                                self.concludeDetection(
                                    "/screenreader/"+str(category)+"", item["tag"])
                                return True
        else:
            result = self.ocrService.reader(frame)
            if len(result) > 0:
                self.concludeDetection(
                    "/screenreader/"+str(category)+"", result[0][1])
                return True

    def doMatch(self, frame, template, x, y, category, tag, checkSelected=False):
        # print("doMatch", frame.shape, template.shape)
        # Apply template Matching
        # assert frame.shape[0] > template.shape[0]
        # assert frame.shape[1] > template.shape[1], "frame width must be greater than template width"
        if template.shape[0] > frame.shape[0] or template.shape[1] > frame.shape[1]:
            return False
        res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        threshold = 0.8
        loc = np.where(res >= threshold)
        # print("loc", loc)
        w, h = template.shape[::-1]
        for pt in zip(*loc[::-1]):
            # print("pt", pt)
            # cv2.rectangle(frame, pt, (pt[0] + w, pt[1] + h), (0, 0, 255), 2)
            # cv2.putText(frame, tag, (0, h - 5),
            #             cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
            # cv2.imshow('Detected', frame)
            if checkSelected == True:
                return tag
            if category is not None:
                self.concludeDetection("/screenreader/"+str(category)+"", tag)
            return True
        return False

    def checkTemplate(self, frame, category, checkSelected=False):
        # print("checkTemplate", frame.shape)

        found = False

        for cat in self.categories:
            if cat["name"] == category:
                for item in cat["items"]:
                    template = cv2.imread(os.path.join(
                        self.dirname, "assets/matches/"+item["file"]), 0)

                    found = self.doMatch(frame, template,
                                         item["x"], item["y"], category, item["tag"], checkSelected)
                    if checkSelected == True and found is not False:
                        return found
        return found

    def clearLastText(self):
        self.lastText = "None"

    def concludeDetection(self, topic, value):
        if self.lastText != value:
            self.lastText = value
            # print("concludeDetection", topic, value)
            if self.send is not None:
                self.send(topic, value)
            # clear lastText after 10 seconds
            if self.clearTimer is not None:
                self.clearTimer.cancel()
            self.clearTimer = Timer(10, self.clearLastText).start()

    def cropWhitePixels(self, frame):
        # convert to gray
        gray = frame

        # threshold input image
        thresh = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)[1]

        # blacken right and bottom of image
        hh, ww = thresh.shape
        thresh[hh-2:hh, 0:ww] = 0
        thresh[0:hh, ww-1:ww] = 0

        # apply morphology close
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))
        mask = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # get contour
        cntrs = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cntrs = cntrs[0] if len(cntrs) == 2 else cntrs[1]
        try:
            # check cntrs range to avoid error
            # assert len(cntrs) > 0, "no contours found"
            if len(cntrs) > 0 and cntrs[0] is not None:
                c = cntrs[0]
            else:
                return [frame.copy(), (0, 0, 0, 0)]
        except:
            return [frame.copy(), (0, 0, 0, 0)]

        # get bounding box coordinates of contour
        x, y, w, h = cv2.boundingRect(c)

        # crop input
        result = frame.copy()
        result = frame[y:y+h, x:x+w]

        # save resulting masked image
        # cv2.imwrite('diff_image_cropped.jpg', result)
        return [result.copy(), (x, y, w, h)]

    def findSelectedItem(self, cropped, name):
        # filter blue color
        # define range of blue color in HSV
        lower_blue = np.array(
            [self.h_screenreader, self.s_screenreader, self.v_screenreader])
        upper_blue = np.array(
            [self.h2_screenreader, self.s2_screenreader, self.v2_screenreader])

        croppedHSV = cv2.cvtColor(cropped, cv2.COLOR_BGR2HSV)
        # Threshold the HSV image to get only blue colors
        mask = cv2.inRange(croppedHSV, lower_blue, upper_blue)

        # Bitwise-AND mask and original image
        newImage = cropped.copy()
        resultMasked = cv2.bitwise_and(newImage, newImage, mask=mask)

        resultMaskedCropped = resultMasked.copy()
        # remove all black pixels
        resultMaskedCropped[np.where((resultMaskedCropped == [0, 0, 0]).all(axis=2))] = [
            255, 255, 255]

        # convert to gray
        grayFromBlue = cv2.cvtColor(resultMaskedCropped, cv2.COLOR_BGR2GRAY)
        # threshold input image]
        thresh = cv2.threshold(
            grayFromBlue, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]

        # crop only black pixels~
        cropResult = self.cropWhitePixels(thresh)

        selectedMenuItem = cropResult[0]
        rectBox = cropResult[1]

        # create white image with same size as cropped
        expansion = 32
        whiteImage = np.zeros(
            (selectedMenuItem.shape[0]+expansion, selectedMenuItem.shape[1]+expansion, 3), np.uint8)
        whiteImage[:] = (255, 255, 255)
        # convert to gray
        grayFromWhite = cv2.cvtColor(whiteImage, cv2.COLOR_BGR2GRAY)
        # put selectedMenuItem on whiteImage
        grayFromWhite[expansion//2:expansion//2+selectedMenuItem.shape[0], expansion//2:expansion//2 +
                      selectedMenuItem.shape[1]] = selectedMenuItem
        selectedMenuItemCropped = grayFromWhite.copy()

        return [selectedMenuItemCropped, selectedMenuItem, rectBox]

        # # put text
        # cv2.putText(resultMasked, "_h_"+str(self.h_screenreader)+"_s_"+str(self.s_screenreader)+"_v_"+str(self.v_screenreader)+"", (10, 15),
        #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    def readerTopMenu(self, topMenuCropped, currentMouseX, currentMouseY):

        # threshold
        img_gray = cv2.cvtColor(topMenuCropped, cv2.COLOR_BGR2GRAY)
        # apply thresholding

        # img = cv2.medianBlur(img_gray, self.medianBlur)
        ret, img_thresh = cv2.threshold(
            img_gray, self.threshParam1, self.threshParam2, cv2.THRESH_BINARY_INV)

        # crop topMenuCropped based on mouse position
        croppedMouseOver = img_thresh.copy()

        startX = 0
        endX = 32
        offset = 16

        startY = 0
        endY = 16
        offsetHeight = 16

        if currentMouseX > 260:
            offset = 64

        if currentMouseY - offsetHeight > 0 and currentMouseY + offsetHeight < croppedMouseOver.shape[0]:
            startY = int(currentMouseY - offsetHeight)
            endY = int(currentMouseY + offsetHeight)
        if currentMouseX - offset > 0 and currentMouseX + offset < croppedMouseOver.shape[1]:
            startX = int(currentMouseX - offset)
            endX = int(currentMouseX + offset)
        croppedMouseOver = croppedMouseOver[0:
                                            croppedMouseOver.shape[0], startX:endX]
        if self.showWindows == True and self.devMode == True:
            cv2.imshow('readerTopMenu', img_thresh)
        prefix = "sr_home_topmenu_"
        if offset == 16:
            prefix = "sr_home_topicons_"
        # save image on keypress
        tag = "quit-to-desktop"
        file = ""+str(prefix)+""+str(tag)+"_"+str(startX)+"_"+str(endX)+""

        if cv2.waitKey(1) & 0xFF == ord('t'):
            print("saving", file)

            # crop only black pixels
            cropResult = self.cropWhitePixels(
                croppedMouseOver)

            croppedMouseOverCropped = cropResult[0]
            # rectBox = cropResult[1]

            cv2.imwrite(os.path.join(
                self.dirname, "assets/matches/"+file+"_c.png"), croppedMouseOverCropped)

            cv2.imwrite(os.path.join(
                self.dirname, "assets/matches/"+file+".png"), croppedMouseOver)

        category = prefix.split("_")[2]
        if currentMouseY < croppedMouseOver.shape[0]:
            if self.useOCR:
                if len(self.ocrThreads) > 5:
                    # stop the last thread
                    self.ocrThreads[-1].join()
                    self.ocrThreads.pop()

                self.ocrThreads.append(
                    Thread(target=self.doOCR, name="ocr-"+str(time.time())+"", args=(croppedMouseOver, category)))
                self.ocrThreads[-1].start()
            if self.useTemplate:
                self.checkTemplate(croppedMouseOver, category)
            if self.showWindows == True and self.devMode == True:
                cv2.imshow('croppedMouseOver', croppedMouseOver)

    def detectSelectedMenu(self, cropped, name, category):
        selectedItem, itemOriginal, rectBox = self.findSelectedItem(
            cropped, name)

        # check selected item
        selectedString = ""
        testString = self.checkTemplate(selectedItem, category, True)

        if testString != False:
            selectedString = testString
            print("selectedString", selectedString, category, rectBox)
            # find category and update selected
            for cat in self.categories:
                if cat["name"] == category:
                    cat["selected"] = selectedString
                    cat["coords"] = rectBox
                    cat["cropped"] = cropped
        else:
            for cat in self.categories:
                if cat["name"] == category:
                    print("selectedString", "None", category, rectBox)
                    cat["selected"] = "None"
                    cat["coords"] = None
                    cat["cropped"] = None

        return selectedString

    def readerHorizontalMenus(self, cropped, currentMouseX, currentMouseY, totalHeight, name, customOffset=0, visionMode="threshold"):
        prefix = "sr_home_"+str(name)+"_"
        selectedItem, itemOriginal, rectBox = self.findSelectedItem(
            cropped, name)

        # check selected item
        category = prefix.split("_")[2]
        selectedString = ""
        testString = self.checkTemplate(selectedItem, category, True)

        if testString != False:

            x = int(rectBox[0])
            y = int(rectBox[1])
            w = int(rectBox[2])
            h = int(rectBox[3])

            pointA = (x, y)
            pointB = (int(x+w), int(y+h))

            # create a copty of cropped
            croppedCopy = cropped.copy()
            # crop croppedCopy with rectBox
            croppedCopy = croppedCopy[y:y+h, x:x+w]

            # if self.showWindows == True and self.devMode == True:
            #     #

            #     cv2.imshow('selecteMenu_'+str(name)+'', selectedItem)
            #     # draw rectBox
            #     # create copy cropped
            #     img = np.copy(cropped)
            #     cv2.rectangle(img, pointA, pointB, (0, 255, 0), 1)
            #     cv2.imshow('selecteMenu_cropped_from', img)
            #     cv2.imshow('selecteMenu_cropped_original', itemOriginal)

            selectedString = testString
            # find category and update selected
            for cat in self.categories:
                if cat["name"] == category:
                    cat["selected"] = selectedString
                    cat["coords"] = rectBox
                    cat["cropped"] = croppedCopy

        # threshold
        img_gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
        # apply thresholding

        # img = cv2.medianBlur(img_gray, self.medianBlur)
        ret, img_thresh = cv2.threshold(
            img_gray, self.threshParam1, self.threshParam2, cv2.THRESH_BINARY_INV)

        # crop topMenuCropped based on mouse position
        croppedMouseOver = img_thresh.copy()
        if visionMode == "gray":
            croppedMouseOver = img_gray.copy()

        startX = 0
        endX = 260
        offset = 32

        startY = 0
        endY = 64
        offsetHeight = 16

        if customOffset > 0:
            offset = customOffset

        startY = int(currentMouseY - offsetHeight)
        endY = int(currentMouseY + offsetHeight)
        if startY < 0:
            startY = 0
        if endY > totalHeight:
            endY = totalHeight
        if currentMouseX - offset > 0 and currentMouseX + offset < croppedMouseOver.shape[1]:
            startX = int(currentMouseX - offset)
            endX = int(currentMouseX + offset)

        if endY - startY > 0:
            # croppedMouseOver = croppedMouseOver[startY:endY, startX:endX]
            croppedMouseOver = croppedMouseOver[0:croppedMouseOver.shape[0],
                                                startX:endX]
        else:
            croppedMouseOver = croppedMouseOver[0:croppedMouseOver.shape[0],
                                                startX:endX]
        # put text
        if self.showWindows == True and self.devMode == True:
            cv2.putText(img_thresh, "_y1_"+str(startY)+"_y2_"+str(endY)+"_s"+str(selectedString)+"", (10, 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

            cv2.putText(img_thresh, "_x1_"+str(startX)+"_x2_"+str(endX)+"", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
            cv2.imshow('readerHorizontalMenus', img_thresh)

            # save image on keypress
            # read text file
            with open('tag.txt', 'r') as file:
                data = file.read()

            tag = data
            file = ""+str(prefix)+""+str(tag)+"_"+str(startX)+"_"+str(endX)+""

            if cv2.waitKey(1) & 0xFF == ord('s'):
                with open('tag.txt', 'r') as file:
                    data = file.read()
                tag = data
                file = ""+str(prefix)+""+str(tag)+"_" + \
                    str(startX)+"_"+str(endX)+""
                print("saving", file)

                # crop only black pixels
                cropResult = self.cropWhitePixels(
                    croppedMouseOver)
                croppedMouseOverCropped = cropResult[0]
                # rectBox = cropResult[1]

                cv2.imwrite(os.path.join(
                    self.dirname, "assets/matches/"+file+"_c.png"), croppedMouseOverCropped)

                cv2.imwrite(os.path.join(
                    self.dirname, "assets/matches/"+file+".png"), croppedMouseOver)

                cv2.imwrite(os.path.join(
                    self.dirname, "assets/matches/"+file+".png"), selectedItem)

        if currentMouseY < totalHeight:
            if self.useOCR:
                if len(self.ocrThreads) > 5:
                    # stop the last thread
                    self.ocrThreads[-1].join()
                    self.ocrThreads.pop()

                self.ocrThreads.append(
                    Thread(target=self.doOCR, name="ocr-"+str(time.time())+"", args=(croppedMouseOver,)))
                self.ocrThreads[-1].start()
            if self.useTemplate:
                self.checkTemplate(croppedMouseOver, category)
            if self.showWindows == True and self.devMode == True:
                cv2.imshow('croppedMouseOverSub', croppedMouseOver)

    def checkActiveTemplate(self, selectables):
        if self.devMode == True and self.showWindows == True:
            newImage = np.zeros((300, 300, 3), np.uint8)
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.namedWindow('active_template', cv2.WINDOW_NORMAL)
            cv2.moveWindow('active_template', 100, 500)

        if len(selectables) > 0:
            # create a 300 x 300 empyu image

            # filter by active
            activeSectors = list(
                filter(lambda x: x['selected'] != 'None', selectables))

            if len(activeSectors) > 0:

                mappedFields = list(
                    map(lambda x: {
                        'name': x['name'],
                        'selected': x['selected']
                    }, activeSectors))

                # [{'name': 'subtopmenu', 'selected': 'practice'}, {'name': 'submenu', 'selected': 'wingman'}]

                # find currentTemplate in parsedTemplates
                # submenu filter
                submenu = next(
                    (index for (index, d) in enumerate(mappedFields) if d["name"] == 'submenu'), None)

                if submenu is not None:
                    submenu = mappedFields[submenu]
                    # print('submenu', submenu)

                subtopmenu = next(
                    (index for (index, d) in enumerate(mappedFields) if d["name"] == 'subtopmenu'), None)

                if subtopmenu is not None:
                    subtopmenu = mappedFields[subtopmenu]
                    # print('subtopmenu', subtopmenu)

                if submenu is not None and subtopmenu is not None:

                    if self.devMode == True and self.showWindows == True:
                        cv2.putText(newImage, 'subtopmenu: ' + subtopmenu['selected'] + ' _ submenu '+str(submenu['selected'])+'', (10, 10),
                                    font, 0.4, (0, 255, 0), 1, 1)

                    if subtopmenu['selected'] == "practice" and submenu['selected'] == "deathmatch":
                        self.currentTemplate = "144126_home_play_practice"
                    elif subtopmenu['selected'] == "practice" and submenu['selected'] == "casual":
                        self.currentTemplate = "144126_home_play_practice"
                    elif subtopmenu['selected'] == "practice" and submenu['selected'] == "competitive":
                        self.currentTemplate = "144126_home_play_practice"
                    elif subtopmenu['selected'] == "practice" and submenu['selected'] == "wingman":
                        self.currentTemplate = "031323_home_practice_wingman"
                    elif subtopmenu['selected'] == "matchmaking" and submenu['selected'] == "casual":
                        self.currentTemplate = "144113_home_play_match"
                    elif subtopmenu['selected'] == "matchmaking" and submenu['selected'] == "deathmatch":
                        self.currentTemplate = "144113_home_play_match"
                    else:
                        self.currentTemplate = None

                    # put text
                    if self.devMode == True and self.showWindows == True:
                        cv2.putText(newImage, 'currentTemplate: ' +
                                    str(self.currentTemplate)+'', (10, 30), font, 0.4, (0, 255, 0), 1, 1)

                        print('checkactive-template-found',
                              len(activeSectors), mappedFields, self.currentTemplate)
            else:
                self.currentTemplate = None
                if self.devMode == True and self.showWindows == True:
                    cv2.putText(newImage, 'NONE_ACTIVE'+str(len(selectables))+'', (10, 10),
                                font, 0.4, (0, 255, 0), 1, 1)
        else:
            self.currentTemplate = None
            if self.devMode == True and self.showWindows == True:
                cv2.putText(newImage, 'EMPTY___'+str(len(selectables))+'', (10, 10),
                            font, 0.4, (0, 255, 0), 1, 1)

        self.concludeDetection(
            "/screenreader/current-template", self.currentTemplate)
        # show image
        if self.devMode == True and self.showWindows == True:
            cv2.imshow('active_template', newImage)
            # wait for q key to close window]
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cv2.destroyAllWindows()

    def processScreenReader(self, frameFull):

        mousePos = pyautogui.position()
        currentMouseX = mousePos[0]
        currentMouseY = mousePos[1]

        totalWidth = frameFull.shape[1]
        totalHeight = frameFull.shape[0]

        # TOP MENU
        topMenuCoords = getRelativeCoords(
            [0, 0, totalWidth, 64], frameFull.shape[1], frameFull.shape[0])

        topMenuCropped = frameFull[topMenuCoords[0][1]:topMenuCoords[1]
                                   [1], topMenuCoords[0][0]:topMenuCoords[1][0]]

        if currentMouseY < topMenuCoords[1][1] and currentMouseY:
            self.readerTopMenu(topMenuCropped, currentMouseX,
                               currentMouseY)

        vertSections = [
            {
                "name": "topmenu",
                "coords": topMenuCoords,
                "startYCrop": 0,
                "endYCrop": 64,
                "customOffset": 0,
                "visionMode": "threshold",
                "selected": "None",
                "isSelectable": True
            },
            {
                "name": "subtopmenu",
                "coords": getRelativeCoords(
                    [0, 64, totalWidth, 113], frameFull.shape[1], frameFull.shape[0]),
                "startYCrop": 64,
                "endYCrop": 113,
                "customOffset": 0,
                "visionMode": "threshold",
                "selected": "None",
                "isSelectable": True
            },
            {
                "name": "submenu",
                "coords": getRelativeCoords(
                    [0, 114, totalWidth, 154], frameFull.shape[1], frameFull.shape[0]),
                "startYCrop": 114,
                "endYCrop": 154,
                "customOffset": 0,
                "visionMode": "threshold",
                "selected": "None",
                "isSelectable": True
            },
            {
                "name": "footeractions",
                "coords": getRelativeCoords(
                    [0, 1005, totalWidth, 1062], frameFull.shape[1], frameFull.shape[0]),
                "startYCrop": 1005,
                "endYCrop": 1062,
                "customOffset": 150,
                "visionMode": "gray",
                "selected": "None",
                "isSelectable": False
            },
            {
                "name": "cards_5x2",
                "coords": getRelativeCoords(
                    [0, 169, totalWidth, 968], frameFull.shape[1], frameFull.shape[0]),
                "startYCrop": 169,
                "endYCrop": 968,
                "customOffset": 0,
                "visionMode": "gray",
                "selected": "None",
                "isSelectable": False
            },
            # {
            #     "name": "cards_4x1",
            #     "coords": getRelativeCoords(
            #         [0, 169, totalWidth, 968], frameFull.shape[1], frameFull.shape[0]),
            #     "startYCrop": 169,
            #     "endYCrop": 968,
            #     "customOffset": 0,
            #     "visionMode": "gray",
            #     "isSelectable": False
            # }
        ]

        # iterate to selectable sections
        selectables = [x for x in vertSections if x["isSelectable"] == True]
        for section in selectables:
            # check if section has selected

            sectionSelectable = frameFull.copy()
            # CROP SECTION
            selectableStartYCrop = section["startYCrop"]
            selectableEndYCrop = section["endYCrop"]
            selectableName = section["name"]

            sectionCoords = getRelativeCoords(
                [0, selectableStartYCrop, totalWidth, selectableEndYCrop], sectionSelectable.shape[1], sectionSelectable.shape[0])

            selectableCrop = sectionSelectable[sectionCoords[0][1]:sectionCoords[1]
                                               [1], sectionCoords[0][0]:sectionCoords[1][0]]

            selectedString = self.detectSelectedMenu(
                selectableCrop, selectableName, selectableName)

            if selectedString == "workshop-maps" and section["name"] == "subtopmenu":
                self.currentTemplate = None

        self.checkActiveTemplate(self.categories)

        if self.currentTemplate == None:
            for section in vertSections:

                shouldSkip = False
                if section["name"] == "topmenu":
                    continue

                if section["name"] == "cards_5x2":
                    # iterate to categories and check if selected
                    for cat in self.categories:

                        if cat["name"] == "topmenu":
                            continue
                        if cat["name"] == "topicons":
                            continue
                        if cat["name"] == "footeractions":
                            continue
                        if cat["name"] == "subtopmenu":
                            if cat["selected"] != "None":
                                if cat["selected"] == "matchmaking":
                                    shouldSkip = True
                                if cat["selected"] == "practice":
                                    shouldSkip = True
                                if cat["selected"] == "workshop-maps":
                                    shouldSkip = True

                        if cat["name"] == "submenu":
                            if cat["selected"] != "None":
                                if cat["selected"] == "competitive":
                                    shouldSkip = False
                                if cat["selected"] == "wingman":
                                    shouldSkip = True
                                if cat["selected"] == "casual":
                                    shouldSkip = False
                                if cat["selected"] == "deathmatch":
                                    shouldSkip = True

                if shouldSkip == True:
                    continue

                sectionCopy = frameFull.copy()

                # CROP SECTION
                startYCrop = section["startYCrop"]
                endYCrop = section["endYCrop"]
                name = section["name"]
                customOffset = section["customOffset"]
                visionMode = section["visionMode"]
                subTopMenuCoords = getRelativeCoords(
                    [0, startYCrop, totalWidth, endYCrop], sectionCopy.shape[1], sectionCopy.shape[0])

                subTopMenuCropped = sectionCopy[subTopMenuCoords[0][1]:subTopMenuCoords[1]
                                                [1], subTopMenuCoords[0][0]:subTopMenuCoords[1][0]]

                if shouldSkip == False and currentMouseY > startYCrop and currentMouseY < endYCrop:
                    self.readerHorizontalMenus(
                        subTopMenuCropped, currentMouseX,
                        currentMouseY - startYCrop, sectionCopy.shape[0], name, customOffset, visionMode)

                    for cat in self.categories:
                        if cat["name"] == name:
                            section["selected"] = cat["selected"]

        # if self.useTemplateMap == True:

            # self.concludeDetection(
            #     "/screenreader/update-categories", self.categories)
            #
