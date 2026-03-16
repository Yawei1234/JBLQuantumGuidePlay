
import numpy as np
import scipy.signal as ss
import data
import pyautogui
import threading
# import sounddevice as sd
import numpy as np
import math

import wave
import scipy.io.wavfile
import cv2
from parser_SVG import listTemplates, parseTemplates


class Theremin:
    def __init__(self, _screenWidth, _screenHeight, _callback, _parent=None, _devMode=False):

        # self.fs = 15000
        # sd.default.samplerate = self.fs
        # sd.default.channels = 2

        # a linear scale thing for making the sound
        # self.t = np.linspace(0, 1, self.fs * 1, False, dtype=np.float32)

        # # the stream
        # self.s = sd.Stream(latency='low', blocksize=1,
        #                    samplerate=self.fs, channels=1)
        # self.s.start()

        self.soundTheremin = None
        self.frequency = 0
        self.volume = 0.1
        self.waveform = 'sin'
        self.waveforms = ['sin', 'triangle', 'square']
        self.currentOctive = 2
        self.callback = _callback
        self.screenHeight = _screenHeight
        self.screenWidth = _screenWidth

        self.templatesList = listTemplates('assets/gamestates_ref/')
        self.parsedTemplates = parseTemplates(
            self.templatesList, 'assets/gamestates_ref/')
        self.currentTemplate = None
        self.templateConfirmed = None
        self.plotThread = None
        self.isPlotting = False
        self.useTemplateMap = True

        self.lastX = 0
        self.lastY = 0
        self.send = None
        self.clearTimer = None
        self.lastText = None
        self.parentREF = None
        self.devMode = False

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
            self.clearTimer = threading.Timer(20, self.clearLastText).start()

    def sgn(self, num):
        maximum = 0.1

        if num > 0:
            return maximum
        elif num < 0:
            return -maximum
        else:
            return 0

    # def runSD(self):
    #     index = 0
    #     # prev_n = None
    #     # current_freq = 440
    #     contents = []

    #     while data.runTheremin:
    #         rounds, a_index = divmod(index, len(self.t))

    #         a = rounds + self.t[a_index]

    #         # print(self.frequency)

    #         # print(current_freq)
    #         current_freq = self.frequency

    #         thing = current_freq * a * 2 * np.pi

    #         pre_amp = math.sin(thing)

    #         if self.waveform == 'Square':  # square wave
    #             pre_amp = self.sgn(pre_amp)
    #         elif self.waveform == 'Triangle':  # triangle wave
    #             ref = a * current_freq - math.floor(a * current_freq)

    #             pre_amp = abs(ref - round(ref)) * 2

    #         actual_n = n = self.volume * pre_amp / 30  # here's where amplitude comes in

    #         '''
    #         if (prev_n is not None and (prev_n <= 0 and n >= 0 or prev_n >= 0 and n <= 0)):
    #             if current_freq != self.frequency:
    #                 current_freq = self.frequency

    #                 actual_n = 0
    #         '''

    #         # print(n)
    #         # a, overflowed = s.read(1)

    #         # the thing that gets written to the stream to produce sound
    #         array = np.array((actual_n,), np.float32)

    #         contents.append(array)

    #         self.s.write(array)  # writes to stream to produce sound

    #         index += 1

    def coordsToFrequency(self, inputArray):

        screenWidth = self.screenWidth
        screenHeight = self.screenHeight
        leftX = 0
        leftY = 0
        rightX = int(inputArray[1])
        rightY = int(inputArray[2])
        scaleMode = True
        octave = self.currentOctive

        frequencyList = [523.251, 493.883, 466.164, 440, 415.305, 391.995,
                         369.994, 349.228, 329.628, 311.127, 293.665, 277.183, 261.626]
        #  c5, b4, a#4, a4, g#4, g4 f#4 f4 e4 d#4 d4 c#4 c4

        volume = 100 - ((leftY / screenHeight) * 100)

        selectedWaveForm = self.waveforms[2]

        if not scaleMode:
            frequency = (((rightX) /
                          screenWidth) * 261.625) + 261.625

        else:
            if rightX <= 1/13 * screenWidth:
                frequency = frequencyList[12]
            elif rightX <= 2/13 * screenWidth:
                frequency = frequencyList[11]
            elif rightX <= 3/13 * screenWidth:
                frequency = frequencyList[10]
            elif rightX <= 4/13 * screenWidth:
                frequency = frequencyList[9]
            elif rightX <= 5/13 * screenWidth:
                frequency = frequencyList[8]
            elif rightX <= 6/13 * screenWidth:
                frequency = frequencyList[7]
            elif rightX <= 7/13 * screenWidth:
                frequency = frequencyList[6]
            elif rightX <= 8/13 * screenWidth:
                frequency = frequencyList[5]
            elif rightX <= 9/13 * screenWidth:
                frequency = frequencyList[4]
            elif rightX <= 10/13 * screenWidth:
                frequency = frequencyList[3]
            elif rightX <= 11/13 * screenWidth:
                frequency = frequencyList[2]
            elif rightX <= 12/13 * screenWidth:
                frequency = frequencyList[1]
            else:
                frequency = frequencyList[0]

        if octave == 1:
            frequency /= 2
        elif octave == 3:
            frequency *= 2

        return [volume, frequency, selectedWaveForm]

    def getColorHeatMap(self, distance, maxDistance):
        # // 0    : blue
        # // 0.25 : cyan
        # // 0.5  : green
        # // 0.75 : yellow
        # // 1    : red

        if distance > maxDistance:
            distance = maxDistance

        r = int(255 * (1 - distance / maxDistance))
        g = int(255 * distance / maxDistance)
        b = int(20 * distance / maxDistance)

        # convert to rgb to bgr
        return [b, g, r]

    def getVolume(self, distance, maxDistance):

        if distance > maxDistance:
            distance = maxDistance

        percent = (distance / maxDistance)
        # invert percent
        volume = 0.5 - percent
        if volume < 0.1:
            volume = 0.1
        return volume

    def getFrequency(self, distance, maxDistance):
        # // 0    : blue
        # // 0.25 : cyan
        # // 0.5  : green
        # // 0.75 : yellow
        # // 1    : red
        multiplier = 10
        topFreq = 440

        if distance > maxDistance:
            distance = maxDistance

        percent = (distance / maxDistance)
        percent = 1 - percent

        frequency = (percent*multiplier) * (topFreq//multiplier)
        return frequency

    def plotTemplate(self, templateIn=None):

        if self.templateConfirmed is None:
            self.isPlotting = False
            return
        else:
            template = self.templateConfirmed

        if self.devMode == True:
            print("PLOTING_TEMPLATE", template['id'])

        plotGrid = False
        blockSize = 20
        imgTemplate = cv2.imread('assets/gamestates_ref/' +
                                 template['image'])
        # grayscale
        imgTemplate = cv2.cvtColor(imgTemplate, cv2.COLOR_BGR2GRAY)
        # increase contrast
        imgTemplate = cv2.equalizeHist(imgTemplate)
        # create a new color image
        imgTemplate = cv2.cvtColor(imgTemplate, cv2.COLOR_GRAY2BGR)

        if self.devMode == True:
            cv2.namedWindow('template_theremin', cv2.WINDOW_NORMAL)
            cv2.resizeWindow(
                'template_theremin', template['width'], template['height'])

        while self.isPlotting == True and self.currentTemplate is not None:

            template = self.templateConfirmed

            if templateIn['id'] != template['id']:
                # update imgTemplate
                imgTemplate = cv2.imread('assets/gamestates_ref/' +
                                         template['image'])
                # grayscale
                imgTemplate = cv2.cvtColor(imgTemplate, cv2.COLOR_BGR2GRAY)
                # increase contrast
                imgTemplate = cv2.equalizeHist(imgTemplate)
                # create a new color image
                imgTemplate = cv2.cvtColor(imgTemplate, cv2.COLOR_GRAY2BGR)

            x_ = self.lastX
            y_ = self.lastY

            font = cv2.FONT_HERSHEY_SIMPLEX

            img = imgTemplate.copy()
            # create a new color image same size as template
            # img = np.zeros(
            #     (template['height'], template['width'], 3), np.uint8)

            # create a grid with blockSizexblockSize for template['width'] and template['height']
            if self.devMode == True and plotGrid == True:
                totalBlocksW = template['width']//blockSize
                totalBlocksH = template['height']//blockSize
                maxDistance = 300

                for i in range(0, totalBlocksW):
                    colX = i*blockSize

                    for j in range(0, totalBlocksH):
                        colY = j*blockSize

                        cv2.rectangle(img, (colX, colY),
                                      (colX+blockSize, colY+blockSize), (0, 0, 0), 1)
                        # draw circle at center
                        centerCircle = (colX+blockSize//2, colY+blockSize//2)

                        # cv2.circle(img, centerCircle, 6, (0, 0, 0), 1)

                        distances = []
                        # iterate to elements and calculate distance

                        for element in template['elements']:
                            if element['style'] and 'fill' in element['style']:
                                fill = element['style']['fill']
                                if fill != 'transparent':
                                    color = (int(element['style']['fill'][0]), int(element['style']
                                                                                   ['fill'][1]), int(element['style']['fill'][2]))
                                    x1 = int(element['x'])
                                    y1 = int(element['y'])
                                    x2 = int(element['x']) + \
                                        int(element['width'])
                                    y2 = int(element['y']) + \
                                        int(element['height'])

                                    center = (x1 + int(element['width']) //
                                              2, y1 + int(element['height']) // 2)

                                    dist = math.sqrt((centerCircle[0] - center[0]) **
                                                     2 + (centerCircle[1] - center[1])**2)
                                    distances.append(dist)

                        # sort distances
                        distances.sort()
                        # get the first distance
                        distance = distances[0]
                        # get the max distance

                        color = self.getColorHeatMap(distance, maxDistance)
                        cv2.circle(img, centerCircle, 5,
                                   (color[0], color[1], color[2]), -1)
            else:
                distances = []
                maxDistance = 500

                for index, element in enumerate(template['elements']):
                    if element['style'] and 'fill' in element['style']:
                        fill = element['style']['fill']
                        if fill != 'transparent':
                            color = (int(element['style']['fill'][0]), int(element['style']
                                                                           ['fill'][1]), int(element['style']['fill'][2]))
                            x1 = int(element['x'])
                            y1 = int(element['y'])
                            x2 = int(element['x'])+int(element['width'])
                            y2 = int(element['y'])+int(element['height'])

                            center = (x1 + int(element['width']) //
                                      2, y1 + int(element['height']) // 2)

                            dist = math.sqrt((x_ - center[0]) **
                                             2 + (y_ - center[1])**2)

                            color = self.getColorHeatMap(dist, maxDistance)

                            if dist < int(element['width'] // 2 or dist < int(element['height']) // 2):
                                if self.devMode == True:
                                    cv2.rectangle(
                                        img, (x1, y1), (x2, y2), (color[0], color[1], color[2]), 3)
                                self.concludeDetection(
                                    "/screenreader/theremin", element['id'])

                            distances.append({
                                'id': element['id'],
                                'index': index,
                                'distance': dist,
                                'weight': element['weight'],
                                'x': center[0],
                                'y': center[1]
                            })

                            if self.devMode == True:
                                # circle on center
                                cv2.circle(img, center, 5,
                                           (color[0], color[1], color[2]), -1)

                                cv2.putText(img, element['id'], center,
                                            font, 0.4, (255, 255, 0), 1, 1)

                distances.sort(key=lambda x: x['distance'])

                # sort by greatest weight
                distances.sort(key=lambda x: x['weight'], reverse=True)

                smallestDistance = distances[0]

                frequency = self.getFrequency(
                    smallestDistance['distance'], maxDistance)

                volume = self.getVolume(
                    smallestDistance['distance'], maxDistance)

                self.frequency = frequency
                self.volume = volume
                self.waveform = 'square'

                lineColor = self.getColorHeatMap(
                    smallestDistance['distance'], maxDistance)

                # the smaller the distance the bigger the circle
                circleSize = 10

                if self.devMode == True:

                    cv2.circle(img, (x_, y_), circleSize,
                               (lineColor[0], lineColor[1], lineColor[2]), -1)

                    # draw line from center to closest element
                    cv2.line(img, (x_, y_), (smallestDistance['x'],
                                             smallestDistance['y']), (lineColor[0], lineColor[1], lineColor[2]), 3)
                    # put text
                    text = ''+str(smallestDistance['id']) + \
                        '_d'+str(smallestDistance['distance']) + \
                        '_w'+str(smallestDistance['weight'])+''

                    text2 = 'f: ' + str(frequency) + ' v: ' + str(self.volume)

                    cv2.putText(img, text, (10, 75),
                                font, 0.4, (255, 255, 0), 1, 1)

                    cv2.putText(img, text2, (10, 120),
                                font, 0.4, (255, 255, 0), 1, 1)

            if self.devMode == True:
                cv2.putText(img, 'x: ' + str(x_) + ' y: ' + str(y_), (10, 10),
                            font, 0.4, (0, 255, 0), 1, 1)

                cv2.imshow('template_theremin', img)
                # cv2.imshow('template_theremin_bg', imgTemplate)

                # if key press q break
                if cv2.waitKey(1) & 0xFF == ord('y'):
                    if plotGrid == False:
                        plotGrid = True
                    else:
                        plotGrid = False
                if cv2.waitKey(1) & 0xFF == ord('b'):
                    self.currentTemplate = None
                    self.isPlotting = False
                    break

    def coordsToHeatMap(self, x_, y_):
        # find currentTemplate in parsedTemplates
        self.templateConfirmed = next(
            (index for (index, d) in enumerate(self.parsedTemplates) if d["id"] == self.currentTemplate), None)

        if self.templateConfirmed is None:
            self.isPlotting = False
            if self.plotThread is not None:
                self.plotThread.join()
            return self.coordsToFrequency([0, x_, y_])

        self.templateConfirmed = self.parsedTemplates[self.templateConfirmed]

        if self.isPlotting == False:
            self.isPlotting = True
            self.plotThread = threading.Thread(target=self.plotTemplate,
                                               args=(self.templateConfirmed,), daemon=True)
            self.plotThread.start()

        if self.currentTemplate is None:
            self.isPlotting = False
            if self.plotThread is not None:
                self.plotThread.join()
            return self.coordsToFrequency([0, x_, y_])

        return [0, 0, 'sin']

    def checkActiveTemplate(self):

        if self.devMode == True:
            cv2.namedWindow('active_theremin', cv2.WINDOW_NORMAL)
            cv2.moveWindow('active_theremin', 500, 500)

            newImage = np.zeros((300, 300, 3), np.uint8)

        if self.parentREF is not None:
            # put text
            font = cv2.FONT_HERSHEY_SIMPLEX
            # create named window
            # cv2.resizeWindow('active_theremin', 300, 300)
            # set position
            if self.parentREF.currentTemplate is not None:
                if self.devMode == True:
                    cv2.putText(newImage, 'currentTemplate: ' + self.parentREF.currentTemplate + '', (10, 10),
                                font, 0.4, (0, 255, 0), 1, 1)
                self.currentTemplate = self.parentREF.currentTemplate
            else:
                if self.devMode == True:
                    cv2.putText(newImage, 'EMPTY___', (10, 10),
                                font, 0.4, (0, 255, 0), 1, 1)
                self.currentTemplate = None
        else:
            self.currentTemplate = None

        if self.devMode == True:
            cv2.imshow('active_theremin', newImage)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cv2.destroyAllWindows()

    # def checkActiveTemplateLegacy(self):
    #     if self.parentREF is not None:

    #         newImage = np.zeros((300, 300, 3), np.uint8)
    #         # put text
    #         font = cv2.FONT_HERSHEY_SIMPLEX
    #         # create named window
    #         cv2.namedWindow('template_theremin', cv2.WINDOW_NORMAL)
    #         cv2.resizeWindow('template_theremin', 300, 300)
    #         # set position
    #         cv2.moveWindow('template_theremin', 100, 500)
    #         if self.parentREF.screenReaderSectors is not None and len(self.parentREF.screenReaderSectors) > 0:
    #             # create a 300 x 300 empyu image

    #             # filter by active
    #             activeSectors = list(
    #                 filter(lambda x: x['selected'] != 'None', self.parentREF.screenReaderSectors))

    #             if len(activeSectors) > 0:

    #                 mappedFields = list(
    #                     map(lambda x: {
    #                         'name': x['name'],
    #                         'selected': x['selected']
    #                     }, activeSectors))

    #                 # [{'name': 'subtopmenu', 'selected': 'practice'}, {'name': 'submenu', 'selected': 'wingman'}]

    #                 # find currentTemplate in parsedTemplates
    #                 # submenu filter
    #                 submenu = next(
    #                     (index for (index, d) in enumerate(mappedFields) if d["name"] == 'submenu'), None)

    #                 if submenu is not None:
    #                     submenu = mappedFields[submenu]
    #                     # print('submenu', submenu)

    #                 subtopmenu = next(
    #                     (index for (index, d) in enumerate(mappedFields) if d["name"] == 'subtopmenu'), None)

    #                 if subtopmenu is not None:
    #                     subtopmenu = mappedFields[subtopmenu]
    #                     # print('subtopmenu', subtopmenu)

    #                 if submenu is not None and subtopmenu is not None:

    #                     cv2.putText(newImage, 'subtopmenu: ' + subtopmenu['selected'] + ' _ submenu '+str(submenu['selected'])+'', (10, 10),
    #                                 font, 0.4, (0, 255, 0), 1, 1)

    #                     if subtopmenu['selected'] == "practice" and submenu['selected'] == "deathmatch":
    #                         self.currentTemplate = "144126_home_play_practice"
    #                     elif subtopmenu['selected'] == "practice" and submenu['selected'] == "casual":
    #                         self.currentTemplate = "144126_home_play_practice"
    #                     elif subtopmenu['selected'] == "matchmaking" and submenu['selected'] == "casual":
    #                         self.currentTemplate = "144113_home_play_match"
    #                     else:
    #                         self.currentTemplate = None

    #                 if self.currentTemplate is not None:
    #                     print('checkactive-template-found',
    #                           len(activeSectors), mappedFields, self.currentTemplate)

    #         else:
    #             cv2.putText(newImage, 'EMPTY___'+str(len(self.parentREF.screenReaderSectors))+'', (10, 10),
    #                         font, 0.4, (0, 255, 0), 1, 1)
    #         # show image
    #         cv2.imshow('template_theremin', newImage)

    def startThereminCapture(self):

        self.lastX = 0
        self.lastY = 0

        sameCount = 0
        delta = 0

        while data.runTheremin == True:

            # LEGACY CODE
            # if self.soundTheremin is None:
            #     self.soundTheremin = threading.Thread(
            #         target=self.run, daemon=True).start()
            # else:
            #     if self.soundTheremin.is_alive() == False:
            #         self.soundTheremin = threading.Thread(
            #             target=self.runSD, daemon=True).start()

            x = pyautogui.position()[0]
            y = pyautogui.position()[1]
            delta += 1

            if x == self.lastX and y == self.lastY:
                sameCount += 1

                if delta % 4 == 0:
                    if self.useTemplateMap == True:
                        # print("theremim CHECKIN_TEMPLATE", x, y)
                        self.checkActiveTemplate()

                # print('theremim not moving', sameCount)
                # if sameCount >= 10000:
                #     self.volume = 0
                #     self.callback(self.screenWidth, self.screenHeight, 0, 0, self.volume, self.frequency,
                #                   self.waveform, "iddle")
                #     print('theremim stopped sameness 1')
                #     continue
                # else:
                # continue

            else:
                self.lastX = x
                self.lastY = y
                # if delta is multiple of 4
                if delta % 2 == 0:
                    if self.useTemplateMap == True:
                        # print("theremim CHECKIN_TEMPLATE", x, y)
                        self.checkActiveTemplate()

                sameCount = 0
                # print("theremim moving", x, y)
            if self.currentTemplate is not None:
                self.coordsToHeatMap(x, y)
                self.callback(self.screenWidth, self.screenHeight, x,
                              y, self.volume, self.frequency, self.waveform, "started")
            else:
                self.isPlotting = False
                if self.plotThread is not None:
                    self.plotThread.join()

                self.frequency = 0
                self.volume = 0.1
                self.waveform = 'none'
                self.callback(self.screenWidth, self.screenHeight, x,
                              y, self.volume, self.frequency, self.waveform, "started")
        else:
            self.callback(self.screenWidth, self.screenHeight, 0,
                          0, 0, 0, 'none', "stopped")

            print('theremim stopped 2')
