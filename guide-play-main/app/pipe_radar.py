from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
from math import atan2, cos, sin, sqrt, radians, pi, sqrt
from threading import Timer, Thread
import concurrent.futures

from tracker import EuclideanDistTracker, distSignal
import math
import numpy as np
import scipy.signal as ss
from scipy import ndimage
import cv2
import json
import base64
import os
import time
import data
from io import BytesIO
from pydub.playback import play
from pydub import AudioSegment
from skimage.morphology import disk
from skimage.filters import threshold_otsu, threshold_local, rank
from skimage.filters.rank import mean, enhance_contrast_percentile, mean_bilateral
from skimage import exposure
from skimage import img_as_ubyte
from utils import read_transparent_png, lerp
from pipe_contrast import adjust_gamma, process_image
from mjpeg_streamer import MjpegServer, Stream


Winname = "Adjustable"


def printTrackBars(props=[]):
    # print("H", cv2.getTrackbarPos('H', Winname))
    # print("S", cv2.getTrackbarPos('S', Winname))
    # print("V", cv2.getTrackbarPos('V', Winname))
    # print("H2", cv2.getTrackbarPos('H2', Winname))
    # print("S2", cv2.getTrackbarPos('S2', Winname))
    # print("V2", cv2.getTrackbarPos('V2', Winname))
    # create json model hsv
    # hsvModel = {
    #     "H": cv2.getTrackbarPos('h', Winname),
    #     "S": cv2.getTrackbarPos('s', Winname),
    #     "V": cv2.getTrackbarPos('v', Winname),
    #     "H2": cv2.getTrackbarPos('h2', Winname),
    #     "S2": cv2.getTrackbarPos('s2', Winname),
    #     "V2": cv2.getTrackbarPos('v2', Winname)
    # }
    # create json from props list
    hsvModel = {}
    for prop in props:
        print("getting prop", prop)
        hsvModel[prop] = cv2.getTrackbarPos(prop, Winname)

    # print json
    print(json.dumps(hsvModel, indent=4))

    pass


def compute_rotation(self, angle, angleCorrected, image):
    # print(situation + '\n '+ signal)
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(image, self.cardinal, (10, 20), font, 0.5, (0, 0, 255), 1)

    # if angleCorrected < 0:
    #     angleCorrected = 360 + angleCorrected
    # if angleCorrected > 360:
    #     angleCorrected = angleCorrected - 360
    # if angleCorrected == 360:
    #     angleCorrected = 0
    if self.cardinal == "SOUTH_90-":
        angleCorrected = angleCorrected + 180
    if self.cardinal == "EAST_90-":
        angleCorrected = angleCorrected
    if self.cardinal == "EAST_90_0":
        angleCorrected = 90 + abs(angleCorrected)
    if self.cardinal == "WEST_90-":
        # invert angle
        angleCorrected = 180 - angleCorrected
        angleCorrected = 180 + angleCorrected
    if self.cardinal == "WEST_90_0":
        angleCorrected = 270 + abs(angleCorrected)
    if self.cardinal == "WEST_90+":
        angleCorrected = 180 - angleCorrected
        angleCorrected = 180 + angleCorrected

    cv2.putText(image, str(angle), (10, 40), font, 0.5, (0, 0, 255), 1)

    cv2.putText(image, "c_"+str(angleCorrected),
                (10, 60), font, 0.5, (0, 0, 255), 1)


def processTriangle(self, image):
    angle = 0

    # arrow angle detection algorithm
    if image is None:
        return None, None
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # GaussianBlur()
    blur = cv2.GaussianBlur(gray, (9, 9), 2, 2)
    ret, thresh = cv2.threshold(
        blur, 127, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    kernel = np.ones((5, 5), np.uint8)
    erosion = cv2.erode(thresh, kernel, iterations=1)
    dilation = cv2.dilate(erosion, kernel, iterations=1)
    contours, hierarchy = cv2.findContours(
        dilation, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    # print("contours large " + str(len(contours)))
    if len(contours) == 2:
        # print("Found 2 contours")
        maxX = 0
        maxI = 0
        i = 0
        for cont in contours:
            mu = cv2.moments(cont)
            if mu['m00'] > 100.0:
                # cv2.drawContours(image, [cont], 0, (255,0,255), 3)
                x, y, w, h = cv2.boundingRect(cont)
                if i == 0:
                    maxX = x
                else:
                    maxI = i if x > maxX else maxI

            i = i+1
        # new algorithm - CIRCLE ALGO 26-09-2018 to get direction of arrow
        # print("1 contour detected");
        pointarrray = contours[maxI]
        (x, y), radius = cv2.minEnclosingCircle(pointarrray)
        # cv2.drawContours(image, pointarrray, -1, (255,255,0), 2)
        center = (int(x), int(y))
        rad = int(radius)
        rad = rad-5

        # cv2.circle(image,center,rad,(255, 128, 255),2)

        # find the best contour
        # print("contours small " + str(len(contours)))

        corners = []
        for p in pointarrray:
            # if selected_contour is not None:
            # print("Found 1 contour", selected_contour)
            # p = selected_contour
            point = (p[0][0], p[0][1])
            # print pt
            # cv2.circle(im,pt,5,(200,0,0),2)
            selected_triangles = []

            leftV = (point[1]-center[1])*(point[1]-center[1]) + \
                (point[0]-center[0])*(point[0]-center[0])
            if leftV > rad*rad:
                corners.append(point)
                # System.out.println("hi"+point.x+" "+point.y);
            # print("corners  " + str(len(corners)))
            p1x = 0
            p1y = 0
            pn1 = 0
            p2x = 0
            p2y = 0
            pn2 = 0
            p3x = 0
            p3y = 0
            pn3 = 0
            # print("Found corners", len(corners))
            if len(corners) > 3:
                p1x = corners[0][0]
                p1y = corners[0][1]
                pn1 = pn1+1
                offset = 10
                for corner in corners:
                    cornerX = corner[0]
                    cornerY = corner[1]
                    if (cornerX < p1x/pn1+offset) and (cornerX > p1x/pn1-offset) and (cornerY < p1y/pn1+offset) and (cornerY > p1y/pn1-offset):
                        p1x = p1x+cornerX
                        p1y = p1y+cornerY
                        pn1 = pn1+1
                    else:
                        if pn2 == 0:
                            p2x = cornerX
                            p2y = cornerY
                            pn2 = pn2+1
                        elif (cornerX < p2x/pn2+offset) and (cornerX > p2x/pn2-offset) and (cornerY < p2y/pn2+offset) and (cornerY > p2y/pn2-offset):
                            p2x = p2x+cornerX
                            p2y = p2y+cornerY
                            pn2 = pn2+1
                        else:
                            if pn3 == 0:
                                p3x = cornerX
                                p3y = cornerY
                                pn3 = pn3+1
                            elif (cornerX < p3x/pn3+offset) and (cornerX > p3x/pn3-offset) and (cornerY < p3y/pn3+offset) and (cornerY > p3y/pn3-offset):
                                p3x = p3x+cornerX
                                p3y = p3y+cornerY
                                pn3 = pn3+1
                if pn1 > 0 and pn2 > 0 and pn3 > 0:
                    p1x /= pn1
                    p2x /= pn2
                    p3x /= pn3
                    p1y /= pn1
                    p2y /= pn2
                    p3y /= pn3

                    # print("corner point1 = " + str(p1x)+","+str(p1y))
                    # print("corner point2 = " + str(p2x)+","+str(p2y))
                    # print("corner point3 = " + str(p3x)+","+str(p3y))
                    if p1x and p2x and p3x and p1y and p2y and p3y:
                        cv2.circle(image, (int(p1x), int(p1y)),
                                   6, (0, 0, 255), -1)
                        # cv2.circle(image,(int(p2x),int(p2y)),4,(0, 0, 255),2)
                        # cv2.circle(image,(int(p3x),int(p3y)),4,(0, 0, 255),2)

                        length1_2 = (p1x - p2x)*(p1x - p2x) + \
                            (p1y - p2y)*(p1y - p2y)
                        length2_3 = (p2x - p3x)*(p2x - p3x) + \
                            (p2y - p3y)*(p2y - p3y)
                        length3_1 = (p3x - p1x)*(p3x - p1x) + \
                            (p3y - p1y)*(p3y - p1y)

                        # print("length1_2 = " + str(length1_2))
                        # print("length2_3 = " + str(length2_3))
                        # print("length3_1 = " + str(length3_1))

                        directedX = 0
                        directedY = 0
                        if length1_2 <= length2_3:
                            if length3_1 < length1_2:
                                directedX = p2x
                                directedY = p2y
                            else:
                                directedX = p3x
                                directedY = p3y
                        else:
                            if length3_1 < length2_3:
                                directedX = p2x
                                directedY = p2y
                            else:
                                directedX = p1x
                                directedY = p1y
                        # cv2.circle(image,(int(directedX),int(directedY)),5,(0, 0, 255),2)

                        numer = y-directedY  # numerator
                        denom = x-directedX  # denominator
                        if denom != 0:
                            angle = np.absolute(
                                np.degrees(np.arctan(numer/denom)))
                        else:
                            angle = 90
                        # print("angle "+str(angle));
                        turnningSignal = ""
                        angle = int(angle)
                        angleCorrected = angle
                        if angle < 8 and denom < 0:
                            turnningSignal = "EAST_90_0"
                        elif angle < 8 and denom > 0 and angle not in range(4, 95):
                            turnningSignal = "WEST_90_0"
                        elif angle > 82 and numer > 0 and angle not in range(85, 95):
                            turnningSignal = "NORTH_90+"
                            angleCorrected = 90-angle
                        elif angle > 82 and numer < 0:
                            turnningSignal = "SOUTH_90-"
                            angleCorrected = 90-angle
                        elif numer > 0 and denom < 0:
                            turnningSignal = "EAST_90+"
                            angleCorrected = 90-angle
                        elif numer > 0 and denom > 0:
                            turnningSignal = "WEST_90+"
                            angleCorrected = 90-angle
                        elif numer < 0 and denom < 0:
                            turnningSignal = "EAST_90-"
                            angleCorrected = 90+angle
                        elif numer < 0 and denom > 0:
                            turnningSignal = "WEST_90-"
                            angleCorrected = 90+angle

                        # clear image
                        # image = np.zeros_like(image)

                        self.AngleTriangle = angleCorrected
                        self.cardinal = turnningSignal

    return angle


def createTriangle(target):
    # Some dummy image
    # img = cv2.fillPoly(img=np.zeros((500, 500, 3), np.uint8),
    #                 pts=np.array([[[200, 100], [400, 200], [300, 300]]]),
    #                 color=(0, 0, 255))

    # img = target.copy()
    # blank image with target shape
    imgBasic = np.zeros((target.shape[0] * 2, target.shape[1]*2, 3), np.uint8)
    # white background
    imgBasic = cv2.bitwise_not(imgBasic)
    # create image with doubled size
    img = np.zeros((target.shape[0], target.shape[1], 3), np.uint8)
    # overlay target to img center
    img[img.shape[0] // 2 - target.shape[0] // 2:img.shape[0] // 2 + target.shape[0] // 2,
        img.shape[1] // 2 - target.shape[1] // 2:img.shape[1] // 2 + target.shape[1] // 2] = target

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # gray = np.float32(gray)
    # corners = cv2.cornerHarris(gray,2,5,0.04)
    # corners = cv2.dilate(corners,None)
    # img[corners>0.10*corners.max()]=[0,0,255]

    # Find only external contours in grayscale converted image
    contours, _ = cv2.findContours(
        gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    if len(contours) == 0:
        # print('No contours found')
        return
    # Find triangle vertices of minimum area enclosing contour
    cnt = max(contours, key=cv2.contourArea)
    _, triangle = cv2.minEnclosingTriangle(cnt)
    pts = np.int32(np.squeeze(np.round(triangle)))
    # print('\nminEnclosingTriangle: \n', pts)

    # Refine/improve triangle vertices (if wanted)
    idx = [np.argmin(np.linalg.norm(cnt - pt, axis=2)) for pt in pts]
    pts = np.int32(np.squeeze(cnt[idx]))
    # print('\nRefined: \n', pts)

    # draw triangle
    img = cv2.polylines(img, [pts], True, (255, 255, 0), 1)
    # fill triangle
    img = cv2.fillPoly(img, [pts], (255, 255, 0))

    triangleVector = np.zeros((target.shape[0], target.shape[1], 3), np.uint8)
    triangleVector = cv2.bitwise_not(triangleVector)

    triangleVector = cv2.polylines(
        triangleVector, [pts], True, (255, 255, 0), 1)
    # fill triangle
    triangleVector = cv2.fillPoly(triangleVector, [pts], (255, 255, 0))
    # overlay triangleVector to imgBasic center
    imgBasic[imgBasic.shape[0] // 2 - triangleVector.shape[0] // 2:imgBasic.shape[0] // 2 + triangleVector.shape[0] // 2,
             imgBasic.shape[1] // 2 - triangleVector.shape[1] // 2:imgBasic.shape[1] // 2 + triangleVector.shape[1] // 2] = triangleVector

    # find the tip of the triangle
    tip = pts[np.argmin(np.sum(pts, axis=1))]
    # print('\nTip: \n', tip)
    # draw tip
    img = cv2.circle(img, tuple(tip), 3, (0, 255, 0), -1)

    # Find index of "top" vertex by finding unique edge lengths; "top" has less than the two base vertices
    idx = np.argmin(
        [np.size(np.unique(np.linalg.norm(pts - pt, axis=1))) for pt in pts])
    top = pts[idx]
    # draw top
    img = cv2.circle(img, tuple(top), 3, (0, 0, 255), -1)

    # Find mid point of the base vertices
    base = np.array([pts[i] for i in np.arange(3) if i != idx])
    base_mid = np.int32(np.round(np.mean(base, axis=0)))

    # Draw angle bisector line
    img = cv2.line(img, tuple(top), tuple(base_mid), (0, 255, 0), 2)

    # overlay img on img2 center
    # img2[img2.shape[0]//2-img.shape[0]//2:img2.shape[0]//2+img.shape[0]//2,
    #     img2.shape[1]//2-img.shape[1]//2:img2.shape[1]//2+img.shape[1]//2] = img

    return imgBasic


def MeasuresForArrow(gray, source, previousAngle, radius):
    img = source.copy()
    # white image for drawing
    cimg = np.zeros_like(img)
    rimg = np.zeros_like(img)
    gimg = np.zeros_like(img)
    factor = 3
    compassCenter = gimg.shape[0] // factor // 2
    globalAngle = previousAngle
    # round
    compassCenter = int(compassCenter + 2)
    compassRadius = gimg.shape[0] // factor // 2

    useSmoothing = False

    def convertAngle(angle, currentAngle):
        finalAngle = str(currentAngle)
        newAngle = currentAngle
        degrees = int(np.rad2deg(angle))

        # print("degrees_RAW", degrees)

        if degrees - 90 < 0:
            newAngle = str(360 + degrees - 90)
        elif degrees - 90 > 360:
            newAngle = str(degrees - 90 - 360)
        elif degrees - 90 == 360:
            newAngle = str(0)
        elif degrees - 90 < 0:
            newAngle = str(360 + degrees - 90)
        elif degrees - 90 > 360:
            newAngle = str(degrees - 90 - 360)
        elif degrees > 360:
            newAngle = str(degrees - 360)
        elif degrees - 90 > 0 and degrees - 90 < 90:
            newAngle = str(degrees - 90)
        else:
            print("degrees_RAW", degrees)
            # newAngle = str(degrees - 90)

        if useSmoothing:
            # apply smoothing between previous angle and new angle
            if int(newAngle) < int(currentAngle):
                finalAngle = str(int((int(newAngle) - int(currentAngle)) / 2))
            else:
                finalAngle = str(int((int(newAngle) + int(currentAngle)) / 2))
        else:
            finalAngle = newAngle
        return finalAngle

    # draw a circle on each 10 degrees of the circle
    degreeTicks = []
    for i in range(0, 360, 10):
        x = int(compassCenter + radius // factor * math.cos(math.radians(i)))
        y = int(compassCenter + radius // factor * math.sin(math.radians(i)))

        extra = 6
        # create bounding box
        x1 = x - extra
        y1 = y - extra
        x2 = x + extra
        y2 = y + extra
        degreeTicks.append([x1, y1, x2, y2])

    # draw bunding boxes on gimg
    for i in range(len(degreeTicks)):
        cv2.rectangle(img, (degreeTicks[i][0], degreeTicks[i][1]),
                      (degreeTicks[i][2], degreeTicks[i][3]), (0, 0, 255), -1)

    # draw a circle on gimg
    cv2.circle(img, (compassCenter, compassCenter),
               int(radius // factor), (255, 255, 255), 1)
    # font
    font = cv2.FONT_HERSHEY_SIMPLEX
    fontScale = 0.5
    fontColor = (255, 0, 0)
    lineType = 1

    # apply gaussian blur
    gray = cv2.GaussianBlur(gray, (11, 11), 0)

    # MEASURES START
    edges = cv2.Canny(gray, 200, 100)
    edges = cv2.dilate(edges, None, iterations=1)
    edges = cv2.erode(edges, None, iterations=1)

    # Contours detection
    contours, _ = cv2.findContours(
        edges.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # for cnt in contours:
    if len(contours) > 0:
        # cnt = max(contours, key=cv2.contourArea)
        cnt = max(contours, key=lambda x: cv2.contourArea(x))
        approx = cv2.approxPolyDP(cnt, 0.08 * cv2.arcLength(cnt, True), True)
        area = cv2.contourArea(approx)

        # coordinate
        x = approx.ravel()[0]
        y = approx.ravel()[1]
        # print("X__", x)
        # print("area__", area)
        # find the center
        M = cv2.moments(approx)
        cX, cY = 0, 0
        if M["m00"] != 0:
            cX = int(M["m10"]/M["m00"])
            cY = int(M["m01"]/M["m00"])
        else:
            cX, cY = 0, 0
        # print("cX", cX)
        # print("cY", cY)

        if area > 5:
            cimg = cv2.drawContours(
                img, [approx], 0, (0, 0, 255), 2)  # 5 is thickness
            rimg = cv2.fillPoly(cimg.copy(), pts=[cnt], color=(180, 180, 180))
            cv2.fillPoly(cimg, pts=[cnt], color=(180, 180, 180))
            cv2.fillPoly(cimg, pts=[approx], color=(255, 0, 180))
            x, y, w, h = cv2.boundingRect(cnt)
            # cv2.rectangle(cimg, (x, y), (x + w, y + h), (0, 255,0), 2)
            center = (x, y)
            # cv2.circle(cimg, center, 5, (0, 0, 255), -1)

            # print("APROX_SIZE", len(approx))
            # if len(approx) == 3:

            #     cv2.putText(img,"Triangle",(cX,cY),font,1,(180,0,120))
            if len(approx) >= 3:
                # cv2.putText(img,"Rectangle",(cX,cY),font,1,(180,0,120))
                # draw line from center to contour
                # cv2.line(img, (cX, cY), (x, y), (0, 255, 0), 2)
                # calculate angle
                angle = math.atan2(cY - y, cX - x)
                # calculate sub angle
                subAngle = str(int(np.rad2deg(angle)) - 90)
                # normalize sub angle
                # if int(subAngle) < 0:
                #     subAngle = str(360 + int(subAngle))
                # if int(subAngle) > 360:
                #     subAngle = str(int(subAngle) - 360)
                # if int(subAngle) == 360:
                #     subAngle = str(0)
                # draw angle text
                # cv2.putText(img, "subd_"+str(subAngle), (cX - 20, cY - 20), font, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
                # find the most distant points on the contour
                extLeft = tuple(approx[approx[:, :, 0].argmin()][0])
                extRight = tuple(approx[approx[:, :, 0].argmax()][0])
                extTop = tuple(approx[approx[:, :, 1].argmin()][0])
                if len(approx) > 3:
                    extBot = tuple(approx[approx[:, :, 1].argmax()][0])
                # draw the points
                cv2.circle(img, extLeft, 5, (0, 0, 255), -1)
                cv2.circle(img, extRight, 5, (0, 255, 0), -1)
                cv2.circle(img, extTop, 5, (255, 0, 0), -1)
                if len(approx) > 3:
                    cv2.circle(img, extBot, 5, (255, 255, 0), -1)

                # draw the center of the contour
                cv2.circle(img, (cX, cY), 3, (255, 255, 255), -1)

                cv2.putText(img, "L_"+str(extLeft[0])+"_"+str(
                    extLeft[1])+"", (155+extLeft[0], extLeft[1]), font, fontScale, (0, 0, 255), lineType)
                cv2.putText(img, "R_"+str(extRight[0])+"_"+str(
                    extRight[1])+"", (155+extRight[0], extRight[1]), font, fontScale, (0, 255, 0), lineType)
                cv2.putText(img, "T_"+str(extTop[0])+"_"+str(
                    extTop[1])+"", (155+extTop[0], extTop[1]), font, fontScale, (255, 0, 0), lineType)
                if len(approx) > 3:
                    cv2.putText(img, "B_"+str(extBot[0])+"_"+str(
                        extBot[1])+"", (155+extBot[0], extBot[1]), font, fontScale, (255, 255, 0), lineType)
                # find the centroid point(xc, yc),
                # then calculate the distance to all contour points,
                # then find the slope of all lines passing by centroid and contour points from line equation
                #  mp= (yp-yc)/(xp-xc),
                # the points that has the same slope belong to the same line,
                # so you sum their distances, and finally find the max total distance.

                # draw the line length
                # compute the distance between the points (x1, y1) and (x2, y2)
                centroid = (cX, cY)
                for p in approx:

                    # draw a white line from centroid to contour point
                    cv2.line(img, centroid, tuple(p[0]), (255, 255, 0), 2)
                    # check if line intersects with degreeTicks
                    for i in range(len(degreeTicks)):
                        # print("degreeTicks[i]", degreeTicks[i])
                        # print("p[0]", p[0])
                        if degreeTicks[i][0] <= p[0][0] <= degreeTicks[i][2] and degreeTicks[i][1] <= p[0][1] <= degreeTicks[i][3]:
                            # print("INTERSECTS")
                            # draw line from center to contour
                            cv2.line(img, (cX, cY),
                                     (p[0][0], p[0][1]), (0, 0, 255), 3)
                            # draw bounding box
                            cv2.rectangle(img, (degreeTicks[i][0], degreeTicks[i][1]), (
                                degreeTicks[i][2], degreeTicks[i][3]), (0, 255, 255), 1)
                            # calculate angle
                            angle = math.atan2(cY - p[0][1], cX - p[0][0])
                            # convert globalAngle to 360 degrees
                            globalAngle = convertAngle(angle, int(globalAngle))
                            # draw the globalAngle
                            # cv2.putText(img, globalAngle), (p[0][0] - 20, p[0][1] - 20), font, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                            # draw the globalAngle text
                            cv2.putText(img, str("____g_"+str(globalAngle)+""),
                                        (p[0][0], p[0][1]), font, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
                    # check if intersects with degreeTicks
                    for i in range(len(degreeTicks)):
                        # print("degreeTicks[i]", degreeTicks[i])
                        # print("p[0]", p[0])
                        if degreeTicks[i][0] <= p[0][0] <= degreeTicks[i][2] and degreeTicks[i][1] <= p[0][1] <= degreeTicks[i][3]:
                            # print("INTERSECTS")
                            # draw line from center to contour
                            cv2.line(img, (cX, cY),
                                     (p[0][0], p[0][1]), (0, 0, 255), 3)
                            # calculate angle
                            angle = math.atan2(cY - p[0][1], cX - p[0][0])
                            # convert globalAngle to 360 degrees
                            globalAngle = convertAngle(angle, int(globalAngle))

                    # cv2.line(img, centroid, tuple(p[0]), (255, 0, 120), 1)
                    # cv2.putText(img, str("p_"+str(p[0])+"") ,(155+tuple(p[0])[0],180+tuple(p[0])[1]),font, fontScale, (0, 120, 180), lineType)

                cv2.putText(img, str("c_"+str(centroid)+""), (155, 220),
                            font, fontScale, (0, 120, 180), lineType)

                # display the line length
                # compute the distance between the points (x1, y1) and (x2, y2)
                if len(approx) > 3:
                    yDist = int(
                        math.sqrt(((extBot[0]-extTop[0])**2)+((extBot[1]-extTop[1])**2)))
                    cv2.putText(img, str("yDist_"+str(yDist)+""),
                                (155, 240), font, fontScale, (0, 120, 180), lineType)

                xDist = int(
                    math.sqrt(((extLeft[0]-extRight[0])**2)+((extLeft[1]-extRight[1])**2)))
                cv2.putText(img, str("xDist_"+str(xDist)+""),
                            (155, 260), font, fontScale, (0, 180, 120), lineType)

                # draw the globalAngle text
                cv2.putText(img, str("g_"+str(globalAngle)+""),
                            (155, 280), font, 0.5, (0, 255, 255), 1, cv2.LINE_AA)

                # draw the distance text
                # cv2.putText(img,str(extLeft),(155,100),font, fontScale, fontColor, lineType)
            else:
                cv2.putText(img, "xy", (cX, cY), font, 0.3, (180, 0, 120))
    # cv2.imshow("MeasuresForArrow", img)
    # clear frame
    img = source.copy()
    # crop
    rimg = rimg[0:120, 0:120]
    return rimg.copy(), globalAngle


def normalizeRadarPlot(x, y, radar, showAngle=False):

    # print("normalizeRadarPlot", x, y)
    radarWidth = radar.shape[1]
    radarHeight = radar.shape[0]
    radarCenter = [radarWidth // 2, radarHeight // 2]

    # print("radarCenter", radarCenter)

    finalX = radarCenter[0]
    finalY = radarCenter[1]

    if (x > 0):
        finalX = radarCenter[0] + abs(x)
    if (y > 0):
        finalY = radarCenter[1] - abs(y)

    if (x < 0):
        finalX = radarCenter[0] - abs(x)
    if (y < 0):
        finalY = radarCenter[1] + abs(y)

    # invert x y
    # finalY = radarHeight - finalY
    # finalX = radarWidth - finalX

    # calculate angle
    if showAngle:
        angle = math.atan2(radarCenter[1] - finalY, radarCenter[0] - finalX)
        # convert to degrees
        angle = np.rad2deg(angle)
        return [finalX, finalY, angle]

    return [finalX, finalY]


def rotateRadar(origin, point, angle):
    """
    Rotate a point counterclockwise by a given angle around a given origin.

    The angle should be given in radians.
    """
    ox, oy = origin
    px, py = point

    qx = ox + math.cos(angle) * (px - ox) - math.sin(angle) * (py - oy)
    qy = oy + math.sin(angle) * (px - ox) + math.cos(angle) * (py - oy)
    return qx, qy


currentDir = os.path.dirname(os.path.realpath(__file__))
# arrowPlayer = cv2.imread(os.path.join(
#     currentDir, 'assets', 'ct_arrow.png'), cv2.IMREAD_UNCHANGED)
# # helpers
arrowPlayer = read_transparent_png(
    os.path.join(currentDir, 'assets', 'ct_arrow.png'))

tracker = EuclideanDistTracker()

# Start of the class


class RADAR ():

    def __init__(self, callback=None, devMode=False):
        self.send = callback
        self.devMode = devMode
        self.showWindows = True
        self.lastFrame = None
        self.lastFrameTracked = None
        self.lastGrayFrame = None
        self.threshold = 90  # no change needed in most situations
        self.arrowContoursPool = []
        self.AngleRoot = "0"
        self.AngleTriangle = "0"
        self.cardinal = "NORTH"
        self.lastCardinal = ""
        self.polarY = 0
        self.polarYpercent = 0
        self.polarFov = 100
        self.polarDegrees = 0
        self.showPlayerIcon = True
        self.team = "nf"
        #
        self.mapItems = []
        self.mapItemsVert = []
        self.detections = []
        #
        self.soundEmmiters = []
        self.polarSlices = []
        # debug masks
        self.h = 0
        self.s = 0
        self.v = 0
        self.h2 = 0
        self.s2 = 0
        self.v2 = 0

        self.threshold_polar = 170
        self.threshold_polarVert = 215
        self.blur_polar = (3, 3)
        self.blur_polar_mask = (3, 3)
        self.canny_polar = 0
        self.dilate_polar = 1
        self.erode_polar = 0

        self.cannyParam1_polar = 33
        self.cannyParam2_polar = 47

        self.lastBeep = 0
        self.lastSilence = 0

        self.lastSilenceWalls = 0
        self.lastBeepWalls = 0

        self.threshold_formask = 175

        self.quadrantsNegative = []
        self.quadrantsPositive = []
        # emissions
        self.emissionAIM = 'notSet'
        self.emissionENEMY = 'notSet'
        self.emissionWALL = 'notSet'
        self.emissionFRIEND = 'notSet'
        #
        self.lastBeepENEMY = 0
        self.lastSilenceENEMY = 0
        self.lastRadarPlot = None

        self.last_frame_full = None
        self.last_frame_radar = None

        self.h_polarRadar = 15
        self.s_polarRadar = 30
        self.v_polarRadar = 65
        self.h2_polarRadar = 100
        self.s2_polarRadar = 80
        self.v2_polarRadar = 90

        self.floorRanges = []
        self.floorRangesTest = []

        self.polarFloorthreshParam1 = 170
        self.polarFloorthreshParam2 = 255
        self.polarContrast = 1.5
        self.polarBrightness = 80
        # self.radarLoopThread = Thread(
        #     target=self.radarLoop, name="RadarLoop", args=(self.last_frame_radar, self.last_frame_full), daemon=True)
        # self.radarLoopThread.start()

        self._alpha1 = 0.5
        self._alpha2 = 0.5
        self.floorTolerance = 65
        self._beta = 0
        self._gridSize = 48
        self._gridIncrease = 4
        self._ObDistances = []
        self._gridFrames = []
        self._gridFrame = None
        self._gridImageF = np.zeros(
            (self._gridSize * self._gridIncrease, self._gridSize * self._gridIncrease), dtype=np.uint8)

        self.runMJPEGserver = False
        self.useMJPEGserver = False

        self.radarIconClassses = [
            {
                "name": "enemy",
                "color": (0, 0, 255),
                "lower": [0, 160, 200],
                "upper": [15, 255, 255]
            },
            {
                "name": "friend_blue",
                "color": (255, 0, 0),
                "lower": [90, 60, 200],
                "upper": [110, 255, 255]
            },
            {
                "name": "friend_yellow",
                "color": (0, 255, 255),
                "lower": [24, 100, 100],
                "upper": [30, 230, 255]
            }
        ]

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, item, value):
        return setattr(self, item, value)

    def getLastFrame(self):
        return self.lastFrameTracked

    def devMJPGLoop(self, stream, server):

        i = 0
        while self.runMJPEGserver == True:

            stream.set_frame(self.getLastFrame())

            # if (i == 0):
            #     server.start()
            if self.runMJPEGserver == False:
                server.stop()
                break
            if cv2.waitKey(1) == ord("k"):
                server.stop()
                self.runMJPEGserver = False
                break

            i += 1
            # print("MJPEG server running", i)
            # time.sleep(0.1)

    def devMJPGserver(self, width=395, height=395):

        ip = '127.0.0.1'
        try:

            stream = Stream("radar_cropped", size=(
                width, height), quality=100, fps=60)
            server = MjpegServer(ip, 9090)
            server.add_stream(stream)
            server.start()

            t = Thread(target=self.devMJPGLoop, name="devMJPGLoop",
                       args=(stream, server), daemon=True)
            t.start()

        except:
            print("Shutting down server")

    def radarLoop(self, frame_radar, frame_full):
        while True:
            if self.last_frame_radar is not None and self.last_frame_full is not None:
                self.processRadar(self.last_frame_radar, self.last_frame_full)
                # print("radarLoop")
            else:
                pass
            time.sleep(0.1)

    def playBeep(self, silence=0.5, param1=0, param2=0):

        # AudioSegment
        if time.time() - self.lastBeep > self.lastSilence:
            print("playBeep", silence)
            self.lastBeep = time.time()
            sound = AudioSegment.from_file(os.path.join(
                currentDir, 'sounds', 'beep_aim.wav'))
            play(sound)
        else:
            print("playBeep", silence, "silenced")

    def updatePlayerIcon(self):
        center = (arrowPlayer.shape[1] // 2, arrowPlayer.shape[0] // 2)

        playerAngle = int(self.AngleRoot) - 180
        rotate_matrix = cv2.getRotationMatrix2D(
            center=center, angle=playerAngle, scale=1)
        # arrowPlayer = rotate_image(arrowPlayer, playerAngle)
        # convert to bgr
        # arrowPlayer = cv2.cvtColor(arrowPlayer, cv2.COLOR_RGBA2BGR)
        # remove background
        # arrowPlayer[np.all(arrowPlayer == [255, 255, 255], axis=2)] = [0, 0, 0]
        # smooth edges
        # arrowPlayer[np.all(arrowPlayer == [255, 255, 255], axis=2)] = [0, 0, 0]
        # show arrowPlayer image
        rotated_image = cv2.warpAffine(src=arrowPlayer, M=rotate_matrix, dsize=(
            arrowPlayer.shape[1], arrowPlayer.shape[0]))
        # create withe background
        # create withe image

        # create mask
        mask = cv2.cvtColor(rotated_image, cv2.COLOR_BGR2GRAY)
        mask[mask > 0] = 255
        mask[mask < 1] = 0
        mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        # apply mask
        rotated_image = cv2.bitwise_and(rotated_image, mask)
        # flip vertical
        rotated_image = cv2.flip(rotated_image, 1)
        # flip horizontal
        rotated_image = cv2.flip(rotated_image, 0)
        # flip horizontal
        rotated_image = cv2.flip(rotated_image, 1)
        # diplay degrees text
        cv2.putText(rotated_image, str(playerAngle), (5, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
        # cv2.imshow('arrowPlayer', rotated_image)

    def updatePlayerArrow(self, frame):
        # LAST MASKED PLAYER FRAME
        self.lastPlayerFrame = frame

        radiusPlayer = self.lastPlayerFrame.shape[0] // 18
        maskedPlayerHSV = cv2.cvtColor(
            np.array(self.lastPlayerFrame), cv2.COLOR_BGR2HSV)
        maskedPlayerBW = cv2.cvtColor(self.lastPlayerFrame, cv2.COLOR_BGR2GRAY)
        maskedPlayerBWBlur = cv2.GaussianBlur(maskedPlayerBW, (3, 3), 0)
        maskedPlayerCanny = cv2.Canny(maskedPlayerBWBlur, 100, 200)
        # MASK PLAYER COLOR YELLOW, BLUE
        lower_pin = np.array([0, 0, 192])
        upper_pin = np.array([180, 250, 255])

        maskpin = cv2.inRange(maskedPlayerHSV, lower_pin, upper_pin)
        maskedpin = cv2.bitwise_and(
            maskedPlayerHSV, maskedPlayerHSV, mask=maskpin)
        maskedpinBW = cv2.cvtColor(maskedpin, cv2.COLOR_BGR2GRAY)
        maskedpinBWBlur = cv2.GaussianBlur(maskedpinBW, (3, 3), 0)

        ret, thresh = cv2.threshold(
            maskedpinBWBlur, 90, 255, cv2.THRESH_TRIANGLE)

        maskPlayer = np.zeros(self.lastPlayerFrame.shape[:2], dtype="uint8")
        cv2.circle(maskPlayer, (self.lastPlayerFrame.shape[1] // 2-2,
                   self.lastPlayerFrame.shape[0] // 2-2), radiusPlayer, 255, -1)

        maskedThresh = cv2.bitwise_and(thresh, thresh, mask=maskPlayer)

        # scale and blur maskedThresh
        maskedThresh = cv2.resize(maskedThresh, (0, 0), fx=3, fy=3)
        maskedThresh = cv2.GaussianBlur(maskedThresh, (5, 5), 0)
        # Apply Canny edge detection
        edges = cv2.Canny(maskedThresh, 50, 150)

        # show
        # cv2.imshow('edges', edges)
        # crop masked circle
        # get image center
        center = (maskedThresh.shape[1] // 2, maskedThresh.shape[0] // 2)
        playerRadius = maskedThresh.shape[0] // 16
        # crop image
        # img_canny = edges[center[1] - 100:center[1] + 100, center[0] - 100:center[0] + 100]
        img_canny = edges[center[1] - playerRadius:center[1] +
                          playerRadius, center[0] - playerRadius:center[0] + playerRadius]
        # fill the arrow with white
        img_dilate = cv2.dilate(img_canny, None, iterations=1)
        img_erode = cv2.erode(img_dilate, None, iterations=2)

        # cv2.imshow('img_canny', img_canny)

        # get the (largest) contour
        contours = cv2.findContours(
            img_canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = contours[0] if len(contours) == 2 else contours[1]
        if len(contours) > 0:
            big_contour = max(contours, key=cv2.contourArea)

            # draw white filled contour on black background
            arrowTreatFilter = np.zeros_like(img_canny)
            cv2.drawContours(arrowTreatFilter, [
                             big_contour], 0, (255, 255, 255), cv2.FILLED)

            # apply blur
            arrowTreatFilter = cv2.GaussianBlur(arrowTreatFilter, (3, 3), 0)
            # apply more blur
            arrowTreatFilter = cv2.GaussianBlur(arrowTreatFilter, (3, 3), 0)
            # apply threshold
            # arrowTreatFilter = cv2.threshold(arrowTreatFilter, 200, 255, cv2.THRESH_BINARY)[1]

            resultMeasures = MeasuresForArrow(arrowTreatFilter, self.lastPlayerFrame.copy(
            ), self.AngleRoot, self.lastPlayerFrame.shape[1] // 2)

            # self.AngleRoot = resultMeasures[1]
            self.croppedTreated = resultMeasures[0]

            gray_image = cv2.cvtColor(self.croppedTreated, cv2.COLOR_BGR2GRAY)
            _, thresh_image = cv2.threshold(
                gray_image, 100, 255, cv2.THRESH_BINARY_INV)

            # apply blur
            thresh_image = cv2.GaussianBlur(thresh_image, (5, 5), 0)
            # apply median blur
            thresh_image = cv2.medianBlur(thresh_image, 9)

            thresh_image = cv2.dilate(thresh_image, None, iterations=1)
            thresh_image = cv2.erode(thresh_image, None, iterations=1)
            # more thresholding
            _, thresh_image = cv2.threshold(
                thresh_image, 100, 255, cv2.THRESH_BINARY)
            # cv2.imshow("croppedTreated", thresh_image)

            # convert thresh_image to gray and apply blur
            gray_image_triangle = thresh_image.copy()
            gray_image_triangle = cv2.GaussianBlur(
                gray_image_triangle, (5, 5), 0)

            # apply more threesholding
            _, thresh_image_triangle = cv2.threshold(
                gray_image_triangle, 100, 255, cv2.THRESH_BINARY_INV)
            # convert to BGR and apply blur
            thresh_image_triangle = cv2.cvtColor(
                thresh_image_triangle, cv2.COLOR_GRAY2BGR)
            thresh_image_triangle = cv2.GaussianBlur(
                thresh_image_triangle, (5, 5), 0)

            newTriangle = createTriangle(thresh_image_triangle)

            if newTriangle is not None:
                angle = processTriangle(self, newTriangle)
                compute_rotation(self, angle, self.AngleTriangle, newTriangle)
                # cv2.imshow("newTriangle", newTriangle)

    def filterRadarItens(self, frame, hsv, lower_mask, upper_mask, className=""):

        maskItem = cv2.inRange(hsv, lower_mask, upper_mask)
        maskedItem = cv2.bitwise_and(
            frame, frame, mask=maskItem)

    #    # convert to grayscale
        maskedItemGray = cv2.cvtColor(maskedItem, cv2.COLOR_BGR2GRAY)
        # detect contours

        contoursItem, hierarchy = cv2.findContours(
            maskedItemGray, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        return contoursItem, maskedItem

    def trackRadarItens(self, frame, hsv, lower_mask, upper_mask, className="", vert=False, onlyDetect=False):

        contoursItem, maskedItem = self.filterRadarItens(
            frame, hsv, lower_mask, upper_mask, className)

        def createRadarItens(self, contours, target, className="", vert=False, minDistance=5, maxDistance=120, onlyDetect=False):

            detections = []
            for c in contours:
                # Calculate the area of each contour
                area = cv2.contourArea(c)
                # Ignore contours that are too small or too large
                if area < 100 or 10000 < area:
                    continue
                # get rect from contours
                (x, y, w, h) = cv2.boundingRect(c)

                rect = cv2.minAreaRect(c)
                # get box from rect
                box = cv2.boxPoints(rect)
                # convert all coordinates floating point values to int
                box = np.intp(box)
                # draw contours
                cv2.drawContours(target, [box], 0, (0, 255, 0), 2)
                # get center of contour
                M = cv2.moments(c)
                # get center x and y
                if M["m00"] != 0:

                    cX = int(M["m10"] / M["m00"])
                    cY = int(M["m01"] / M["m00"])

                    cXVert = int(M["m10"] / M["m00"])
                    cYVert = int(M["m01"] / M["m00"])

                    # print("normalizeRadarPlot_before", cX, cY)

                    radarWidth = target.shape[1]
                    radarHeight = target.shape[0]
                    radarCenter = [radarWidth // 2, radarHeight // 2]

                    if cX > radarCenter[0]:
                        cX = cX - radarCenter[0]
                    else:
                        cX = radarCenter[0] - cX
                        cX = cX * -1

                    if cY > radarCenter[1]:
                        cY = cY - radarCenter[1]
                        cY = cY * -1
                    else:
                        cY = radarCenter[1] - cY

                    # if ver is true

                    if vert:
                        # invert x y
                        # cY = radarHeight - cY
                        # cX = radarWidth - cX
                        if className == "enemy":
                            color = (0, 0, 255)
                        elif className == "friend":
                            color = (255, 0, 255)
                        elif className == "friend_yellow":
                            color = (0, 255, 255)
                        elif className == "friend_blue":
                            color = (255, 0, 0)
                        else:
                            color = (0, 255, 0)

                        if onlyDetect == False:
                            cv2.circle(target, (cXVert, cYVert),
                                       5, color, -1)

                            # if cXVert > 100:
                            # display cYVert text
                            cv2.putText(target, str("cYVert_"+str(cYVert)+""),
                                        (cXVert+10, cYVert), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

                            # distance from center

                            self.mapItemsVert.append({
                                'className': className,
                                'x': cXVert,
                                'y': cYVert,
                                'minDistance': minDistance
                            })
                        else:
                            dist = int(
                                math.sqrt((cXVert - 10)**2 + (cYVert - 10)**2))
                            detections.append({
                                'className': className,
                                'x': cXVert,
                                'y': cYVert,
                                'dist': dist,
                                'minDistance': minDistance
                            })
                    else:

                        if className == "enemy":
                            color = (0, 0, 255)
                        elif className == "friend":
                            color = (255, 0, 255)
                            minDistance = 20
                        elif className == "friend_yellow":
                            color = (0, 255, 255)
                            minDistance = 20
                        elif className == "friend_blue":
                            color = (255, 0, 0)
                            minDistance = 20
                        else:
                            color = (0, 255, 0)

                        if onlyDetect == False:
                            cv2.circle(target, normalizeRadarPlot(
                                cX, cY, target), 5, color, -1)

                            # get box coordinates
                            # create cropper image from box coordinates
                            # crop the image
                            # crop_img = target[y:y+h, x:x+w]
                            # # create empty image with 50x50
                            # croppedThumb = np.zeros((50, 50, 3), dtype="uint8")
                            # # put crop_img in the center of croppedThumb
                            # croppedThumb[0:crop_img.shape[0],
                            #              0:crop_img.shape[1]] = crop_img

                            # if self.devMode:
                            #     # show croppedThumb
                            #     cv2.imshow("croppedThumb", croppedThumb)

                            self.mapItems.append({
                                'className': className,
                                'x': cX,
                                'y': cY,
                                'silence': 0,
                                'lastBeep': 0,
                                'level': 0,
                                'lastSilence': 0,
                                'beepCounts': 0,
                                'lastBeepWalls': 0,
                                'lastSilenceWalls': 0,
                                'minDistance': minDistance,
                                'maxDistance': maxDistance
                            })
                        else:
                            dist = int(math.sqrt((cX - 10)**2 + (cY - 10)**2))
                            detections.append({
                                'className': className,
                                'x': cX,
                                'y': cY,
                                'dist': dist,
                                'minDistance': minDistance,
                                'maxDistance': maxDistance
                            })

            return detections
        detected = createRadarItens(
            self, contoursItem, maskedItem, className, vert, 5, 120, onlyDetect)

        if onlyDetect == True:
            return maskedItem, detected
        # show maskedItem
        # cv2.imshow("maskedItem_"+str(className)+"", maskedItem)
        #  combine maskedBlue and maskedRed
        mined = cv2.bitwise_or(maskedItem, frame)

        # minDistance = 5
        # # if exist friend on className string
        # if "friend" in className:
        #     minDistance = 20
        # filterResult = []
        # filter minDistance
        if vert:
            self.mapItemsVert = [x for x in self.mapItemsVert if abs(
                x['x']) > x['minDistance'] or abs(x['y']) > x['minDistance']]
            filterResult = self.mapItemsVert
        else:
            self.mapItems = [x for x in self.mapItems if abs(
                x['x']) > x['minDistance'] or abs(x['y']) > x['minDistance']]
            # filter maxDistance
            self.mapItems = [x for x in self.mapItems if abs(
                x['x']) < x['maxDistance'] or abs(x['y']) < x['maxDistance']]
            filterResult = self.mapItems

        return mined, filterResult

    def radarAIM(self, frame, frameOriginal, lower_mask, upper_mask, className=""):
        # convert to hsv
        polarHSV = cv2.cvtColor(frameOriginal, cv2.COLOR_BGR2HSV)
        # filter radar itens
        mined, mapItemsVert = self.trackRadarItens(
            frameOriginal, polarHSV, lower_mask, upper_mask, className, True)

        # print("mapItemsVert", mapItemsVert)

        # draw polarY line
        cv2.line(mined, (0, self.polarY), (mined.shape[1], self.polarY),
                 (255, 255, 255), 1)

        enemiesSpoted = []
        finalAIMList = []
        bestTarget = None

        frame_full = np.zeros((288, 512, 3), dtype="uint8")

        # check if line intersects with mapItemsVert
        for i in range(len(mapItemsVert)):
            # print("\nmapItemsVert", mapItemsVert[i])
            x = mapItemsVert[i]['x']
            y = mapItemsVert[i]['y']

            depthVert = int(sqrt((x - 10)**2 + (y - self.polarY)**2))

            dist = abs(y - self.polarY)
            realDist = y - self.polarY

            if self.polarY-self.polarFov // 2 <= y <= self.polarY+self.polarFov // 2:
                # print("INTERSECTS")
                # draw line from center to contour
                enemiesSpoted.append(
                    {'x': x, 'y': y, 'dist': dist, 'realDist': realDist, 'depth': depthVert})

                color = (0, 255, 0)
                if dist < 10:
                    color = (0, 0, 255)
                cv2.line(mined, (0, self.polarY),
                         (x, y), color, 3)
                # draw bounding box
                cv2.rectangle(mined, (x-5, y-5), (x+5, y+5), (0, 255, 255), 1)

                cv2.putText(mined, str("realDist_"+str(realDist)+""),
                            (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

        for i in range(len(enemiesSpoted)):
            if bestTarget is None:
                bestTarget = enemiesSpoted[i]
            elif enemiesSpoted[i]['dist'] < bestTarget['dist']:
                bestTarget = enemiesSpoted[i]

        cropTop = self.polarY-self.polarFov // 2
        cropBottom = self.polarY+self.polarFov // 2

        if cropTop > 0:
            mined[0:cropTop, 0:mined.shape[1]] = (0, 0, 0)
        # fill cropBottom with black
        if cropBottom < mined.shape[0]:
            mined[cropBottom:mined.shape[0], 0:mined.shape[1]] = (0, 0, 0)

        # display polarY text
        cv2.putText(mined, str("polarY_"+str(self.polarY)+""),
                    (20, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        if bestTarget is not None:
            x = bestTarget['x']
            y = bestTarget['y']
            dist = bestTarget['dist']
            realDist = bestTarget['realDist']
            depth = bestTarget['depth']
            id = str(x)+"_"+str(y)+"_"+str(dist)+""
            # play beep sound and repeat according to dist

            color = (0, 255, 0)
            if dist < 10:
                color = (0, 0, 255)
            cv2.putText(mined, str("dist_"+str(realDist)+""),
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

            cv2.putText(mined, str("prox_"+str(depth)+""),
                        (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

            silence = 1

            if dist < 50:
                silence = 0.8
            if dist < 40:
                silence = 0.6
            if dist < 30:
                silence = 0.4
            if dist < 20:
                silence = 0.2
            if dist < 10:
                silence = 0.05

            #  playBeep on separeted thread

            # if dist < 50:
            newposition = [int(realDist * 4), int(depth * 4)]

            # calculate angle in degrees from 0,0
            angle = math.atan2(self.polarY - y, 0 - x)

            model = {
                'id': id,
                # 'position': ""+str(realDist * 4)+"_"+str(depth * 4)+"",
                'position': newposition,
                'px': newposition[0],
                'py': newposition[1],
                'x': int(x),
                'y': int(y),
                'angle': int(angle),
                'dist': int(dist),
                'silence': silence,
            }

            finalAIMList.append(model)

            # draw vertival line on frame_full
            lineX = int(newposition[0] + frame_full.shape[1] // 2)

            lineX = int(lerp(lineX, frame_full.shape[1] // 2, 0.1))

            cv2.line(frame_full, (lineX, 0), (lineX, frame_full.shape[0]),
                     color, 1)
            # show frame full
            # cv2.imshow("frame_full_PolarAIM", frame_full)

            # send osc message
            if self.send is not None:
                self.send("/aimpolar", json.dumps(finalAIMList))

        # if len(enemiesSpoted) == 0:
        #     if self.send is not None:
        #         self.send("/aim", json.dumps([]))
        # show mined
        # cv2.imshow("mined_AIM", mined)
        return mined

    def radarWall(self, frame):
        # convert to hsv
        mined = frame.copy()
        return mined

    def radarSegmentation(self, frame):
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        twoDimage = img.reshape((-1, 3))
        twoDimage = np.float32(twoDimage)
        criteria = (cv2.TERM_CRITERIA_EPS +
                    cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        K = 6
        attempts = 2
        ret, label, center = cv2.kmeans(
            twoDimage, K, None, criteria, attempts, cv2.KMEANS_PP_CENTERS)
        center = np.uint8(center)
        res = center[label.flatten()]
        result_image = res.reshape((img.shape))
        result_image = cv2.cvtColor(result_image, cv2.COLOR_RGB2BGR)
        return result_image

    def polarHistogram(self, frame, isTest=False):
        # convert to hsv
        original = frame.copy()

        # apply histogram equalization
        original = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
        original = cv2.equalizeHist(original)
        original = cv2.cvtColor(original, cv2.COLOR_GRAY2BGR)
        return original

    def estimateBrightness(self, frame):
        if len(frame.shape) == 3:
            # Colored RGB or BGR (*Do Not* use HSV images with this function)
            # create brightness with euclidean norm
            return np.average(np.linalg.norm(frame, axis=2)) / np.sqrt(3)
        else:
            # Grayscale
            return np.average(frame)

    def applyBrightAndContrast(self, frame, alpha=1.0, beta=0):
        # alpha = 1.5  # Contrast control (1.0-3.0)
        # beta = 0  # Brightness control (0-100)
        # alpha = self.polarContrast
        # beta = self.polarBrightness

        adjusted = cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)
        return adjusted

    def block_mean(self, ar, fact):
        assert isinstance(fact, int), type(fact)
        sx, sy = ar.shape
        X, Y = np.ogrid[0:sx, 0:sy]
        regions = sy//fact * (X//fact) + Y//fact
        res = ndimage.mean(ar, labels=regions,
                           index=np.arange(regions.max() + 1))
        res.shape = (sx//fact, sy//fact)
        return res

    def resetMapGrid(self):
        self.floorGrid = [0] * self._gridSize * self._gridSize
        self._gridImageF = np.zeros(
            (self._gridSize * self._gridIncrease, self._gridSize * self._gridIncrease), dtype=np.uint8)
        self.floorGridTimer = None
        self._ObDistances = []

    def generateGridImage(self, _x, _y, _width, _height, generate=False):
        # iterate to all pixels self.floorGrid
        # create image
        increased = self._gridSize * self._gridIncrease
        center = (increased // 2, increased // 2)
        distances = []
        # img = np.zeros((increased, increased, 3), dtype=np.uint8)
        if generate == True:
            # create 1 channel image
            self._gridImageF = np.zeros(
                (self._gridSize * self._gridIncrease, self._gridSize * self._gridIncrease), dtype=np.uint8)

            # return self._gridImageF
            # iterate to all pixels
            for i in range(self._gridSize):
                for j in range(self._gridSize):
                    # check if contains white
                    if self.floorGrid[i * self._gridSize + j] == 1:
                        # self._gridImageF[i*self._gridIncrease, j*self._gridIncrease] = [255, 255, 255]
                        y = j*self._gridIncrease
                        x = i*self._gridIncrease

                        # get angle
                        angleP = math.atan2(y - center[1], x - center[0])

                        # rotated
                        soundposition = rotateRadar(
                            center, (x, y), radians(int(self.AngleRoot)))

                        rx = int(soundposition[0])
                        ry = int(soundposition[1])

                        self._gridImageF[x, y] = 255
                        # distance from center
                        dist = sqrt((x - center[0])**2 + (y - center[1])**2)

                        distances.append({
                            'dist': dist,
                            'x': y,
                            'y': x,
                            'rx': ry,
                            'ry': rx,
                            'angle': angleP
                        })

                    else:
                        # self._gridImageF[i*self._gridIncrease, j*self._gridIncrease] = [0, 0, 0]
                        self._gridImageF[i*self._gridIncrease,
                                         j*self._gridIncrease] = 0
        else:
            x = _x*self._gridIncrease
            y = _y*self._gridIncrease
            self._gridImageF[x, y] = 255

            # distance from center
            dist = sqrt((x - center[0])**2 + (y - center[1])**2)
            distances.append({
                'dist': dist,
                'x': y,
                'y': x
            })

        # sort by distances
        distances = sorted(distances, key=lambda k: k['dist'])
        # filter first 10
        # self._ObDistances = distances[-10:]
        # draw line from center to shorters point
        if len(distances) > 0:
            # get the first distance
            self._ObDistances = [distances[0]]
            cv2.line(
                self._gridImageF, center, (int(distances[0]['x']), int(distances[0]['y'])), 255, 1)

            cv2.line(
                self._gridImageF, center, (int(distances[0]['rx']), int(distances[0]['ry'])), 180, 2)
        else:
            self._ObDistances = []
        return self._gridImageF

    def setFloorMapGrid(self, x, y, maxX, maxY, value):
        relX = round((x / maxX) * self._gridSize)
        relY = round((y / maxY) * self._gridSize)
        id = (relX * self._gridSize + relY) - 1
        if id < len(self.floorGrid):
            self.floorGrid[id] = value
        return relX, relY

    def blendFrames(self, frame1, frame2, alpha=0.5, beta=0.5):
        # blend frames
        blended = cv2.addWeighted(frame1, alpha, frame2, beta, 0)
        # GET MEAN OF FRAMES
        # blended = cv2.add(frame1, frame2) // 2
        return blended

    def addGridFrame(self, frame, split=5):

        self._gridFrames.append(frame)
        # get last 10 frames
        if len(self._gridFrames) > split:
            self._gridFrames = self._gridFrames[-split:]

        # blend frames
        for i in range(len(self._gridFrames)):
            if i == 0:
                self._gridFrame = self._gridFrames[i]
            else:
                self._gridFrame = self.blendFrames(
                    self._gridFrame, self._gridFrames[i], alpha=0.5, beta=0.5)

        return self._gridFrame

    def floorSegmentation(self, frame, refillRadius, isTest=False):

        radius = 5
        saveOnDisk = False
        footprint = disk(radius)
        # if 3 channels
        if len(frame.shape) == 3:
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            img = frame
            # apply blur
            # img = cv2.GaussianBlur(img, (9, 9), 0)
            # img = mean(img, disk(radius))
            img = enhance_contrast_percentile(img, footprint, p0=.1, p1=.9)
            # img = cv2.equalizeHist(img)

        # local_otsu = rank.otsu(img, footprint)

        img = cv2.resize(
            img, (0, 0), fx=0.35, fy=0.35, interpolation=cv2.INTER_NEAREST)

        block_size = 35
        local_thresh = threshold_local(img, block_size)
        binary_local = img > local_thresh

        # binaryMap = img >= local_otsu

        # convert binary map to grayscale
        cv_image = img_as_ubyte(binary_local)

        # cv_image = cv2.resize(
        #     cv_image, (0, 0), fx=0.7, fy=0.7, interpolation=cv2.INTER_NEAREST)

        # show cv_image
        # cv2.imshow("cv_image_input", img)
        radiusCalc = 6

        # draw white circle to eliminate the player from the floor
        cv2.circle(cv_image, (cv_image.shape[1] // 2, cv_image.shape[0] // 2),
                   radiusCalc, (255, 255, 255), -1)

        # cv2.imshow("cv_image", cv_image)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        res = cv2.morphologyEx(cv_image, cv2.MORPH_OPEN, kernel)

        contours, hierarchy = cv2.findContours(
            res, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)

        # filter contours only with area > self.floorTolerance
        contours = [c for c in contours if cv2.contourArea(
            c) > self.floorTolerance]

        # create new mask
        mask = np.zeros_like(cv_image)

        cv2.drawContours(mask, contours, -1, (255, 255, 255), -1)

        # get cv_image width and height
        height, width = cv_image.shape[:2]
        # center
        center = (width // 2, height // 2)

        # mask1 = np.zeros((height+2, width+2), np.uint8)     # line 26
        cv2.floodFill(mask, None, center, 255)     # line 27
        mask_inv = cv2.bitwise_not(mask)
        mask_inv_resized = mask_inv.copy()

        # draw circle
        mask_inv_masker = np.zeros_like(mask_inv_resized)
        # mask pixels circle
        cv2.circle(mask_inv_masker, (mask_inv_resized.shape[1] // 2, mask_inv_resized.shape[0] // 2),
                   mask_inv_resized.shape[0] // 3-2, (255, 255, 255), -1)

        mask_inv_resized = cv2.bitwise_and(
            mask_inv_resized, mask_inv_resized, mask=mask_inv_masker)

        # draw black circle to eliminate the player from the floor
        cv2.circle(mask_inv_resized, center,
                   radiusCalc, (0, 0, 0), -1)

        # convert to bgr
        # mask_inv_resized = cv2.cvtColor(
        #     mask_inv_resized, cv2.COLOR_GRAY2BGR)

        # optional - scale interpolation=cv2.INTER_NEAREST

        # mask_inv_resized = cv2.resize(
        #     mask_inv_resized, (0, 0), fx=0.5, fy=0.5)

        # reset grid
        self.resetMapGrid()
        # iterate to all pixels
        # pixelsList = np.argwhere(mask_inv_resized != [0, 0, 0])
        finalSize = mask_inv_resized.copy()
        finalSize = cv2.resize(
            finalSize, (0, 0), fx=0.40, fy=0.40, interpolation=cv2.INTER_NEAREST)

        blended = self.addGridFrame(finalSize, split=2)
        pixelsList = np.argwhere(blended > 25)

        width, height = blended.shape[:2]

        for px in pixelsList:
            x = px[0]
            y = px[1]
            _x, _y = self.setFloorMapGrid(x, y, width, height, 1)

        if len(pixelsList) > 0:
            gridImage = self.generateGridImage(
                None, None, None, None, generate=True)
        else:
            gridImage = blended

        # downsample
        #
        if saveOnDisk == True:
            image = Image.fromarray(res)
            # draw = ImageDraw.Draw(image)
            # convert image to base64
            buffered = BytesIO()
            # image = image.resize((100, 100), resample=0)
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue())
            filename = ""+os.path.join(os.path.dirname(__file__) +
                                       "/UI/images/", "lastframe_radar.png")
            image.save(filename)

            # downsample = self.block_mean(mask_inv, 5)

            if self.send is not None:
                self.send("/binarymap", {'binarymap': len(str(img_str))})

        return res, mask_inv_resized, gridImage, blended

    def polarFloorSegmentation(self, frame, isTest=False):

        if isTest == True:
            recipient = self.floorRangesTest
        else:
            recipient = self.floorRanges

        # convert to hsv
        original = frame.copy()
        hsv = cv2.cvtColor(original, cv2.COLOR_BGR2HSV)
        masked = hsv.copy()
        masks = []

        if len(recipient) == 0:
            return original

        # filter radar floor with multiple masks
        for i in range(len(recipient)):
            lower = np.array(recipient[i]['lower'])
            upper = np.array(recipient[i]['upper'])

            # mask lower and upper
            mask = cv2.inRange(hsv, lower, upper)

            masks.append(mask)

        # apply multiple masks
        for i in range(len(masks)):
            masked = cv2.bitwise_and(masked, masked, mask=masks[i])

        # convert to bgr
        masked = cv2.cvtColor(masked, cv2.COLOR_HSV2BGR)
        # put text
        cv2.putText(masked, str("totalMasks_"+str(len(recipient))+""),
                    (20, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        return masked

    def angleToCartesian(self, angle, radius):
        x = radius * math.cos(radians(angle))
        y = radius * math.sin(radians(angle))
        return x, y

    def angleToCardinal(self, angle):
        if 0 <= angle < 22.5:
            return "NORTH"
        elif 22.5 <= angle < 67.5:
            return "NORTH EAST"
        elif 67.5 <= angle < 112.5:
            return "EAST"
        elif 112.5 <= angle < 157.5:
            return "SOUTH EAST"
        elif 157.5 <= angle < 202.5:
            return "SOUTH"
        elif 202.5 <= angle < 247.5:
            return "SOUTH WEST"
        elif 247.5 <= angle < 292.5:
            return "WEST"
        elif 292.5 <= angle < 337.5:
            return "NORTH WEST"
        elif 337.5 <= angle <= 360:
            return "NORTH"

    def polarDetector(self, frame, radius=0, emit=False, cropFov=False, angleOnly=False):
        warpPolar = cv2.linearPolar(src=frame, center=(
            frame.shape[0]/2, frame.shape[1]/2), maxRadius=radius, flags=cv2.WARP_FILL_OUTLIERS)

        if cropFov == True:
            # fill with white from 0 to 1/4
            warpPolar[0:warpPolar.shape[0], warpPolar.shape[1] -
                      140:warpPolar.shape[1]] = (255, 255, 255)

        self.polarFov = warpPolar.shape[0] // 4
        warpPolarOriginal = warpPolar.copy()
        warpToMask = warpPolar.copy()

        # # filter only dark colors
        # lower = np.array(
        #     [self.h_polarRadar, self.s_polarRadar, self.v_polarRadar])
        # upper = np.array(
        #     [self.h2_polarRadar, self.s2_polarRadar, self.v2_polarRadar])

        # # convert to hsv
        # warpPolarHSV = cv2.cvtColor(warpPolar, cv2.COLOR_BGR2HSV)
        # # filter radar itens

        # # mask lower and upper
        # mask = cv2.inRange(warpPolarHSV, lower, upper)
        # # apply mask
        # warpPolar = cv2.bitwise_and(warpPolar, warpPolar, mask=mask)

        # convert to gray
        # check if 3 channels
        if len(warpPolar.shape) == 3:
            warpPolarGray = cv2.cvtColor(warpPolar, cv2.COLOR_BGR2GRAY)
        else:
            warpPolarGray = warpPolar

        blur = cv2.GaussianBlur(warpPolarGray, self.blur_polar, 0)
        # show polarY text

        def getVerticalDegrees(self, blur, radius=0):
            cardinal = ""
            if emit == True:
                return None, None
            # crop 20 pixels from left to right
            # crop 20 pixels from top to bottom
            # crop
            cropTile = blur[0:blur.shape[0], 20:40]
            # apply threshold
            ret, threshCroped = cv2.threshold(
                cropTile, self.threshold_polarVert, 255, cv2.THRESH_BINARY)

            # found contours
            contours, hierarchy = cv2.findContours(
                threshCroped, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            # draw contours

            # convert to BGR
            threshCroped = cv2.cvtColor(threshCroped, cv2.COLOR_GRAY2BGR)
            # get threshCroped height
            threshCropedHeight = threshCroped.shape[0]

            if len(contours) > 0:
                cv2.drawContours(threshCroped, contours, -1, (0, 255, 0), 1)
                # find the biggest area
                c = max(contours, key=cv2.contourArea)
                # get the bounding rect
                x, y, w, h = cv2.boundingRect(c)
                # draw a green rectangle to visualize the bounding rect
                cv2.rectangle(threshCroped, (x, y), (x+w, y+h), (0, 255, 0), 2)
                # get the min area rect
                rect = cv2.minAreaRect(c)
                box = cv2.boxPoints(rect)
                # convert all coordinates floating point values to int
                box = np.intp(box)
                # draw contours
                cv2.drawContours(threshCroped, [box], 0, (0, 0, 255), 2)

                maxArea = -1

                for i in range(len(contours)):
                    temp = contours[i]
                    area = cv2.contourArea(temp)
                    if area > maxArea:
                        maxArea = area
                        ci = i
                        res = contours[ci]
                y2_max = threshCroped.shape[0]-1
                y2_min = 0
                x2_max = threshCroped.shape[1]-1
                x2_min = 0
                # get the max x value
                for i in range(len(res)):
                    if res[i][0][0] > x2_min:
                        x2_min = res[i][0][0]
                        y2_min = res[i][0][1]
                # get the max y value
                for i in range(len(res)):
                    if res[i][0][1] < y2_max:
                        y2_max = res[i][0][1]
                        x2_max = res[i][0][0]
                # draw contours
                cv2.drawContours(threshCroped, [res], 0, (0, 255, 0), 2)
                cv2.circle(threshCroped, (x2_max, y2_max), 3,
                           (0, 0, 255), 3)  # draw top of hands
                cv2.circle(threshCroped, (x2_min, y2_min),
                           3, (255, 0, 255), -3)
                # draw line
                cv2.line(threshCroped, (x2_min, y2_min), (x2_max, y2_min),
                         (255, 0, 0), 2)
                self.polarY = y2_min

                # get polarY percentage
                polarYPercentage = (self.polarY * 100) // threshCropedHeight

                # pixels per 180
                # 50% = 180 degrees
                # 100% = 360 degrees

                self.polarYpercent = polarYPercentage
                # 30% = 180 degrees
                # 100% = 360 degrees
                rawDegrees = int((polarYPercentage * 36)) // 10

                self.polarDegrees = 90 + rawDegrees
                if self.polarDegrees > 360:
                    self.polarDegrees = self.polarDegrees - 360
                if self.polarDegrees < 0:
                    self.polarDegrees = self.polarDegrees + 360

                # round polarDegrees
                self.polarDegrees = round(self.polarDegrees, 2)
                self.AngleRoot = str(self.polarDegrees)

                cardinal = self.angleToCardinal(self.polarDegrees)

                # get center of contour
                M = cv2.moments(c)
                # get center x and y
                if M["m00"] != 0:
                    cX = int(M["m10"] / M["m00"])
                    cY = int(M["m01"] / M["m00"])
                    # draw the contour center
                    cv2.circle(threshCroped, (cX, cY), 7, (255, 255, 255), -1)
                    # draw the contour center
                    cv2.circle(threshCroped, (cX, cY), 5, (0, 0, 255), -1)
                    # draw the contour center
                    cv2.circle(threshCroped, (cX, cY), 3, (255, 255, 255), -1)
            self.cardinal = cardinal
            return threshCroped, cardinal

        def generateROIs(self, frame, startX=0, startY=0, endX=0, endY=0):

            for i in range(len(self.polarSlices)):
                # get roi
                roi = frame[self.polarSlices[i]['y']:self.polarSlices[i]
                            ['y2'], self.polarSlices[i]['x']:self.polarSlices[i]['x2']]

                width = self.polarSlices[i]['x2'] - self.polarSlices[i]['x']
                height = self.polarSlices[i]['y2'] - self.polarSlices[i]['y']

                self.polarSlices[i]['x2_min'] = width
                self.polarSlices[i]['width'] = width

                canny = cv2.Canny(roi, self.cannyParam1_polar,
                                  self.cannyParam2_polar)
                # fill gaps of canny
                kernel = np.ones((3, 3), np.uint8)
                dilate = cv2.dilate(
                    canny, kernel, iterations=self.dilate_polar)
                # create new image
                self.polarSlices[i]['image'] = frame.copy()

                # convert to bgr
                # check if image is grayscale
                if len(self.polarSlices[i]['image'].shape) < 3:
                    self.polarSlices[i]['image'] = cv2.cvtColor(
                        self.polarSlices[i]['image'], cv2.COLOR_GRAY2BGR)
                # draw vertival line startX
                cv2.line(
                    self.polarSlices[i]['image'], (startX, 0), (startX, self.polarSlices[i]['y2']), (169, 255, 0), 2)

                # get contours
                contours, hierarchy = cv2.findContours(
                    dilate, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

                # iterate contours and get the lower left point
                finalContours = []
                for c in contours:
                    # Calculate the area of each contour
                    area = cv2.contourArea(c)
                    # Ignore contours that are too small or too large
                    if area < 100 or 10000 < area:
                        continue
                    # get rect from contours
                    (x, y, w, h) = cv2.boundingRect(c)

                    finalContours.append(c)
                    # get the min area rect
                    rect = cv2.minAreaRect(c)
                    box = cv2.boxPoints(rect)
                    # convert all coordinates floating point values to int
                    box = np.intp(box)
                    # draw contours

                    # get center of contour
                    M = cv2.moments(c)
                    # get center x and y
                    if M["m00"] != 0:
                        cX = int(M["m10"] / M["m00"])
                        cY = int(M["m01"] / M["m00"])

                        if w > 10 and cX > startX:

                            cv2.drawContours(self.polarSlices[i]['image'], [
                                box], 0, self.polarSlices[i]['color'], 2)

                            if cX < self.polarSlices[i]['x2_min']:
                                self.polarSlices[i]['x2_min'] = cX

                            # draw the contour center
                            cv2.circle(self.polarSlices[i]['image'],
                                       (cX, cY), 7, (255, 255, 255), -1)
                        else:
                            # check if is noise
                            if w > 20 and h > 20:
                                cv2.drawContours(self.polarSlices[i]['image'], [
                                    box], 0, (0, 255, 0), 2)
                                # draw the contour center
                                cv2.circle(self.polarSlices[i]['image'],
                                           (cX, cY), 8, (0, 0, 255), -1)

                # draw contours
                cv2.drawContours(
                    self.polarSlices[i]['image'], finalContours, -1, self.polarSlices[i]['color'], -1)

                # draw vertical line
                cv2.line(
                    self.polarSlices[i]['image'], (self.polarSlices[i]['x2_min'], 0), (self.polarSlices[i]['x2_min'], self.polarSlices[i]['y2']), (255, 255, 255), 3)
                # named window
                # cv2.namedWindow("roi_"+str(self.polarSlices[i]['name'])+"")

                # x2_min, y2_min, x2_max, y2_max = getExtremes(
                #     self, finalContours, self.polarSlices[i]['image'], startX, startY, endX, endY)

                if self.polarSlices[i]['x2_min'] > 0:
                    level = (180 // (self.polarSlices[i]['x2_min']))
                    inverted = (
                        self.polarSlices[i]['x2_min'] * -1) + (self.polarSlices[i]['x2_min'])
                else:
                    level = 0
                # percent of x2_min
                self.polarSlices[i]['x_level'] = int(level)
                self.polarSlices[i]['inverted'] = int(
                    inverted + abs(inverted) + abs(inverted))

                # draw rectangle
                if level > 0:
                    cv2.rectangle(
                        self.polarSlices[i]['image'], (2, 2), (width-2, height-2), self.getLevel(i, level)[0], 3)

                # # draw vertical line
                # cv2.line(self.polarSlices[i]['image'], (self.polarSlices[i]['x2_min'], 0),
                #          (self.polarSlices[i]['x2_min'], self.polarSlices[i]['y2']), (169, 255, 0), 2)
                # cv2.circle(self.polarSlices[i]['image'],
                #            (self.polarSlices[i]['x2_min'], y2_min), 5, (255, 255, 0), -1)

                # draw name
                cv2.putText(self.polarSlices[i]['image'], "_x"+str(self.polarSlices[i]['x2_min'])+"_p"+str(self.polarSlices[i]['x_level'])+"_i"+str(self.polarSlices[i]['inverted']), (5, 12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

                cv2.putText(self.polarSlices[i]['image'], ""+str(self.polarSlices[i]['name'])+"", (5, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

                # get image width and height
                widthSensor = self.polarSlices[i]['x2']-1
                heightSensor = 90
                cv2.rectangle(self.polarSlices[i]['image'], (0, 0), (
                    widthSensor, heightSensor), self.polarSlices[i]['color'], 2)

                # cv2.imshow(
                #     "roi_"+str(self.polarSlices[i]['name'])+"", self.polarSlices[i]['image'])

                # cv2.resizeWindow(
                #     "roi_"+str(self.polarSlices[i]['name'])+"", widthSensor, heightSensor)

        def vertToDegrees(self, ref, totalHeight):

            # get polarY percentage
            polarYPercentage = (ref * 100) // totalHeight

            # pixels per 180
            # 50% = 180 degrees
            # 100% = 360 degrees

            # 30% = 180 degrees
            # 100% = 360 degrees
            rawDegrees = int((polarYPercentage * 36)) // 10
            return 90 + rawDegrees

        def getExtremes(self, contours, frame, startX=0, startY=0, endX=0, endY=0):
            maxArea = -1
            minLeft = frame.shape[1]-1
            minTop = frame.shape[0]-1

            if len(contours) < 1:
                return 0, 0, 0, 0

            res = []

            for i in range(len(contours)):
                temp = contours[i]
                area = cv2.contourArea(temp)
                # if area > maxArea:

                ci = i
                c = contours[ci]
                extLeftTemp = tuple(c[c[:, :, 0].argmin()][0])
                extRightTemp = tuple(c[c[:, :, 0].argmax()][0])

                if area > 300 and extLeftTemp[0] < minLeft and extLeftTemp[0] > startX:
                    minLeft = extLeftTemp[0]
                    minTop = extLeftTemp[1]
                    res = contours[ci]

            y2_max = frame.shape[0]-1
            y2_min = 0
            x2_max = frame.shape[1]-1
            x2_min = 0

            # c = max(contours, key=cv2.contourArea)

            # extLeft = tuple(c[c[:, :, 0].argmin()][0])
            # extRight = tuple(c[c[:, :, 0].argmax()][0])

            x2_min = minLeft
            y2_min = minTop

            # if extLeft[0] > startX and extRight[0] > startX + 10:
            #     x2_min = extLeft[0]
            # else:
            #     x2_min = startX

            # if extLeft[1] > startY:
            #     y2_min = extLeft[1]
            # else:
            #     y2_min = startY

            # get the max y value
            for i in range(len(res)):
                if res[i][0][1] < y2_max:
                    y2_max = res[i][0][1]
                    x2_max = res[i][0][0]
            # if res[i][0][0] < x2_min:
            #     x2_min = res[i][0][0]
            #     y2_min = res[i][0][1]

            return x2_min, y2_min, x2_max, y2_max

        threshCroped, cardinal = getVerticalDegrees(
            self, blur, radius)

        if angleOnly == True:
            return warpPolar, blur, warpPolarOriginal, cardinal

        startXwalls = 12

        # canny
        canny = cv2.Canny(blur, self.cannyParam1_polar, self.cannyParam2_polar)
        # fill gaps of canny
        kernel = np.ones((3, 3), np.uint8)
        dilate = cv2.dilate(canny, kernel, iterations=self.dilate_polar)
        # fill the first 40 pixels with black vertical
        dilate[:, 0:startXwalls] = 0
        # show
        # cv2.imshow('canny_polar_dilate', dilate)
        # cv2.imshow('canny_polar', canny)

        # draw contours from dilate
        contours, hierarchy = cv2.findContours(
            dilate, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

       # draw contours
        if len(contours) > 0:
            cv2.drawContours(warpPolar, contours, -1, (0, 255, 0), 1)

            x2_min, y2_min, x2_max, y2_max = getExtremes(
                self, contours, dilate)

            # draw vertical line
            cv2.line(warpPolar, (x2_min, 0),
                     (x2_min, warpPolar.shape[0]), (169, 255, 0), 2)
            cv2.circle(warpPolar, (x2_min, y2_min), 15, (0, 0, 255), -1)
            # put text
            # detectionInDegrees = int((y2_min * 36) // 10)
            detectionInDegrees = vertToDegrees(
                self, y2_min, warpPolar.shape[0])
            cv2.putText(warpPolar, "x2_min_"+str(x2_min)+"_y2_min_"+str(y2_min)+"_*"+str(int(detectionInDegrees))+"", (x2_min + 20, y2_min),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, 1)

            obstacleCoords = self.angleToCartesian(detectionInDegrees, x2_min)

            obstacles = []
            x, y = obstacleCoords
            px, py = obstacleCoords
            dist = int(x2_min)

            cv2.putText(warpPolar, "d_"+str(dist)+"_*"+str(int(detectionInDegrees))+"", (warpPolar.shape[1] - 150, 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, 1)

            finalX = int(x)
            finalY = int(y)

            # if detectionInDegrees > 180:
            #     finalX = int(x * -1)
            #     finalY = int(y * -1)

            if emit == True:
                maxDist = 360
            else:
                maxDist = 180
                # dist = int(dist-7)

            if emit == True:

                model = {
                    'id': str(time.time()),
                    'uniqueId': str(time.time()),
                    'w': 20,
                    'h': 20,
                    'x': finalX,
                    'y': finalY,
                    'px': finalX,
                    'py': finalY,
                    'angle': int(detectionInDegrees),
                    'closest': False,
                    'index': -1,
                    'dist': dist,
                    'class': 'obstacles',
                    'silence': 0.5 + (dist / maxDist),
                    'angleP': int(self.AngleRoot),
                }

                obstacles.append(model)

                if self.send != None:
                    self.send(
                        "/obstaclesVert", obstacles)

            # convert y2_min to degrees

            # draw Front Left - Front Right - Back Left - Back Right

            if warpPolar.shape[0] > 0:

                refY = self.polarY + self.polarFov // 2
                depth = int(self.polarFov * 1.2)

                sectorHeight = warpPolar.shape[0] // 4

                # draw line refY
                cv2.line(warpPolar, (0, refY), (warpPolar.shape[1], refY),
                         (255, 0, 255), 5)

                # QUADRANTS NEGATIVE
                self.quadrantsNegative = [
                    {
                        'x': 0,
                        'y': refY - sectorHeight,
                        'x2': depth,
                        'y2': refY,
                        'color': (255, 0, 0),
                        'name': 'n_fr_n'
                    },
                    # center
                    {
                        'x': 0,
                        'y': refY - sectorHeight * 2,
                        'x2': depth,
                        'y2': refY - sectorHeight,
                        'color': (0, 0, 255),
                        'name': 'n_fl'
                    },
                    {
                        'x': 0,
                        'y': refY - sectorHeight * 3,
                        'x2': depth,
                        'y2': refY - sectorHeight * 2,
                        'color': (255, 0, 255),
                        'name': 'n_bl'
                    },
                    {
                        'x': 0,
                        'y': refY - sectorHeight * 4,
                        'x2': depth,
                        'y2': refY - sectorHeight * 3,

                        'color': (255, 255, 0),
                        'name': 'n_br'
                    },
                    {
                        'x': 0,
                        'y': refY - sectorHeight * 4 - sectorHeight // 2,
                        'x2': 90,
                        'y2': refY - sectorHeight * 4,
                        'color': (0, 160, 255),
                        'name': 'n_fr_p'
                    }
                ]

                # QUADRANTS POSITIVE
                self.quadrantsPositive = [
                    {
                        'x': 0,
                        'y': refY - sectorHeight,
                        'x2': depth,
                        'y2': refY,
                        'color': (255, 0, 0),
                        'name': 'p_fr_p'
                    },
                    {
                        'x': 0,
                        'y': refY,
                        'x2': depth,
                        'y2': refY + sectorHeight,
                        'color': (255, 255, 0),
                        'name': 'p_br'
                    },
                    {
                        'x': 0,
                        'y': refY + sectorHeight,
                        'x2': depth,
                        'y2': refY + sectorHeight * 2,
                        'color': (255, 0, 255),
                        'name': 'p_bl'
                    },
                    {
                        'x': 0,
                        'y': refY + sectorHeight * 2,
                        'x2': depth,
                        'y2': refY + sectorHeight * 3,

                        'color': (0, 0, 255),
                        'name': 'p_fl'
                    },
                    {
                        'x': 0,
                        'y': refY + sectorHeight * 3,
                        'x2': 90,
                        'y2': refY + sectorHeight * 3 + sectorHeight // 2,

                        'color': (0, 160, 255),
                        'name': 'p_fr_n'
                    }

                ]

                # iterate quadrantsNegative
                for i in range(len(self.quadrantsNegative)):
                    # bgr color
                    color = self.quadrantsNegative[i]['color']
                    x = self.quadrantsNegative[i]['x']
                    y = self.quadrantsNegative[i]['y']
                    x2 = self.quadrantsNegative[i]['x2']
                    y2 = self.quadrantsNegative[i]['y2']
                    name = self.quadrantsNegative[i]['name']

                    if y < 0:
                        y = 0

                    if y2 - y > 0:
                        self.polarSlices.append({
                            'name': name,
                            'x': x,
                            'y': y,
                            'x2': x2,
                            'y2': y2,
                            'color': color,
                            'alarm_color': (255, 255, 255),
                            'silence': 0,
                            'index': i,
                            'polo': 'negative'
                        })
                        #  draw rectangle
                        cv2.rectangle(warpPolar, (x, y),
                                      (x2, y2), color, 3)

                        cv2.putText(warpPolar, ""+str(self.quadrantsNegative[i]['name'])+"_y_"+str(y)+"y2"+str(y2)+"", (x, y + 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1, cv2.LINE_AA)

                        cv2.line(warpPolar, (x, y + self.polarFov // 2),
                                 (x2, y + self.polarFov // 2), (0, 0, 0), 1)

                # iterate quadrantsPositive
                for i in range(len(self.quadrantsPositive)):
                    # bgr color
                    color = self.quadrantsPositive[i]['color']
                    x = self.quadrantsPositive[i]['x']
                    y = self.quadrantsPositive[i]['y']
                    x2 = self.quadrantsPositive[i]['x2']
                    y2 = self.quadrantsPositive[i]['y2']
                    name = self.quadrantsPositive[i]['name']

                    if y < 0:
                        y = 0

                    if y2 > warpPolar.shape[0]:
                        y2 = warpPolar.shape[0]

                    if y < y2 and y2 > 0:
                        if y2 - y > 0:
                            self.polarSlices.append({
                                'name': name,
                                'x': x,
                                'y': y,
                                'x2': x2,
                                'y2': y2,
                                'color': color,
                                'alarm_color': (255, 255, 255),
                                'silence': 0,
                                'index': i,
                                'polo': 'positive'
                            })
                            #  draw rectangle
                            cv2.rectangle(warpPolar, (x, y),
                                          (x2, y2), color, 3)

                            cv2.putText(warpPolar, ""+str(self.quadrantsPositive[i]['name'])+"_y_"+str(y)+"y2"+str(y2)+"", (x, y + 30),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

                            cv2.line(warpPolar, (x, y - self.polarFov // 2),
                                     (x2, y - self.polarFov // 2), (0, 0, 0), 1)

        ret, thresh = cv2.threshold(
            blur, self.threshold_polar, 255, cv2.THRESH_BINARY)

        # threshold warpPolarGray
        ret, threshForMask = cv2.threshold(
            blur, self.threshold_formask, 255, cv2.THRESH_BINARY)

        width = threshForMask.shape[1]

        # fill with black
        threshForMask[:, 40:width] = 0
        threshForMask[:, 0:24] = 255

        # apply blur
        # threshForMask = cv2.GaussianBlur(
        #     threshForMask, self.blur_polar_mask, 0)

        # invert
        threshForMask = cv2.bitwise_not(threshForMask)

        # mask warpPolarOriginal

        warpToMask = cv2.bitwise_and(
            warpToMask, warpToMask, mask=threshForMask)

        # show
        # cv2.imshow('threshForMask_mask', threshForMask)
        # cv2.imshow('threshForMask', warpToMask)

        generateROIs(self, warpToMask, 28)
        # show thresh
        # cv2.imshow('threshold_polar', thresh)

        cv2.putText(warpPolar, str("polarY_"+str(self.polarY)+"_"+str(self.polarYpercent)+"%---"+str(self.polarDegrees)+"*"),
                    (90, self.polarY), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1, cv2.LINE_AA)
        # draw polarY line
        cv2.line(warpPolar, (0, self.polarY), (warpPolar.shape[1], self.polarY),
                 (255, 0, 255), 1)

        # draw polarY line
        cv2.line(warpPolar, (0, self.polarY-self.polarFov // 2),
                 (warpPolar.shape[1], self.polarY-self.polarFov // 2), (0, 0, 255), 1)

        cv2.line(warpPolar, (0, self.polarY+self.polarFov // 2),
                 (warpPolar.shape[1], self.polarY+self.polarFov // 2), (0, 0, 255), 1)

        return warpPolar, blur, warpPolarOriginal, cardinal

        # dilate and erode
        # # dilate
        # kernel = np.ones((5, 5), np.uint8)
        # dilation = cv2.dilate(thresh, kernel, iterations=1)
        # # erode
        # erosion = cv2.erode(dilation, kernel, iterations=1)
        # # show
        # cv2.imshow('erosion', erosion)

    def updateSoundEmmiters(self, frame, mined, frame_full, minDistance=2, maxDistance=120, multiplier=3):
        # print(json.dumps(mapItems, indent=4, sort_keys=True)  )
        # print('mapItems', len(mapItems))

        # create new window and plot positions

        # create a 512x288 image
        frame_full = np.zeros((288, 512, 3), dtype="uint8")

        finalRadarPlot = np.zeros_like(mined)

        # draw radius maxDistance
        cv2.circle(finalRadarPlot, normalizeRadarPlot(
            0, 0, mined), maxDistance, (0, 255, 0), 1)
        # draw radius minDistance
        cv2.circle(finalRadarPlot, normalizeRadarPlot(
            0, 0, mined), minDistance, (0, 0, 255), 1)

        # # combine image with finalRadarPlot
        # finalRadarPlot = cv2.bitwise_or(finalRadarPlot, grid)

        # draw self.cardinal text
        cv2.putText(finalRadarPlot, str(self.cardinal), (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        cv2.putText(finalRadarPlot, str(self.AngleRoot), (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        # north position
        nx, ny = (0, maxDistance + 14)
        rotatedNorth = rotateRadar(
            (0, 0), (nx, ny), radians(int(self.AngleRoot)))

        cv2.putText(finalRadarPlot, 'N', normalizeRadarPlot(int(rotatedNorth[0]), int(
            rotatedNorth[1]), mined), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        degreesRadar = []
        for i in range(0, 360, 10):
            x = int(maxDistance * math.cos(math.radians(i)))
            y = int(maxDistance * math.sin(math.radians(i)))

            rotatedPOS = rotateRadar(
                (0, 0), (x, y), radians(int(self.AngleRoot)))

            cv2.circle(finalRadarPlot, normalizeRadarPlot(
                int(rotatedPOS[0]), int(rotatedPOS[1]), mined), 2, (255, 255, 0), -1)
            # draw line from center to xy
            if (i < 150 and i > 30):
                cv2.line(finalRadarPlot, normalizeRadarPlot(
                    0, 0, mined), normalizeRadarPlot(x, y, mined), (255, 255, 0), 1)
            extra = 4
            # create bounding box
            x1 = x - extra
            y1 = y - extra
            x2 = x + extra
            y2 = y + extra
            degreesRadar.append([x1, y1, x2, y2])

        totalEnemies = 0
        if len(self.mapItems) > 0:

            for i in range(len(self.mapItems)):

                item = self.mapItems[i]

                item_x = item['x']
                item_y = item['y']

                if item['className'] == 'enemy':
                    totalEnemies = totalEnemies + 1
                # apply global rotation

                # print("updateSoundEmmiters_____mapItems__01", item)

                if abs(item_x) < minDistance or abs(item_y) < minDistance:

                    if item['className'] != 'enemy':
                        continue
                if abs(item_x) > maxDistance or abs(item_y) > maxDistance:
                    continue

                # print("updateSoundEmmiters_____mapItems__len", len(self.mapItems))

                soundposition = [item_x * multiplier, item_y * multiplier]
                # calculate x and y distance
                dist = int(sqrt((item_x - 0)**2 + (item_y - 0)**2))

                timecode = time.time()
                id = ''+str(dist)+'_'+item['className'] + \
                    '_x'+str(item_x)+'_y'+str(item_y)+'_t'+str(timecode)+''

                # apply global rotation
                soundposition = rotateRadar(
                    (0, 0), soundposition, radians(int(self.AngleRoot)))
                rotated = rotateRadar(
                    (0, 0), (item_x, item_y), radians(int(self.AngleRoot)))

                finalCoords = normalizeRadarPlot(
                    int(rotated[0]), int(rotated[1]), mined, True)

                self.detections.append(
                    [finalCoords[0]-5, finalCoords[1]-5, 10, 10, id, finalCoords[2], soundposition[0], soundposition[1]])

                if (item['className'] == 'enemy'):
                    # red
                    cv2.circle(finalRadarPlot, (finalCoords[0], finalCoords[1]),
                               5, (0, 0, 255), -1)

                elif (item['className'] == 'friend'):
                    # purple
                    cv2.circle(finalRadarPlot, (finalCoords[0], finalCoords[1]),
                               5, (255, 0, 255), -1)
                elif (item['className'] == 'friend_blue'):
                    # blue
                    cv2.circle(
                        finalRadarPlot, (finalCoords[0], finalCoords[1]), 5, (255, 0, 0), -1)
                elif (item['className'] == 'friend_yellow'):
                    # yellow
                    cv2.circle(finalRadarPlot, (finalCoords[0], finalCoords[1]),
                               5, (27, 205, 247), -1)
                else:
                    # pink
                    cv2.circle(finalRadarPlot, (finalCoords[0], finalCoords[1]),
                               5, (255, 0, 255), -1)

            boxes_ids = tracker.update(self.detections)
            closest = -1
            closestId = -1

            finalDetections = []
            finalAIMList = []

            if len(boxes_ids) < 1:
                if self.send != None:
                    print("[RADAR_DEBUG] /trackeds EMPTY - mapItems:", len(self.mapItems))
                    self.send("/trackeds", [])

            for i in range(len(boxes_ids)):

                box_id = boxes_ids[i]

                x = box_id[0]
                y = box_id[1]
                w = box_id[2]
                h = box_id[3]
                id = box_id[4]
                realId = box_id[5]
                angle = box_id[6]
                px = box_id[7]
                py = box_id[8]

                # get the dist value from realId
                dist = int(realId.split("_")[0])

                model = {
                    'id': realId,
                    'uniqueId': id,
                    'w': w,
                    'h': h,
                    'x': x,
                    'y': y,
                    'px': px,
                    'py': py,
                    'angle': angle,
                    'closest': False,
                    'index': -1,
                    'dist': dist,
                    'silence': -1,
                    'angleP': int(self.AngleRoot),
                }

                if closest > 0 and dist < closest:
                    closest = dist
                    closestId = i
                    model['closest'] = True

                if closest < 0:
                    closest = dist
                    closestId = i
                    model['closest'] = True

                color = (255, 255, 255)
                # check if id string contains enemy
                if 'enemy' in realId:
                    model['class'] = 'enemy'
                    silence, color = distSignal(dist, maxDistance)
                    model['silence'] = silence
                    # check if realId string contains friend
                if 'friend' in realId:
                    model['class'] = 'friend'
                    color = (255, 255, 255)
                    silence = distSignal(dist, maxDistance)[0]
                    model['silence'] = silence

                model['color'] = color

                finalDetections.append(model)

                if i == len(boxes_ids) - 1:
                    # convert finalDetections to json string
                    if self.send != None:
                        print("[RADAR_DEBUG] /trackeds FOUND:", len(finalDetections), "entities:", [d.get('class','?') for d in finalDetections])
                        self.send(
                            "/trackeds", finalDetections)

                cv2.putText(finalRadarPlot, "("+str(id)+")_"+str(realId)+"", (x+w, y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

                cv2.rectangle(finalRadarPlot, (x-2, y-2),
                              (x+w+2, y+h+2), color, 1)

                linecolor = (255, 255, 255)
                linestroke = 1

                # distance from the ideal angle

                if model['class'] == 'enemy' and model['closest'] == True:
                    angleDistance = int(abs(angle - 90))

                    realDistance = angleDistance

                    if angle - 90 < 0:
                        realDistance = 0 - angleDistance

                    if angleDistance < 5:
                        linestroke = 2
                        linecolor = (0, 0, 255)
                    # draw a line from center to item
                    cv2.line(finalRadarPlot, normalizeRadarPlot(
                        0, 0, mined), (x+5, y+5), linecolor, linestroke)

                    cv2.putText(finalRadarPlot, "("+str(angleDistance)+")_("+str(int(angle))+")", (x+w+10, y+h+10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, linecolor, 1, cv2.LINE_AA)

                    cv2.putText(finalRadarPlot, "agd_("+str(int(angleDistance))+")", (10, 90),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, linecolor, 1, cv2.LINE_AA)

                    # CARTESIAN AIM MODEL
                    newposition = [int(realDistance * 4), int(200)]
                    model = {
                        'id': id,
                        # 'position': ""+str(realDist * 4)+"_"+str(depth * 4)+"",
                        'position': newposition,
                        'px': int(newposition[0]),
                        'py': int(newposition[1]),
                        'x': int(x),
                        'y': int(y),
                        'angle': int(angle),
                        'angleP': int(angleDistance),
                        'angleRoot': int(self.AngleRoot),
                        'dist': int(realDistance),
                        'emissionDist': int(dist),
                        'silence': silence,
                    }
                    if angleDistance < 75:
                        finalAIMList.append(model)

                    if angleDistance <= 5:
                        if self.send != None:
                            self.send("/aimaligned", True)
                    else:
                        if self.send != None:
                            self.send("/aimaligned", False)

                    # send osc message
                    if self.send is not None:
                        self.send("/aim", finalAIMList,
                                  len(finalAIMList))

                    # draw a vertical line at the center
                    if realDistance < 0:
                        hCenter = frame_full.shape[1] // 2 + \
                            realDistance * 3.5
                    else:
                        hCenter = frame_full.shape[1] // 2 + \
                            realDistance * 3.5
                        # lerp hCenter
                        hCenter = lerp(
                            frame_full.shape[1] // 2, frame_full.shape[1] // 2 + realDistance * 2.5, 0.5)
                    cv2.line(frame_full, (int(hCenter), 0),
                             (int(hCenter), frame_full.shape[0]), linecolor, 1)

                    # cv2.putText(frame_full, "("+str(angleDistance)+")_("+str(int(angle))+")", (int(hCenter) + 10, frame_full.shape[0] // 2),
                    #             cv2.FONT_HERSHEY_SIMPLEX, 1, linecolor, 1, cv2.LINE_AA)

                    # show

                # cv2.imshow('frame_full', frame_full)

                if len(finalAIMList) < 1:
                    if self.send != None:
                        self.send("/aim", [], 0)

            # if closestId is not none
            if closestId > -1 and len(boxes_ids) > 0:
                box_id = boxes_ids[closestId]

                x = box_id[0]
                y = box_id[1]
                w = box_id[2]
                h = box_id[3]
                id = box_id[4]
                realId = box_id[5]

                # get the dist value from realId
                dist = int(realId.split("_")[0])

                silence, color = distSignal(dist)

                silence = dist // 100

                cv2.rectangle(finalRadarPlot, (x-4, y-4),
                              (x+w+4, y+h+4), color, 3)

            else:
                if self.send != None:
                    self.send("/aimaligned", False)

        if totalEnemies < 1:
            if self.send != None:
                self.send("/aimaligned", False)

        return finalRadarPlot

    def wallDetector(self):
        # create new image 200x500
        quadrantLogs = np.zeros((500, 500, 3), dtype="uint8")

        greatestLevel = 0
        greatestLevelId = 0

        for i in range(len(self.polarSlices)):

            # get roi width
            width = self.polarSlices[i]['x2'] - self.polarSlices[i]['x']
            height = self.polarSlices[i]['y2'] - self.polarSlices[i]['y']
            # get roi name
            name = self.polarSlices[i]['name']
            color = self.polarSlices[i]['color']
            alarm_color = self.polarSlices[i]['alarm_color']
            # get roi x_level
            level = self.polarSlices[i]['x_level']
            # get roi inverted
            inverted = self.polarSlices[i]['inverted']
            # get roi x2_min
            x2_min = self.polarSlices[i]['x2_min']

            if level > greatestLevel:
                greatestLevel = level
                greatestLevelId = i

            width = width * 2
            height = height * 2

            realDist = 0

            colorCoded = self.getLevel(i, level)[0]

            if name == 'p_bl' or name == 'n_bl':
                realDist = -200
                # cv2.arrowedLine(quadrantLogs, (0, 499),
                #                 (250 - 20, 250 + 10), colorCoded, (10), 8, 0, 0.1)

            if name == 'p_br' or name == 'n_br':
                realDist = 200
                # cv2.arrowedLine(quadrantLogs, (499, 499),
                #                 (250 + 20, 250 + 20), colorCoded, (10), 8, 0, 0.1)

            if name == 'p_fr_p' or name == 'p_fr_n':
                realDist = 0
                # cv2.arrowedLine(quadrantLogs, (499, 0),
                #                 (250 + 20, 250 - 20), colorCoded, (10), 8, 0, 0.1)

            if name == 'p_fl' or name == 'n_fl':
                realDist = -200
                # cv2.arrowedLine(quadrantLogs, (0, 0),
                #                 (250 - 20, 250 - 20), colorCoded, (10), 8, 0, 0.1)

            self.polarSlices[i]['realDist'] = realDist

            if time.time() - self.lastBeepWalls > self.lastSilenceWalls:
                self.lastSilenceWalls = self.getLevel(greatestLevelId,
                                                      self.polarSlices[greatestLevelId]['x_level'])[1]
                self.lastBeepWalls = time.time()
                # t = Thread(target=self.playBeep, args=[silence])
                # t.start()
                # t.join(silence)

                # if dist < 50:
                soundposition = [
                    self.polarSlices[greatestLevelId]['realDist'] * 2, 200]

                # if self.emissionWALL == 'notSet':
                #     print("self.emissionWALL == 'notSet'")

                # if self.emissionWALL != 'notSet':
                #     print("self.emissionWALL == 'set'")

            #  draw text
            cv2.putText(quadrantLogs, ""+str(name)+"_"+str(level)+"_"+str(x2_min)+"_i"+str(inverted), (5, 200 + 30 * i),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, colorCoded, 1, cv2.LINE_AA)
            # draw a circle and split in 8 parts
            cv2.circle(quadrantLogs, (250, 250), 250, color, 1)
            #  8 semi circles around the circle
            cv2.ellipse(quadrantLogs, (250, 250),
                        (250, 250), 0, 0, 45, color, 1)

        # show
        return quadrantLogs

    def findQuadrant(self, i, polo):

        if len(self.polarSlices) < 1:
            return None

        if polo == 'positive':
            # front right
            if (i <= 90 and i >= 0):
                obj = next(
                    (obj for obj in self.polarSlices if obj['name'] == 'p_fr_p'), None)
                return obj or None
            # # front left
            if (i <= 180 and i >= 90):
                obj = next(
                    (obj for obj in self.polarSlices if obj['name'] == 'p_fl'), None)
                return obj or None
            # back left
            if (i <= 270 and i >= 180):
                obj = next(
                    (obj for obj in self.polarSlices if obj['name'] == 'p_bl'), None)
                return obj or None
            # back right
            if (i <= 360 and i >= 270):
                obj = next(
                    (obj for obj in self.polarSlices if obj['name'] == 'p_br'), None)
                return obj or None

    def plotWallDetectors(self, frame):

        for s in range(0, 360, 10):

            # find quadrantsPositive by name
            quadrant = self.findQuadrant(s, 'positive')

            if quadrant is not None:

                colorCoded = quadrant['alarm_color']
                rayDistance = 250 // quadrant['x_level']

                if (s <= 90 and s >= 0):
                    x = int(rayDistance * math.cos(math.radians(s)))
                    y = int(rayDistance * math.sin(math.radians(s)))

                    cv2.circle(frame, normalizeRadarPlot(
                        x, y, frame), 5, colorCoded, -1)
                    cv2.line(frame, (250, 250),
                             normalizeRadarPlot(x, y, frame), quadrant['color'], 1)
                # # front left
                if (s <= 180 and s >= 90):
                    x = int(rayDistance * math.cos(math.radians(s)))
                    y = int(rayDistance * math.sin(math.radians(s)))
                    cv2.circle(frame, normalizeRadarPlot(
                        x, y, frame), 5, colorCoded, -1)
                    cv2.line(frame, (250, 250),
                             normalizeRadarPlot(x, y, frame), quadrant['color'], 1)
                # back left
                if (s <= 270 and s >= 180):
                    x = int(rayDistance * math.cos(math.radians(s)))
                    y = int(rayDistance * math.sin(math.radians(s)))
                    cv2.circle(frame, normalizeRadarPlot(
                        x, y, frame), 5, colorCoded, -1)
                    cv2.line(frame, (250, 250),
                             normalizeRadarPlot(x, y, frame), quadrant['color'], 1)
                # back right
                if (s <= 360 and s >= 270):
                    x = int(rayDistance * math.cos(math.radians(s)))
                    y = int(rayDistance * math.sin(math.radians(s)))
                    cv2.circle(frame, normalizeRadarPlot(
                        x, y, frame), 5, colorCoded, -1)
                    cv2.line(frame, (250, 250),
                             normalizeRadarPlot(x, y, frame), quadrant['color'], 1)

    def getLevel(self, i, level):

        color = (255, 255, 255)
        silence = 1
        if level < 2:
            silence = 0.8
            # light blue
            color = (180, 100, 0)
            self.polarSlices[i]['silence'] = silence
            self.polarSlices[i]['alarm_color'] = color
            return color, silence

        if level < 3:
            silence = 0.4
            color = (0, 255, 255)
            self.polarSlices[i]['silence'] = silence
            self.polarSlices[i]['alarm_color'] = color
            return color, silence
        if level < 4:

            silence = 0.2
            color = (0, 0, 255)
            self.polarSlices[i]['silence'] = silence
            self.polarSlices[i]['alarm_color'] = color
            return color, silence
        if level < 5:
            silence = 0.1
            color = (0, 150, 255)
            self.polarSlices[i]['silence'] = silence
            self.polarSlices[i]['alarm_color'] = color
            return color, silence
        if level < 6:
            silence = 0.1
            color = (0, 0, 255)
            self.polarSlices[i]['silence'] = silence
            self.polarSlices[i]['alarm_color'] = color
            return color, silence
        return color, silence

    def maskPlayer(self, frame, radiusPlayer=10):

        maskPlayer = np.zeros(frame.shape[:2], dtype="uint8")
        centerRadar = (frame.shape[1] // 2-2, frame.shape[0] // 2-2)
        # circle player mini mask
        cv2.circle(
            maskPlayer, centerRadar, radiusPlayer, 255, -1)

        maskedPlayer = cv2.bitwise_and(frame, frame, mask=maskPlayer)
        return maskedPlayer

    def maskRadar(self, frame, radius=200):

        mask = np.zeros(frame.shape[:2], dtype="uint8")
        # circle big mask
        cv2.circle(mask, (frame.shape[1] // 2,
                   frame.shape[0] // 2), radius, 255, -1)
        masked = cv2.bitwise_and(frame, frame, mask=mask)
        return masked

    def cartesianTrackings(self, frame, masked, maskedHSV):
        # TRACKER MAP ITEMS
        # CREATE NEW MASK PARAMS
        # lower_params = np.array([self.h, self.s, self.v])
        # upper_params = np.array([self.h2, self.s2, self.v2])

        # lower = np.array(
        #     [self.h_polarRadar, self.s_polarRadar, self.v_polarRadar])
        # upper = np.array(
        #     [self.h2_polarRadar, self.s2_polarRadar, self.v2_polarRadar])

        # ENEMIES
        # enemyClass = next(
        #     (obj for obj in self.radarIconClassses if obj['name'] == 'enemy'), None)
        # lower_red = np.array(enemyClass['lower'])
        # upper_red = np.array(enemyClass['upper'])

        # # FRIENDS YELLOW
        # friendYellowClass = next(
        #     (obj for obj in self.radarIconClassses if obj['name'] == 'friend_yellow'), None)
        # lower_yellow = np.array(friendYellowClass['lower'])
        # upper_yellow = np.array(friendYellowClass['upper'])

        # # FRIENDS BLUE
        # friendBlueClass = next(
        #     (obj for obj in self.radarIconClassses if obj['name'] == 'friend_blue'), None)
        # lower_blue = np.array(friendBlueClass['lower'])
        # upper_blue = np.array(friendBlueClass['upper'])

        # iterate self.radarIconClassses
        for i in range(len(self.radarIconClassses)):
            classItem = self.radarIconClassses[i]
            if classItem['name'] == 'enemy':
                lower_red = np.array(classItem['lower'])
                upper_red = np.array(classItem['upper'])
            if classItem['name'] == 'friend_yellow':
                lower_yellow = np.array(classItem['lower'])
                upper_yellow = np.array(classItem['upper'])
            if classItem['name'] == 'friend_blue':
                lower_blue = np.array(classItem['lower'])
                upper_blue = np.array(classItem['upper'])

        # DEBUG MASKS
        # lower_boundary = np.array([H,S,V])
        # upper_boundary = np.array([H2,S2,V2])
        # create new image with same size as frame

        newImage = masked.copy()
        newImageHSV = maskedHSV.copy()

        detectedItems = []
        detectedItemsENEMY = []
        detectedItemsFRIEND_YELLOW = []
        detectedItemsFRIEND_BLUE = []
        # clear mapItems
        self.mapItems.clear()
        self.detections.clear()

        newImage, detectedItemsENEMY = self.trackRadarItens(
            newImage, newImageHSV, lower_red, upper_red, 'enemy', False)

        if self.team == 'nf' or self.team == 't':
            newImage, detectedItemsFRIEND_YELLOW = self.trackRadarItens(
                newImage, newImageHSV, lower_yellow, upper_yellow, 'friend_yellow', False)
        if self.team == 'nf' or self.team == 'ct':
            newImage, detectedItemsFRIEND_BLUE = self.trackRadarItens(
                newImage, newImageHSV, lower_blue, upper_blue, 'friend_blue', False)

        # merge detectedItems
        detectedItems = detectedItemsENEMY + \
            detectedItemsFRIEND_YELLOW + detectedItemsFRIEND_BLUE

        return newImage, detectedItems

    def normalizeCartesian(self, _X, _Y, targetCenter):
        finalX = _X
        finalY = _Y
        if _X > targetCenter[0]:
            finalX = _X - targetCenter[0]
        else:
            finalX = targetCenter[0] - _X
            finalX = finalX * -1

        if _Y > targetCenter[1]:
            finalY = _Y - targetCenter[1]
            finalY = finalY * -1
        else:
            finalY = targetCenter[1] - _Y

        return finalX, finalY

    def floorMapTrackings(self, frame, floorMap, floorMapInv, radius):
        # cv2.imshow('floorMap', floorMap)
        # cv2.imshow('floorMapInv', floorMapInv)

        # warpedFloor = cv2.linearPolar(src=floorMap, center=(
        #     frame.shape[0]/2, frame.shape[1]/2), maxRadius=radius, flags=cv2.WARP_FILL_OUTLIERS)

        # POLAR WARP FRAME
        # warpedFloor, blurPolar, warpPolarOriginal, cardinal = self.polarDetector(
        #     floorMap, radius, True, True, True)

        if self.send is not None:
            # self.floorGridTimer = Timer(
            #     0.5, self.send, ["/floorgrid", {'floorGrid': self.floorGrid}])
            # self.floorGridTimer.start()

            if len(self._ObDistances) > 0:
                multiplier = 16
                maxDist = 420
                minDist = 20
                obstacles = []
                # iterate over self._ObDistances
                # sort by dist
                self._ObDistances = sorted(
                    self._ObDistances, key=lambda k: k['dist'])

                for i in range(1):

                    _X = int(self._ObDistances[i]['x'])
                    _Y = int(self._ObDistances[i]['y'])
                    _RX = int(self._ObDistances[i]['rx'])
                    _RY = int(self._ObDistances[i]['ry'])
                    detectionInDegrees = self._ObDistances[i]['angle']
                    dist = int(self._ObDistances[i]['dist'])

                    # self._gridImageF height
                    height = self._gridImageF.shape[0]
                    width = self._gridImageF.shape[1]
                    targetCenter = [width // 2, height // 2]

                    finalX, finalY = self.normalizeCartesian(
                        _X, _Y, targetCenter)

                    finalRX, finalRY = self.normalizeCartesian(
                        _RX, _RY, targetCenter)

                    finalX = int(finalX * multiplier)
                    finalY = int(finalY * multiplier)
                    finalRX = int(finalRX * multiplier)
                    finalRY = int(finalRY * multiplier)
                    dist = int(dist * (multiplier+1))

                    model = {
                        'id': str(time.time()),
                        'uniqueId': str(time.time()),
                        'w': 20,
                        'h': 20,
                        'x': finalX,
                        'y': finalY,
                        'px': finalRX,
                        'py': finalRY,
                        'angle': int(detectionInDegrees),
                        'closest': False,
                        'index': -1,
                        'dist': dist,
                        'class': 'obstacles',
                        'silence': 0.01 + (dist / maxDist),
                        'angleP': int(self.AngleRoot),
                        'maxDist': maxDist,
                        'minDist': minDist,
                    }

                    if (dist < maxDist):
                        obstacles.append(model)

                    # put text self._gridImageF
                    # text1 = "_d_"+str(dist)+""
                    # "x_"+str(_X)+"_y_"+str(_Y)+"_d_"+str(dist)+""

                    # cv2.putText(self._gridImageF, text1, (_X, _Y),
                    #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

                    # text = "x_"+str(finalX)+"_y_"+str(finalY)+"_d_"+str(dist)+""

                    text = "d_"+str(dist)+"_x_"+str(finalX)+"_w_"+str(width)+"_y_"+str(finalY)+"_h_"+str(
                        height)+"_rx_"+str(finalRX)+"_ry_"+str(finalRY)+"_a_"+str(detectionInDegrees)+""

                    cv2.putText(self._gridImageF, text, (10, height - 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

                self.send(
                    "/obstacles", obstacles)

            if self.devMode == True:
                self.send(
                    "/floorgrid", {'floorgrid': self.floorGrid, 'angleP': int(self.AngleRoot)-180})
        # cv2.imshow('warpedFloor', warpedFloor)

    def detectPinClass(self, pinImg):
        # FRIENDS YELLOW
        friendYellowClass = next(
            (obj for obj in self.radarIconClassses if obj['name'] == 'friend_yellow'), None)

        lower_yellow = np.array(friendYellowClass['lower'])
        upper_yellow = np.array(friendYellowClass['upper'])

        # FRIENDS BLUE
        friendBlueClass = next(
            (obj for obj in self.radarIconClassses if obj['name'] == 'friend_blue'), None)
        lower_blue = np.array(friendBlueClass['lower'])
        upper_blue = np.array(friendBlueClass['upper'])

        # detect friends on pinImg
        pinImgYellow, detYellow = self.trackRadarItens(
            pinImg, pinImg.copy(), lower_yellow, upper_yellow, 'friend_yellow', False, True)

        if len(detYellow) > 0:
            # put text detYellow len on pinImg
            cv2.putText(pinImgYellow, ""+str(detYellow[0]['dist'])+"_x"+str(detYellow[0]['x'])+"_y"+str(
                detYellow[0]['y'])+"", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        pinImgBlue, detBlue = self.trackRadarItens(
            pinImg, pinImg.copy(), lower_blue, upper_blue, 'friend_blue', False, True)

        if len(detBlue) > 0:
            # put text detBlue len on pinImg
            cv2.putText(pinImgBlue, "_"+str(detBlue[0]['dist'])+"_x"+str(detBlue[0]['x'])+"_y"+str(
                detBlue[0]['y'])+"_", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        # convert to bgr
        pinImgYellow = cv2.cvtColor(pinImgYellow, cv2.COLOR_HSV2BGR)
        pinImgBlue = cv2.cvtColor(pinImgBlue, cv2.COLOR_HSV2BGR)

        # stack side by side
        pinImg = np.hstack((pinImgYellow, pinImgBlue))

        return pinImg, detYellow, detBlue

    def polarTrackings(self, frame, masked, maskedHSV, radius, plot=True):

        lower_params = np.array([self.h, self.s, self.v])
        upper_params = np.array([self.h2, self.s2, self.v2])

        # show masked
        pinImg = maskedHSV.copy()
        pinImg, detYellow, detBlue = self.detectPinClass(pinImg)

        textYellow = ""
        textBlue = ""
        foundBlue = False
        foundYellow = False

        if len(detYellow) > 0:
            # sort by dist
            detYellow = sorted(detYellow, key=lambda k: k['dist'])

            textYellow = "yellow_"+str(detYellow[0]['dist'])+"_x"+str(
                detYellow[0]['x'])+"_y"+str(detYellow[0]['y'])+""
            foundYellow = True

        if len(detBlue) > 0:
            # sort by dist
            detBlue = sorted(detBlue, key=lambda k: k['dist'])

            textBlue = "blue_"+str(detBlue[0]['dist'])+"_x"+str(
                detBlue[0]['x'])+"_y"+str(detBlue[0]['y'])+""
            foundBlue = True

        # put texts
        cv2.putText(pinImg, textYellow, (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(pinImg, textBlue, (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        if self.showWindows == True and self.devMode == True:
            cv2.imshow('masked-pin', pinImg)

        if foundBlue == True or foundYellow == True:
            if self.send is not None:
                self.send("/pin-radar", True)

        # detect friends on pinImg

        self.polarSlices.clear()
        # POLAR WARP FRAME

        # POLAR WARP FRAME
        warpPolar, blurPolar, warpPolarOriginal, cardinal = self.polarDetector(
            masked, radius, False, False, True)

        if cardinal != "":

            if self.send is not None:
                self.send("/player-radar", True)
        else:
            if self.send is not None:
                self.send("/player-radar", False)

        # RADAR WALL DETECTORS
        # wallResut = self.wallDetector()

        # SEND OSC CARDINAL TOPIC

        if cardinal != self.lastCardinal:
            self.lastCardinal = cardinal
            self.send("/cardinal", cardinal)

        # MOCK
        wallResut = warpPolarOriginal
#
        if plot:
            # if self.showWindows == True and self.devMode == True:
            #     cv2.imshow('warpPolar', warpPolar)
            self.plotWallDetectors(wallResut)

        # RADAR AIM DETECTORS
        self.mapItemsVert.clear()
        # red vert
        lower_red_vert = np.array([0, 40, 100])
        upper_red_vert = np.array([20, 255, 255])
        # lower_red_vert = lower_params
        # upper_red_vert = upper_params

        # # yellow vert
        # lower_yellow_vert = np.array([8, 160, 0])
        # upper_yellow_vert = np.array([30, 255, 255])

        # # blue vert
        # lower_blue_vert = np.array([35, 210, 180])
        # upper_blue_vert = np.array([100, 255, 255])

        newPolar = warpPolarOriginal

        # newPolar = self.radarAIM(
        #     newPolar, newPolar, lower_red_vert, upper_red_vert, 'enemy')
        # newPolar = self.radarAIM(
        #     newPolar, newPolar, lower_yellow_vert, upper_yellow_vert, 'friend_yellow')
        # newPolar = self.radarAIM(
        #     newPolar, newPolar, lower_blue_vert, upper_blue_vert, 'friend_blue')
        return wallResut, newPolar

    def ghostRadarItems(self, frame):
        startTime = time.time()
        filtereds = []
        frameHSV = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        ghostlist = self.radarIconClassses.copy()
        # add white to radarIconClassses
        ghostlist.append(
            {'name': 'ghost', 'lower': [0, 0, 50], 'upper': [0, 0, 255]})

        # iterate to radarIconClassses
        for i in range(len(ghostlist)):
            # if i < 1:

            # get class
            radarClass = ghostlist[i]
            # change color to gray
            lower = np.array(radarClass['lower'])
            upper = np.array(radarClass['upper'])
            # apply mask
            mask = cv2.inRange(frameHSV, lower, upper)
            # apply mask to frameHSV
            masked = cv2.bitwise_and(frameHSV, frameHSV, mask=mask)
            # masked = cv2.cvtColor(masked, cv2.COLOR_HSV2BGR)
            filtereds.append(masked)
        #
        for i in range(len(filtereds)):
            colored = filtereds[i]
            # apply blur
            # colored = cv2.GaussianBlur(colored, (5, 5), 0)

            # get frame mean color
            # avg_color_per_row = np.average(frame, axis=0)
            # avg_color = np.average(avg_color_per_row, axis=0)
            # # get predominant color

            # get dominant color
            # data = np.reshape(frame, (-1, 3))
            # data = np.float32(data)

            # criteria = (cv2.TERM_CRITERIA_EPS +
            #             cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            # flags = cv2.KMEANS_RANDOM_CENTERS
            # compactness, labels, centers = cv2.kmeans(
            #     data, 1, None, criteria, 10, flags)

            # dmt_color = centers[0].astype(np.int32)
            grayLevel = int(0.45*255)
            dmt_color = (grayLevel, grayLevel, grayLevel)

            # paint colored with avg_color
            colored[np.where((colored != [0, 0, 0]).all(axis=2))] = [
                255, 255, 255]

            # convert to gray
            colored = cv2.cvtColor(colored, cv2.COLOR_BGR2GRAY)
            # invert colors
            # colored = cv2.bitwise_not(colored)

            # create new mask
            cloned = np.zeros_like(frame)
            # # paint all frames with avg_color
            cloned[:] = dmt_color
            # # convert to hsv
            cloned = cv2.cvtColor(cloned, cv2.COLOR_BGR2HSV)

            # # masked cloned with mask
            masked = cv2.bitwise_and(cloned, cloned, mask=colored)
            colored = masked
            # convert to bgr
            colored = cv2.cvtColor(colored, cv2.COLOR_HSV2BGR)

            # iterate to non black pixels
            pixelsList = np.argwhere(colored != [0, 0, 0])

            for pxֶ in pixelsList:
                x = pxֶ[0]
                y = pxֶ[1]
                # get pixel
                pixel = colored[x, y]
                # get pixel color
                color = (int(pixel[0]), int(pixel[1]), int(pixel[2]))
                # if is black
                if color != (0, 0, 0):
                    # paint frame with color
                    frame[x, y] = color

            # for x in range(colored.shape[0]):
            #     for y in range(colored.shape[1]):
            #         # get pixel
            #         pixel = colored[x, y]
            #         # get pixel color
            #         color = (int(pixel[0]), int(pixel[1]), int(pixel[2]))
            #         # if is black
            #         if color != (0, 0, 0):
            #             # paint frame with color
            #             frame[x, y] = color

            # put colored over frame
            # frame = cv2.addWeighted(
            #     frame, self._alpha1, colored.copy(), self._alpha2, self._beta)

            # cv2.imshow('filtered_'+str(i), colored)
        endTime = time.time()
        totalTime = endTime - startTime
        # put text
        # cv2.putText(frame, "ghostRadarItems_"+str(totalTime), (10, 20),
        #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        return frame

    def floorSegmentationPipe(self, floorHistGray, radiusPlayer):
        segmentationStart = time.time()
        floorMap, floorMapFloodInv, gridImage, blended = self.floorSegmentation(
            floorHistGray, radiusPlayer-3, self.devMode)
        segmentationEnd = time.time()
        segmentationTime = segmentationEnd - segmentationStart

        # convert to bgr
        # floorMap = cv2.cvtColor(floorMap, cv2.COLOR_GRAY2BGR)
        # floorMapFloodInv = cv2.cvtColor(floorMapFloodInv, cv2.COLOR_GRAY2BGR)

        # put text
        cv2.putText(floorMapFloodInv, "st_"+str(segmentationTime), (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1, cv2.LINE_AA)

        return floorMap, floorMapFloodInv, gridImage, blended

    def processRadar(self, frame_radar, frame_full, parentRef):

        # get parentRef params
        processStart = time.time()
        radarText = "waiting_parentRef"
        gamestate = "waiting_parentRef"
        wallDetector = False
        if parentRef != None:

            envNavigation = parentRef.parentRef.serverCallback(
                "/getconfig", "EnvironmentNavigation", "EnvironmentAlerts")

            if envNavigation["value"] == "on":
                wallDetector = True

            gamestate = parentRef.gameStateParams["name"]
            team = parentRef.roundParams['team']
            if team != "nf":
                self.team = team

            lastChange = parentRef.roundParams['lastChange']
            radarText = "team_"+team+"_lastChange_"+str(lastChange)+""

        if gamestate != "gameplay":
            return

        radius = frame_radar.shape[0] // 2
        radiusPlayer = frame_radar.shape[0] // 18
        radiusFOV = frame_radar.shape[0] // 3
        # apply the mask
        maskedPlayer = self.maskPlayer(frame_radar.copy(), radiusPlayer)
        maskedRadar = self.maskRadar(frame_radar.copy(), radius)
        maskedFOV = self.maskRadar(frame_radar.copy(), radiusFOV)
        maskedHSV = cv2.cvtColor(np.array(maskedRadar), cv2.COLOR_BGR2HSV)
        maskedHSVPlayer = cv2.cvtColor(
            np.array(maskedPlayer), cv2.COLOR_BGR2HSV)

        self.lastFrame = maskedRadar
        self.lastFrameHSV = maskedHSV
        self.lastGrayFrame = cv2.cvtColor(self.lastFrame, cv2.COLOR_BGR2GRAY)

        contrast = self.polarContrast
        brightness = self.polarBrightness
        param1 = self.polarFloorthreshParam1
        param2 = self.polarFloorthreshParam2

        if wallDetector == True:
            maskToFov = np.zeros(frame_radar.shape[:2], dtype="uint8")
            # fill all white
            maskToFov.fill(255)
            # draw a black circle in the center of the maskedFOV
            cv2.circle(maskToFov, (frame_radar.shape[1] // 2,
                                   frame_radar.shape[0] // 2), radiusPlayer-3, (0, 0, 0), -1)
            # mask maskedFOV
            maskedFOV = cv2.bitwise_or(maskedFOV, maskedFOV, mask=maskToFov)
            # detectedBrightness = self.estimateBrightness(frame_radar)

            # check if detectedBrightness is above 100
            # if detectedBrightness > 100:
            #     # contrast = 1
            #     brightness = brightness // detectedBrightness
            #     param1 = param1 // detectedBrightness

            # # floor segmentation
            # floorHist = self.applyBrightAndContrast(
            #     maskedFOV, contrast, brightness)
            maskedFOV = self.ghostRadarItems(maskedFOV)
            # filtered items show
            # cv2.imshow('maskedFOV_filtered', maskedFOV)

            # # convert to gray and apply threeshold
            floorHistGray = cv2.cvtColor(maskedFOV, cv2.COLOR_BGR2GRAY)
            # # increase contrast

            # # ret, floorHistThresh = cv2.threshold(
            # #     floorHistGray, param1, param2, cv2.THRESH_BINARY)

            with concurrent.futures.ThreadPoolExecutor(thread_name_prefix="wallDetector_") as executor:
                future = executor.submit(
                    self.floorSegmentationPipe, floorHistGray, radiusPlayer-4)
                floorMap, floorMapFloodInv, gridImage, blended = future.result()

            # TRACKINGS
            # FLOOR MAP TRACKINGS
            self.floorMapTrackings(frame_radar, floorMap,
                                   floorMapFloodInv, radius)

        # CARTESIAN TRACKINGS
        newImage, detectedCartesian = self.cartesianTrackings(
            frame_radar, maskedRadar, maskedHSV)

        # print("detectedCartesian", detectedCartesian)

        # POLAR TRACKINGS
        self.polarTrackings(frame_radar, maskedPlayer,
                            maskedHSVPlayer, radius)

        self.lastFrameTracked = newImage

        # EMISSIONS
        # update sound emmiters
        self.lastRadarPlot = self.updateSoundEmmiters(
            frame_radar, newImage, frame_full)

        processEnd = time.time()
        processTime = processEnd - processStart

        # put text
        cv2.putText(self.lastFrameTracked, radarText, (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        # return
        # put text self.lastFrameTracked
        cv2.putText(self.lastFrameTracked, "pt_"+str(processTime), (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

        # cv2.namedWindow('GuidePlay-Radar')
        if self.showWindows == True and self.devMode == True:

            if self.useMJPEGserver == True and self.runMJPEGserver == False:
                self.runMJPEGserver = True
                t = Thread(target=self.devMJPGserver(), args=[],
                           daemon=True, name="devMJPGserver")
                t.start()

            cv2.imshow('GuidePlay-Radar_mined', self.lastFrameTracked)
            cv2.imshow('GuidePlay-Radar', self.lastRadarPlot)
            # if wallDetector == True:
            #     cv2.imshow('GuidePlay-floorMapFloodInv', floorMapFloodInv)
            #     cv2.imshow('GuidePlay-gridImage', gridImage)
            #     cv2.imshow('GuidePlay-blended', blended)
            # cv2.imshow('GuidePlay-floorHist-gray', floorHistGray)
            # # cv2.imshow('GuidePlay-floorHist', floorHistThresh)

            # destroy window key q
            if cv2.waitKey(1) & 0xFF == ord('z'):
                cv2.destroyAllWindows()

    def test(self):
        print(self.lastFrame)

    def createTrackbars(self, name, size=255):
        # if not exist create window
        if not cv2.getWindowProperty(Winname, cv2.WND_PROP_VISIBLE):
            cv2.namedWindow(Winname)
        cv2.resizeWindow(Winname, 400, 300)
        cv2.createTrackbar(name, Winname, 0, size,
                           lambda x: self.updateProp(prop=name, value=x))

    def updateProp(self, prop, value):
        if prop == 'blur_polar' or prop == 'blur_polar_mask':
            # even numbers only
            if value % 2 == 0:
                value += 1
            self[prop] = (value, value)
        elif prop == 'threshold_polar':
            self.threshold_polar = value
        else:
            # if window exist
            self[prop] = value
        if cv2.getWindowProperty(Winname, cv2.WND_PROP_VISIBLE):
            cv2.setTrackbarPos(prop, Winname, value)
            # 'h', 's', 'v', 'h2', 's2', 'v2',
            # printTrackBars(['threshold',
            #                'blur_polar', 'threshold_polar', 'canny_polar', 'dilate_polar', 'erode_polar'])
