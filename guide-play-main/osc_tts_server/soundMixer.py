import pygame
import time
import numpy as np
import threading
import sys
import data
from pynput.keyboard import Key, Listener
from UltraDict import UltraDict
from pydub import AudioSegment
from sound import Emission, DynamicEmission, trimSilence, addSilence, concatenateSound, WhiteNoise, segToNP
import data


global ultraTimer

q = None
ultraTimer = None

size = 44100
pygame.init()

mymixer = pygame.mixer
mymixer.set_num_channels(26)
mymixer.init(frequency=size, size=-16, channels=2)

buffer = np.random.randint(-32768, 32767, size)
buffer = np.repeat(buffer.reshape(size, 1), 2, axis=1)
sound = pygame.sndarray.make_sound(buffer)
pygame.time.wait(int(sound.get_length()))

sound1 = mymixer.Sound(sound)
# sound1.play()


class SoundMixer:
    def __init__(self, path="../app"):
        self.path = path
        self.entities = []
        self.lastDicts = []
        self.rootThread = None
        self.controlRef = False
        pass

    def startEntities(self):

        self.entities = [
            {
                'id': 1,
                'class': 'aim',
                'segment': AudioSegment.empty(),
                'emmiter': None,
                'isRunning': False,
                'wav': 'beep_aim.wav',
            },
            {
                'id': 2,
                'class': 'enemy',
                'segment': AudioSegment.empty(),
                'emmiter': None,
                'isRunning': False,
                'wav': 'beep_enemy0.wav',
            },
            {
                'id': 3,
                'class': 'friend',
                'segment': AudioSegment.empty(),
                'emmiter': None,
                'isRunning': False,
                'wav': 'beep_friend0.wav',
            },
        ]
        lastDicts = []
        for entity in self.entities:
            lastDicts.append({
                'id': entity['id'],
                'class': entity['class'],
            })
        self.lastDicts = lastDicts

    def start(self):
        self.controlRef = True
        self.startEntities()

    def stop(self):
        self.controlRef = False
        self.rootThread.join()

    def getSegmentById(self, id):

        # find segment by id
        for entity in self.entities:
            if entity['id'] == id:
                return entity
        return None

    def updateSegment(self, segment, id, isRunning, motif):

        ent = self.getSegmentById(id)
        if ent is not None:
            print("\nsegment-updated", id, motif)
            ent['segment'] = segment
            ent['isRunning'] = isRunning

    def stopChannel(self, channel, withSilence=False, withFade=False):
        if mymixer.get_init():
            if withSilence:
                # generate silence 2 channels segment
                silence = AudioSegment.silent(duration=100, frame_rate=size)
                # convert to numpy array
                converted = segToNP(silence)
                shaped = np.repeat(converted[0].reshape(
                    converted[0].shape[0], 1), 2, axis=1)
                mymixer.Channel(channel).play(
                    pygame.sndarray.make_sound(shaped), loops=0, fade_ms=100)
                return
            if withFade:
                self.fadeOut(channel, 100)
                return
            mymixer.Channel(channel).stop()

    def playChannel(self, snd, id, className, volume):
        if mymixer.get_init():
            # mymixer.Channel(1).stop()
            # if is not playing
            if not mymixer.Channel(id).get_busy():
                if className != 'aim':
                    snd.set_volume(volume)
                # check if need fade in
                if mymixer.Channel(id).get_volume() == 0:
                    self.fadeIn(id, 100)
                mymixer.Channel(id).play(snd, loops=0)
                # pygame.time.wait(int(snd.get_length()))
            else:
                pass

    def generateSilencedSound(self, segment, silence):
        # add silence at the end of the current SFX - addSilence
        # combined = addSilence(segment, silence)
        # concatenateSound X times
        # combined_segment = concatenateSound(combined, 2)

        # totalDuration = silence + len(combined_segment) / 1000
        t1 = time.time()
        totalDuration = len(segment) / 1000
        converted = segToNP(segment)
        t2 = time.time()
        print("time-to-convert-silence", (t2 - t1))

        return [pygame.sndarray.make_sound(converted[0]), totalDuration]

    def getVolume(self, className, distance):
        # the grater the distance the lower the volume
        maxDist = 600
        percent = (distance / maxDist) * 100
        amt = abs(1.0 - percent)

        # print("____volume", className, amt)
        if className == 'aim':
            return 1
        elif className == 'enemy':
            return amt
        elif className == 'friend':
            return amt

    def fadeIn(self, channel, duration):
        if mymixer.get_init():
            mymixer.Channel(channel).set_volume(1)

    def fadeOut(self, channel, duration):
        if mymixer.get_init():
            mymixer.Channel(channel).fadeout(duration)

    def checkLastDicts(self, lastDicts, className, params):
        for lastDict in lastDicts:
            if lastDict['class'] == className:

                keys = list(params.keys())

                isNew = False
                isDiff = False
                for key in keys:
                    if key not in lastDict:
                        # append params to lastDict
                        lastDict[key] = params[key]
                        isNew = True

                if isNew:
                    lastDict['silence'] = params['silence']
                    lastDict['posX'] = params['posX']
                    lastDict['posY'] = params['posY']
                    lastDict['multiplier'] = params['multiplier']
                    return True

                for key in keys:
                    if lastDict[key] != params[key]:
                        lastDict[key] = params[key]
                        isDiff = True
                        return True

                if isDiff:
                    lastDict['silence'] = params['silence']
                    lastDict['posX'] = params['posX']
                    lastDict['posY'] = params['posY']
                    lastDict['multiplier'] = params['multiplier']
                    return True

                break
        return False

    def processSound(self, entityRef, ultra):
        entity = entityRef
        className = entity['class']
        if ultra[className] is not None and entity is not None and entity['emmiter'] is not None and entity['segment'] is not None:
            params = {
                'silence': 5,
                'posX': 0,
                'posY': 0,
                'multiplier': 1,
                'stopped': False,
                'id': time.time(),
            }

            print("ultra-content-last", ultra[className])
            if ultra[className]:
                if ultra[className]['multiplier']:
                    params['multiplier'] = int(ultra[className]['multiplier'])

                if ultra[className]['x']:
                    params['posX'] = int(ultra[className]['x'])

                if ultra[className]['y']:
                    params['posY'] = int(ultra[className]['y'])

                if ultra[className]['silence']:
                    # silenceMult = 0
                    # if className == 'aim':
                    #     silenceMult = 0.5
                    params['silence'] = float(ultra[className]['silence'])

                if ultra[className]['stopped']:
                    params['stopped'] = bool(ultra[className]['stopped'])

                if ultra[className]['id']:
                    params['id'] = int(ultra[className]['id'])

                # if params['silence'] < 5:
                print("model-updated-request",
                      params['silence'], params['posX'], params['posY'], params['multiplier'])

                # update lastDicts with new params
                result = self.checkLastDicts(self.lastDicts, className, params)
                if result == False:
                    print("rejected", className, params)
                    return False
                # print("model-updated", className, params['silence'], params['posX'], params['posY'], params['multiplier'])
                # render new parametric sound segment
                t1 = time.time()
                entity['emmiter'].updatePosition(
                    [params['posX'], params['posY']])
                # base64 = entity['emmiter'].getBase64()
                # if base64 is not None:
                #     print("base64", len(base64))
                #     setUltraChanges(ultra, className, 'encoded', base64)
                # else:
                # print("base64 is None")
                # generate pygame sound with gap and volume
                soundWithGap, totalDuration = self.generateSilencedSound(
                    entity['segment'], params['silence'])
                self.playChannel(soundWithGap, entity['id'], className, self.getVolume(
                    className, params['silence']))
                t2 = time.time()

                print("time-to-play", (t2 - t1), totalDuration, className,
                      params['silence'], params['posX'], params['posY'], params['multiplier'])

                # else:
                #     # print("stopped", className, params)
                #     if params['stopped']:
                #         self.stopChannel(entity['id'], False, True)

    def setUltraChanges(self, ultra, className, key, value):
        with ultra.lock:
            ultra[className][key] = value

    def retryUltra(self, ultraTimer, retries):
        self.controlRef = False

        if ultraTimer is not None:
            ultraTimer.cancel()
            print("ultraTimer retry 1 sec")
            ultraTimer = threading.Timer(
                1, self.threadStarter, args=[retries+1, self.path])
            ultraTimer.start()
        else:
            print("ultraTimer 1s retry 1 sec")
            ultraTimer = threading.Timer(
                1, self.threadStarter, args=[retries+1, self.path])
            ultraTimer.start()

    def threadStarter(self, retries, newPath=None):

        if newPath is None:
            path = self.path
        else:
            path = newPath

        sys.path.append(path)
        data.path_prefix = path

        for entity in self.entities:
            if entity['isRunning'] == False:
                print("loading entity", entity)
                entity['emmiter'] = DynamicEmission(
                    entity['id'], entity['class'], ''+path+'/sounds/'+entity['wav']+'', [0, 0], 1, self.updateSegment)
                entity['emmiter'].startLoop()
                entity['isRunning'] = True

        if self.rootThread is not None:
            if self.rootThread.is_alive():
                self.rootThread.join()

        if self.controlRef == False:
            self.controlRef = True
        self.rootThread = threading.Thread(target=self.ultraChangeListener, daemon=True, args=[
                                           retries], name="ultraChangeListener")
        self.rootThread.start()

        return self.rootThread

    def ultraChangeListener(self, isRetry):

        global ultraTimer

        retries = isRetry

        print("ultraChangeListener-starting", retries, self.controlRef)
        while self.controlRef == True:
            print("ultraChangeListener-running", retries, self.controlRef)
            try:

                try:
                    ultra = UltraDict(shared_lock=True,
                                      recurse=True, name='very_unique_name', full_dump_size=10000*4, buffer_size=10000*2)
                except Exception as e:
                    print("waiting-for-ultra-node\n", e)
                    self.retryUltra(ultraTimer, retries)
                    break

                for entity in self.entities:
                    if entity['isRunning'] == False:
                        pass

                    if entity['class'] == 'aim':
                        self.processSound(entity, ultra)
                        # print("aim generating skipped")
                        pass

                    if entity['class'] == 'enemy':
                        # new thread for each processing
                        # self.processSound(entity, ultra)
                        pass

                    if entity['class'] == 'friend':
                        # self.processSound(entity, ultra)
                        pass

            except Exception as e:
                print("waiting-for-dependepencies\n", e)
                # try again in 1
                self.retryUltra(ultraTimer, retries)
                break

            time.sleep(1)
