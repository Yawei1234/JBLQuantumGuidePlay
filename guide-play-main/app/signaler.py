from sound import Emission
import data
import json
import time
import cv2
import numpy as np
from threading import Timer, Thread

global emissionENEMY
global lastBeepENEMY
global lastSilenceENEMY

emissionENEMY = 'notSet'
lastBeepENEMY = 0
lastSilenceENEMY = 0


def soundUpdatePosition(emmiter, position, id, overlap=True):
    # Update the position of the given emmiter
    emmiter.updatePosition(position, overlap)
    # Return
    return


def soundStart(emmiter, position, id):
    # print(f"soundStart [{position}] [{id}]")
    if emmiter.isPlaying:
        return
    emmiter.play()
    return


def soundEnd(emmiter, position, id):
    # print(f"soundEnd [{position}] [{id}]")
    # print(emmiter)
    emmiter.setEnded()
    # delete emmiter
    del emmiter
    # print("emitter_deleted", id)
    return


def signaler(contents, SoundPlotFrame, multiplier=3):

    # if closestId is not none

    global emissionENEMY
    global lastBeepENEMY
    global lastSilenceENEMY

    for i in range(len(contents)):

        item = contents[i]
        # print("signaler", contents[i])
        if item['closest'] == True:
            box_id = item

            x = box_id['x']
            y = box_id['y']
            w = box_id['w']
            h = box_id['h']
            id = box_id['uniqueId']
            realId = box_id['id']

            print("\nsignaling____", realId, id)

            # get the dist value from realId
            dist = int(realId.split("_")[0])

            silence = 1

            color = (0, 255, 0)

            if (dist > 50):
                # purple
                silence = 0.7
                color = (255, 0, 255)
            elif (dist > 40):
                # cyan
                silence = 0.350
                color = (255, 255, 0)
            elif (dist > 30):
                # yellow
                silence = 0.150
                color = (0, 255, 255)
            elif (dist > 10):
                # red
                silence = 0.05
                color = (0, 0, 255)
            else:
                # red
                color = (0, 0, 255)
                silence = 0

            silence = dist // 100

            # if dist < 50:
            # soundposition = [x * multiplier, y * multiplier]

            if 'enemy' in realId:

                if time.time() - lastBeepENEMY > lastSilenceENEMY:
                    lastSilenceENEMY = silence
                    lastBeepENEMY = time.time()
                    # t = Thread(target=playBeep, args=[silence])
                    # t.start()
                    # t.join(silence)

                    # if dist < 50:
                    soundposition = [x * multiplier, y * multiplier]

                    if emissionENEMY == 'notSet':
                        # print("emissionENEMY == 'notSet'")
                        emissionENEMY = Emission(
                            realId, 'sounds/beep_enemy0.wav', soundposition, 0, 'square')

                    if emissionENEMY != 'notSet':
                        # print("emissionENEMY == 'set'")
                        # emissionENEMY.updatePosition(soundposition)
                        # emissionENEMY.play()

                        # cv2.rectangle(SoundPlotFrame, (x-4, y-4),
                        #               (x+w+4, y+h+4), color, 2)

                        # cv2.imshow('SoundPlotFrame', SoundPlotFrame)
                        print("emissionENEMY", emissionENEMY.isPlaying)

                        t = Thread(target=soundUpdatePosition, args=[
                            emissionENEMY, soundposition, realId, False])
                        t.start()

                        # q = Timer(duration + silence, soundEnd, args=[
                        #     emissionENEMY, soundposition, id])
                        # q.start()

    # show image


def run(radarDetectors):
    index = 0
    print("sound running", radarDetectors)

    # # create a blank image 500x500
    # SoundPlotFrame = np.zeros((500, 500, 3), np.uint8)

    # while data.runRadar:
    #     contents = COME_FROM
    #     if len(contents) > 0:
    #         print("sound running", len(contents))

    # find the minimum distance
    # closestId = None
    # closestDist = 1000
    # for i in range(len(contents)):
    #     item = contents[i]
    #     if item['dist'] < closestDist:
    #         closestDist = item['dist']
    #         closestId = item['id']

    #     if i == len(contents) - 1:
    #         for i in range(len(contents)):
    #             item = contents[i]
    #             if item['id'] == closestId:
    #                 item['closest'] = True
    #             else:
    #                 item['closest'] = False
    #         # jsonX = json.dumps(contents, indent=4, sort_keys=True)
    #         # print("sound running", jsonX)
    #         signaler(contents, SoundPlotFrame, 3)
