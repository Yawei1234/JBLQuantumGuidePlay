"""OSC SIGNALER SERVER

Listen to game state and some signals from the game and emit sounds to the user.
"""
import io
import sys
import time
import json
import threading
from queue import Queue
from pythonosc import osc_server, udp_client
from pythonosc.dispatcher import Dispatcher
import pyttsx3
import math
import argparse
import numpy as np
import os
import data
import numpy as np
import gc
from sound import Emission, trimSilence, addSilence, concatenateSound, WhiteNoise
from tracker import distSignal
from pydub.playback import play, _play_with_simpleaudio
from pydub import AudioSegment
from pydub.playback import play
import pyaudio
from osc import oscRECEIVER, oscQUEUE



global soundpath
global client
global lastCardinal
global cardinalConfidence
global addressConfidence
global guideVoice
global cliRef

lastCardinal = ""
cardinalConfidence = 0
addressConfidence = 0
soundpath = None
client = None
cliRef = None

global trackedIDS
global lastTrackeds
global lastTrackedTime
global lastAimTime

global emissionENEMIES
global enemyEMITTER
global enemiesCOOLDOWN
global lastBeepENEMY
global lastSilenceENEMY

global emissionFRIENDS
global lastBeepFRIEND
global lastSilenceFRIEND
global friendEMITTER


global aimEmitter
global lastAIM
global lastBeepAIM
global lastSilenceAIM

global lastAddress


trackedIDS = []
lastTrackeds = []
lastTrackedTime = 0
lastAimTime = 0

enemyEMITTER = None
emissionENEMIES = []
enemiesCOOLDOWN = 0
lastBeepENEMY = 0
lastSilenceENEMY = 0


friendEMITTER= None
emissionFRIENDS = []
lastBeepFRIEND = 0
lastSilenceFRIEND = 0
lastAIM = []
lastBeepAIM = 0
lastSilenceAIM = 0
aimEmitter = None

lastAddress = ""

global SFX
SFX = {
    "AimAlerts": {
        "file": "_wzy_aim_a1_01.wav",
        "volume": 0.0
    },
    "EnemyKilled": {
        "file": "_wzy_enemydown_a0.wav",
        "volume": 0.0
    },
    "EnemyProximity": {
        "file": "beep_enemy0.wav",
        "volume": 0.0,
        "enemyReport": "off"
    },
    "EnvironmentNavigation": {
        "file": "_wzy_hurt_a0_01.wav",
        "volume": 0.0
    },
    "IncomingDamageDirection": {
        "file": "_wzy_hurt_a0_01.wav",
        "volume": 0.0
    },
    "ScreenReader": {
        "compass": "off",
        "file": "",
        "screen": "off",
        "sectors": "off",
        "speed": 5,
        "volume": 100.0
    },
    "TeamProximity": {
        "file": "beep_friend0.wav",
        "volume": 0.0
    },
    "default": {
        "file": "wzy_aim_a0.wav",
        "volume": 0.0
    },
    "lastSync": {
        "time": time.time()
    }
}

def soundUpdatePosition(emmiter, position, id, overlap=True):
    emmiter.updatePosition(position, overlap)
    return


def soundStart(emmiter, position, id, silence=0.0, autoDestroy=False, overlap=True):
    emmiter.play(overlap, autoDestroy, silence)
    return


def soundEnd(emmiter, position, id, silence=0.0, classType="enemy"):
    emmiter.setEnded(emmiter, autoDestroy=True)
    del emmiter
    global emissionENEMIES
    global emissionFRIENDS

    if classType == "enemy":
        # print("BEEP_ENEMY_soundEnd__start_emissionENEMIES = ", len(emissionENEMIES))
        emissionENEMIES = list(
            filter(lambda x: x['id'] != id, emissionENEMIES))
        # print("BEEP_ENEMY_soundEnd__end__emissionENEMIES = ", len(emissionENEMIES))

    if classType == "friend":
        emissionFRIENDS = list(
            filter(lambda x: x['id'] != id, emissionFRIENDS))
        # print("BEEP_FRIEND_soundEnd__emissionFRIENDS = ", len(emissionFRIENDS))
    gc.collect()
    return


def aimEmit(soundpath, contents, multiplier=3):

    global lastBeepAIM
    global lastSilenceAIM

    for i in range(len(contents)):
        item = contents[i]
        position = item['position']
        silence = item['silence']
        uniqueId = item['id']

        if time.time() > lastBeepAIM + lastSilenceAIM:

            soundFile = SFX['AimAlerts']['file']

            newEmitter = Emission(
                        uniqueId, ''+soundpath+'/sounds/'+soundFile+'', position, 0, 'square')

            duration = 0.08
            # print("GOT_DURATION", duration, uniqueId)

            lastBeepAIM = time.time()
            lastSilenceAIM = duration + silence

            t = threading.Thread(target=soundStart, args=[
                newEmitter, position, uniqueId, lastSilenceAIM, True, True])
            t.start()

            q = threading.Timer(lastSilenceAIM, soundEnd, args=[
                newEmitter, position, uniqueId, lastSilenceAIM, 'aim'])
            q.start()
        time.sleep(0.1)
            

        
def legacyEmmiter(uniqueId, soundpath, realId, soundposition, silence):
    if 'enemy' in realId:

        if time.time() > lastBeepENEMY + lastSilenceENEMY:

            newEmitter = Emission(
                    uniqueId, ''+soundpath+'/sounds/beep_enemy0.wav', soundposition, 0, 'square')

            duration = 0.08
            # print("GOT_DURATION", duration, uniqueId)

            lastBeepENEMY = time.time()
            lastSilenceENEMY = duration + silence

            t = threading.Thread(target=soundStart, args=[
                newEmitter, soundposition, uniqueId, lastSilenceENEMY, True, True])
            t.start()

            q = threading.Timer(lastSilenceENEMY, soundEnd, args=[
                newEmitter, soundposition, uniqueId, lastSilenceENEMY, 'enemy'])
            q.start()

    if 'friend' in realId:

        if time.time() > lastBeepAIM + lastSilenceAIM:

            newEmitter = Emission(
                    uniqueId, ''+soundpath+'/sounds/beep_friend0.wav', soundposition, 0, 'square')

            duration = 0.08
            # print("GOT_DURATION", duration, uniqueId)

            lastBeepFRIEND = time.time()
            lastSilenceFRIEND = duration + silence

            t = threading.Thread(target=soundStart, args=[
                newEmitter, soundposition, uniqueId, lastSilenceFRIEND, True, True])
            t.start()

            q = threading.Timer(lastSilenceFRIEND, soundEnd, args=[
                newEmitter, soundposition, uniqueId, lastSilenceFRIEND, 'friend'])
            q.start()

global radarStream
radarStream = None
global sliced_segments
sliced_segments = []

def radarEmitterLoop(audiofile=None, silence=False):

    global radarStream
    global soundpath
    # audiofile = SFX['EnemyProximity']['file']


    if silence == True:
        # newsound = AudioSegment.silent(duration=100, frame_rate=44100)
        # generate white noise
        noise = WhiteNoise(10000, 44100, "noise.wav")
        newsound = noise.generate()

    elif audiofile is not None:
        print("radarEmitterLoop", audiofile, silence)
        newsound = AudioSegment.from_file(''+soundpath+'/sounds/'+str(audiofile)+'')
    else:
        print("radarEmitterLoop", audiofile, silence)

    p = pyaudio.PyAudio()
    if radarStream is None:
        radarStream = p.open(format=p.get_format_from_width(newsound.sample_width),
                        channels=newsound.channels,
                        rate=newsound.frame_rate,
                        output=True)
    
        
    sliced_segments.append(newsound)

    while True:
        try:
            for slice in sliced_segments:
                print("writing slice", len(sliced_segments))
                nextSlice = slice.raw_data
                # remove from sliced_segments
                radarStream.write(nextSlice)
                play(radarStream)
                # sliced_segments.remove(slice)
        except:
            # get exception

            print("radarEmitterLoop__except")
            break
            # pass
        finally:
            # print("radarEmitterLoop__finally")
            radarStream.stop_stream()
            radarStream.close()

            p.terminate()

def radarEmit(soundpath, contents, multiplier=5):

    global lastBeepENEMY
    global lastSilenceENEMY
    global emissionENEMIES

    global lastBeepFRIEND
    global lastSilenceFRIEND
    global emissionFRIENDS

    global beepFriend
    global friendEMITTER
    global enemyEMITTER

    # print("\r -- radarEmit", len(contents))
    # print("radarEmit__emissionENEMIES = ", len(emissionENEMIES))
    # print("radarEmit__emissionFRIENDS = ", len(emissionFRIENDS))
    # # get the first five elements
    contents = contents[:5]

    # filtered = list(
    #     filter(lambda x: x['closest'] == True, contents))

    for i in range(len(contents)):

        item = contents[i]
        # if item['closest'] == True:
        box_id = item

        x = box_id['x']
        y = box_id['y']
        w = box_id['w']
        h = box_id['h']
        uniqueId = box_id['uniqueId']
        realId = box_id['id']

        # get the dist value from realId
        dist = int(realId.split("_")[0])
        silence = 1
        color = (0, 255, 0)

        silence, color = distSignal(dist)

        # silence = dist // 100
        # silence = 0.5

        soundposition = [x * multiplier, y * multiplier]

        sfxKey = "EnemyProximity"
        if 'enemy' in realId:
            sfxKey = "EnemyProximity"
            # legacyEmmiter(uniqueId, soundpath, realId, soundposition, silence, sfxKey)
            

        if 'friend' in realId:
            sfxKey = "TeamProximity"
            # legacyEmmiter(uniqueId, soundpath, realId, soundposition, silence)
            # print("GENERATE_FRIEND", realId, soundposition, silence, sfxKey, sfxKey)

        if sfxKey == "EnemyProximity":
            print("GENERATE_ENEMY", realId, soundposition, silence, SFX[sfxKey]['file'])
            radarEmitterLoop(SFX[sfxKey]['file'], False)
        
      
        time.sleep(0.1)           

                
def enemyReport(report):
    global SFX
    if SFX['EnemyProximity']['enemyReport'] == "on":
        if report == "detected":
            # soundpath = SFX['EnemyProximity']['file']
            # newEmitter = Emission(
            #     "enemyReport", ''+soundpath+'/sounds/'+soundpath+'', [0, 0], 0, 'square')
            # newEmitter.play(False, True, 0)
            # q.put("enemy detected")
            if cliRef is not None:
                cliRef.queueSay('enemy detected')
        if report == "lost":
            # soundpath = SFX['EnemyProximity']['file']
            # newEmitter = Emission(
            #     "enemyReport", ''+soundpath+'/sounds/'+soundpath+'', [0, 0], 0, 'square')
            # newEmitter.play(False, True, 0)
            # q.put("enemy lost")
            if cliRef is not None:
                cliRef.queueSay('enemy lost')
        print("EMIT_ENEMY_REPORT", report)
            

def getLastAimTime():
    global lastAimTime
    return lastAimTime

def getLastTrackedTime():
    global lastTrackedTime
    return lastTrackedTime


def setLastTrackedTime(val):
    global lastTrackedTime
    lastTrackedTime = val


def getLastTracks():
    global lastTrackeds
    return lastTrackeds


def setLastTracks(val):
    global lastTrackeds
    lastTrackeds = val


def getLastAIM():
    global lastAIM
    return lastAIM


def setLastAIM(val):
    global lastAIM
    lastAIM = val


def getEmissionENEMIES():
    global emissionENEMIES
    return emissionENEMIES


def signaler_run(soundpath):

    trackedContent = getLastTracks()
    aimContent = getLastAIM()
    delta = 0
    reseted = True
    enemyFound = False

    while True:

        # print("signaler_run_runtime", delta, len(trackedContent))

        if getLastAimTime() > 0 and time.time() - getLastAimTime() > 1:
            setLastAIM([])

        if getLastTrackedTime() > 0 and time.time() - getLastTrackedTime() > 1:
            setLastTracks([])
            setLastAIM([])
            print("signaler_run_reset", getLastTrackedTime())
            setLastTrackedTime(0)
            if enemyFound == True:
                enemyReport("lost")
            enemyFound = False
            reseted = True

        trackedContent = getLastTracks()

        aimContent = getLastAIM()
        enemiesEmiting = getEmissionENEMIES()

        delta += 1
        # print("signaler_run_runtime:", delta, len(trackedContent))

        # if len(trackedContent) > 0 and len(aimContent) > 0:
        if len(aimContent) > 0:
            # filter trackedContent by class
            # print("trackedContent", trackedContent)
            filteredENE = list(
                filter(lambda x: x['class'] == 'enemy', trackedContent))
            if len(filteredENE) > 0:
                aimEmit(soundpath, aimContent, 4)
        else:
            setLastAIM([])
            # print("aimContent", aimContent)
        # radar items are sorted by dist
        if len(trackedContent) > 0:
            # print("trackedContent\n", len(trackedContent))
            trackedContent.sort(key=lambda x: x['dist'])
            trackedContent[0]['closest'] = True
            if reseted == True:
                print("signaler_run_reseted_willfilter", trackedContent)
                # deted enemies
                filteredENEMIES = list(
                    filter(lambda x: x['class'] == 'enemy', trackedContent))
                if len(filteredENEMIES) > 0:
                    
                    if len(aimContent) < 1:
                        radarEmit(soundpath, filteredENEMIES, 3)

                    enemyFound = True
                    
                    enemyReport("detected")
                else:
                    if enemyFound == True:
                        
                        enemyReport("lost")
                    enemyFound = False

            reseted = False

            # print("signaler_run_runtime_filtered", trackedContent)
            filteredFRIENDS = list(
                filter(lambda x: x['class'] == 'friend', trackedContent))
            radarEmit(soundpath, filteredFRIENDS, 3)
        else:
            if enemyFound == True:
                # This is the code that makes the enemy disappear when it is no longer visible.
                enemyReport("lost")
                enemyFound = False
            reseted = True

global testQueue
global lastTestBeep
global lastTestSilence
global cachedSegments
global playingSound
global playback

lastTestBeep = 0
lastTestSilence = 0.2
testQueue = []
cachedSegments = []
playingSound = None
playback = None

# sound loop

def playBeep(silence=0.2, param1=0, param2=0, file='beep_aim.wav', soundpath='', segID=0):
    # AudioSegment
    global lastTestBeep
    global lastTestSilence
    global cachedSegments
    global playingSound
    global playback

    if time.time() - lastTestBeep > lastTestSilence:
        print("playBeep", silence)
        lastTestBeep = time.time()
        lastTestSilence = silence
        playingSound = cachedSegments[segID]
        if playback is not None:
            playback.stop()
        playback = _play_with_simpleaudio(playingSound)
        # play(playingSound)
    else:
        print("playBeep", silence, "silenced")

def SoundTesterLoop(soundpath):
    global testQueue
    global lastTestBeep
    global lastTestSilence
    while True:
        # print("SoundTesterLoop", len(testQueue))
        if len(testQueue) > 0:
            if time.time() - lastTestBeep > lastTestSilence:
                item = testQueue.pop(0)
                t = threading.Thread(target=playBeep, args=[
                    item['silence'], item['param'], item['volume'], item['file'], soundpath, item['segID']])
                t.start()
                # playBeep(soundpath=soundpath, silence=item['silence'], param1=item['param'], param2=item['volume'], file=item['file'])
                print("SoundTesterLoop", len(testQueue))
        time.sleep(0.01)

def testSFX(id, subitem, volume=None, newfile=None):
    global soundpath
    
    uniqueId = time.time()
    silence = 0
    position = [0, 0]
    motif = 'aim'

    print("TESTING_FX", id, subitem)

    if newfile is not None:
        print("TESTING_FX_NEWFILE", newfile)

        # if contains .wav
        if ".wav" in newfile:
            SFX[id]['file'] = newfile
        else:
            SFX[id]['file'] = ""+str(newfile)+".wav"

    file = SFX[id]['file']
    duration = 0

    cachedSegments.clear()

    sound = AudioSegment.from_file(''+soundpath+'/sounds/'+file+'')
    combined = AudioSegment.empty()
    for i in range(3):
        combined += sound

    # normalize volume
    # normalized = combined.apply_gain(-combined.max_dBFS)
    # set volume
    if volume is not None:
        volumeTreated = -50 + (volume * 50)
        SFX[id]['volume'] = volumeTreated

    print("TESTING_FX_VOLUME", SFX[id]['volume'])

    gain = combined.apply_gain(SFX[id]['volume'])
    # audio_fade_in = volumed.fade_in(500)
    cachedSegments.append(gain)
    
    playBeep(0.2, 0, 0, file, soundpath, 0)


def setCardinal(val):
    global lastCardinal
    global cardinalConfidence
    valueChanged = lastCardinal != val
    if valueChanged or lastCardinal == "":
        cardinalConfidence += 1
    else:
        cardinalConfidence = 0

    if cardinalConfidence >= 6 or lastCardinal == "":
        lastCardinal = val
        cardinalConfidence = 0
        return True
    return False

def setAddress(val):
    global lastAddress
    global addressConfidence
    valueChanged = lastAddress != val
    if valueChanged or lastAddress == "":
        addressConfidence += 1
        # print("\n_______ADDRESS_CHECK_CONFIDENCE", addressConfidence, val)
        if addressConfidence >= 5 or lastAddress == "":
            lastAddress = val
            addressConfidence = 0
            return True
    else:
        # print("\n_______ADDRESS_EQUAL", val, lastAddress)
        addressConfidence = 0
    return False

def speech_cardinal(unused_addr, args, cardinal):

    # "ScreenReader": {
    #     "compass": "off",
    #     "file": "",
    #     "screen": "off",
    #     "sectors": "off",
    #     "speed": 5,
    #     "volume": 100.0
    # },

    if SFX['ScreenReader']['compass'] == "on":
        # print("__CARDINAL_COMMING", cardinal)
        newCardCheck = setCardinal(cardinal)
        if newCardCheck == True:
            # size = q.qsize()
            # q.queue.clear()
            # q.put(cardinal)
            if cliRef is not None:
                cliRef.queueSay(cardinal)
            # print("\n_______CARDINAL_UPDATE", cardinal, size)
    else:
        print("\n_______CARDINAL_UPDATE__OFF>", cardinal)

def address(unused_addr, args, address):

    if SFX['ScreenReader']['sectors'] == "on":

        newAddressCheck = setAddress(address)
        if newAddressCheck == True:
            # clear queue
            # get queue size
            # size = q.qsize()
            # q.queue.clear()
            # q.put(''+lastCardinal+' '+address+'')
            # q.put(address)
            if cliRef is not None:
                cliRef.queueSay(address)
            # print("\n_______ADDRESS_UPDATE__NEW>", address, size)
    else:
        print("\n_______ADDRESS_UPDATE__OFF>", address)

def trackeds(unused_addr, args, trackeds):
    global lastTrackeds
    global lastTrackedTime
    lastTrackedTime = time.time()
    # lastTrackeds = json.load(trackeds)
    parsed = json.loads(trackeds)
    print("/trackeds-runtime\n", len(parsed))
    lastTrackeds = parsed
    return

def updatesfx(unused_addr, args, sfx):

    global cliRef
    # parse json
    # update sfx
    jsonSFX = json.loads(sfx)
    for key in jsonSFX:
        model = jsonSFX[key]
        if key != "default" and key != "ScreenReader":
            newvolume = model['volume']
            volumeOriginal = float(newvolume) * 0.01
            volumeTreated = -50 + (volumeOriginal * 50)
            model['volume'] = volumeTreated
        SFX[key] = model
        if key == "ScreenReader":
            # if tts_thread is not None:
            #     tts_thread.speed = 200 + (int(int(model['speed']) * 50))
            #     tts_thread.volume = float(model['volume']) * 0.01
            if cliRef is not None:
                if cliRef.threadTTS is not None:
                    cliRef.threadTTS.speed = 200 + (int(int(model['speed']) * 50))
                    cliRef.threadTTS.volume = float(model['volume']) * 0.01
    
    SFX['lastSync']['time'] = time.time()
    # print("updatesfx", json.dumps(SFX, indent=4, sort_keys=True))
    print("updatesfx-lastSync", SFX['lastSync']['time'])
    return

def changesfx(unused_addr, args, sfx):
    # volume comes 1-5
    # min 0
    # max 1
    # 1 = 0
    # 5 = 1
    id, subitem, newfile = sfx.split("-")
    
    print("changesfx", id, subitem, newfile)
    testSFX(id, subitem, None, newfile)
    return

def changesfxvolume(unused_addr, args, volume):
    # volume comes 1-5
    # min 0
    # max 1
    # 1 = 0
    # 5 = 1
    id, subitem, newvolume = volume.split("-")
    finalVolume = float(newvolume) * 0.01
    testSFX(id, subitem, finalVolume)
    print("changesfxvolume", id, subitem, finalVolume)
    return

def changevolume(unused_addr, args, volume):
    # volume comes 1-5
    # min 0
    # max 1
    # 1 = 0
    # 5 = 1
    id, param, newvolume = volume.split("-")
    finalVolume = float(newvolume) * 0.01
    # tts_thread.volume = finalVolume
    if cliRef is not None:
        cliRef.threadTTS.volume = finalVolume
    # saynow("unused_addr", "args", "volume changed to "+str(int(finalVolume)))
    return

def changespeed(unused_addr, args, speed):
    # speed comes 1-5
    # min 200
    # max 400
    # 1 = 200
    # 5 = 500
    if cliRef is not None:
        cliRef.threadTTS.speed = 200 + (int(speed) * 50)
    # tts_thread.speed = 200 + (int(speed) * 50)
    # saynow("unused_addr", "args", "speed changed to "+str(speed))
    return

def saynow(unused_addr, args, say):
    # pass
    # clear queue
    # get queue size
    # global cliRef
    if cliRef is not None:
        cliRef.queueSay(''+str(say)+'')
        # cliRef.queueTTS.put(say)
        return
    # size = q.qsize()
    # q.queue.clear()
    # if tts_thread is not None and tts_thread.is_alive():
    #     tts_thread.reset()
    #     print("RESET tts_thread.is_alive()", tts_thread.is_alive())
    
    
    # q.put(say)
    return

def say(unused_addr, args, say):
    # pass
    # q.put(say)
    # global cliRef
    if cliRef is not None:
        cliRef.queueSay(''+str(say)+'')
        # cliRef.queueTTS.put(say)
    # return

def aim(unused_addr, args, aim):
    global lastAIM
    global lastAimTime
    lastAimTime = time.time()
    # print("aim_incoming", aim)
    lastAIM = json.loads(aim)
    return

def exit(unused_addr, args, exit):
    print("exit", exit)
    os._exit(0)
    return

def keepAliveLoop(qOSC, port):
    global SFX
    keepAlive = time.time()
    print("messenger-keepAliveLoop", keepAlive)
    lastSync = SFX['lastSync']['time']
    while True:
        if qOSC is not None:
            # print("keepAlive_1", keepAlive)
            lastSync = SFX['lastSync']['time']
            lastSyncCount = time.time() - lastSync
            # print("keepAliveLoop_CHECK_LAST_SYNC", lastSyncCount)
            # client.send_message("/keepalive", time.time())
            qOSC.put(('/keepalive', time.time()))
            if lastSync == -1 or lastSyncCount > 5:

                # client.send_message("/asksync", time.time())
                qOSC.put(('/asksync', time.time()))
            if lastSyncCount > 30:
                print("guideplay-not-found-quitting", lastSyncCount)
                # auto kill
                # os._exit(0)
                if cliRef is not None:
                    cliRef.do_quit("now")
                    os._exit(0)
                else:
                    os._exit(0)

            time.sleep(1)
        else:
            print("keepAlive_0", keepAlive, "client is None", port)
            time.sleep(10)
            # break
    return

def mainWorker(args, cliREF):
    
    global soundpath
    global client
    global cliRef

    if cliREF is not None:
        cliRef = cliREF

    cancellation_event = threading.Event()

    print("STARTING_SERVER", args['ip'], args['port'], args['port_app'])

    if args['path']:
        soundpath = args['path']
        print("sound_path____", soundpath)
        sys.path.append(soundpath)
        data.path_prefix = soundpath

        # threading.Thread(target=signaler_run, args=(
        #     soundpath, ), daemon=True, name="signaler_legacy").start()
        
        # Spawn worker threads
        osc_queue: Queue[tuple[bool, int, int]] = Queue()
        osc = oscQUEUE(cancellation_event, osc_queue, args['ip'], args['port_app'])
        osc_thread = threading.Thread(target=osc.run, name="osc_thread")

        # start worker threads
        osc_thread.start()

        threading.Thread(target=keepAliveLoop, args=(osc_queue, args['port_app']), name="messageWorker_keep").start()

        osc_receiver = oscRECEIVER(cancellation_event, args['ip'], args['port'])

        def debugger(unused_addr, args, value):
            print("/test-trackeds", value)
            return

        osc_receiver.mapDispatcher("/trackeds", trackeds, "Trackeds")
        osc_receiver.mapDispatcher("/test-trackeds", debugger, "Trackeds")
        osc_receiver.mapDispatcher("/address", address, "Address")
        osc_receiver.mapDispatcher("/aim", aim, "Aim")
        osc_receiver.mapDispatcher("/say", say, "Say")
        # osc_receiver.mapDispatcher("/saynow", saynow, "Saynow")
        osc_receiver.mapDispatcher("/changespeed", changespeed, "Changespeed")
        osc_receiver.mapDispatcher("/changevolume", changevolume, "ChangeVolume")
        osc_receiver.mapDispatcher("/changesfxvolume", changesfxvolume, "ChangeSFXVolume")
        osc_receiver.mapDispatcher("/changesfx", changesfx, "ChangeSFX")
        osc_receiver.mapDispatcher("/updatesfx", updatesfx, "UpdateSFX")
        osc_receiver.mapDispatcher("/cardinal", speech_cardinal, "Cardinal")
        osc_receiver.mapDispatcher("/exit", exit, "Exit")

        osc_receiver_thread = threading.Thread(target=osc_receiver.run, name="osc_receiver_thread")
        osc_receiver_thread.start()
        
        # threading.Thread(target=SoundTesterLoop, args=(soundpath,), daemon=True).start()
