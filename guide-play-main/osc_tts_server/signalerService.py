import threading
import time
import gc
from tracker import distSignal
from sound import Emission, trimSilence, addSilence, concatenateSound, WhiteNoise


class SignalerThread(threading.Thread):
    def __init__(self, queue, soundpath="osc_server/sounds/"):
        threading.Thread.__init__(self)
        self.queue = queue
        self.soundpath = soundpath
        self.daemon = True
        self.detections = []
        self.trackedContent = []
        self.delta = 0
        self.time = time.time()
        self.runner = None
        self.start()
        self.start_sig_runner()
        self.SFX = {
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

    def getTrackFromDetections(self):
        modelDetections = []
        for i in range(len(self.detections)):
            modelDet = {}
            item = self.detections[i].split("_")

            modelDet['x'] = int(item[0])
            modelDet['y'] = int(item[1])
            modelDet['w'] = int(item[2])
            modelDet['h'] = int(item[3])
            modelDet['dist'] = int(item[4])
            modelDet['angle'] = int(item[5])
            modelDet['class'] = item[6]
            modelDet['closest'] = False
            modelDet['index'] = i
            modelDet['frameId'] = time.time().__round__()

            modelDetections.append(modelDet)
        self.detections = []
        return modelDetections
    
    def enemyReport(self, status):
        print("enemyReport", status)

    def soundStart(self, emmiter, position, id, silence=0.0, autoDestroy=False, overlap=True):
        emmiter.play(overlap, autoDestroy, silence)
        return

    def soundEnd(self, emmiter, position, id, silence=0.0, classType="enemy"):
        emmiter.setEnded(emmiter, autoDestroy=True)
        print("soundEnd", id, classType)
        print("soundEnd-trackeds", self.trackedContent)
        # remove from trackedContent
        self.trackedContent = list(
            filter(lambda x: x['frameId'] != id, self.trackedContent))
    
    def radarSoundEmitter(self, index, uniqueId, classType, soundposition, silence, file):


        newEmitter = Emission(
                uniqueId, ''+self.soundpath+''+file+'', soundposition, 0, 'square')

        duration = 0.08
        lastSilenceENEMY = duration + silence

        tS = threading.Thread(target=self.soundStart, args=[
            newEmitter, soundposition, uniqueId, lastSilenceENEMY, True, True])
        tS.start()

        tE = threading.Timer(lastSilenceENEMY, self.soundEnd, args=[
            newEmitter, soundposition, uniqueId, lastSilenceENEMY, classType])
        tE.start()
    
    def radarEmit(self, contents, multiplier=5):

        print("radarEmit:frame", len(contents))

        
        contents = contents[:5]

        for i in range(len(contents)):

            # if item['closest'] == True:
            box_id = contents[i]

            x = box_id['x']
            y = box_id['y']
            w = box_id['w']
            h = box_id['h']
            uniqueId = box_id['frameId']
            index = box_id['index']
            dist = box_id['dist']
            classType = box_id['class']
            angle = box_id['angle']
            silence, color = distSignal(dist)

            soundposition = [x * multiplier, y * multiplier]

            sfxKey = "default"

            if 'enemy' in box_id['class']:
                sfxKey = "EnemyProximity"

            if 'friend' in box_id['class']:
                sfxKey = "TeamProximity"

            if sfxKey == "EnemyProximity":
                # print("GENERATE_ENEMY", index, soundposition, silence, self.SFX[sfxKey]['file'])
                # await sound emitter
                
                self.radarSoundEmitter(index, uniqueId, classType, soundposition, silence, self.SFX[sfxKey]['file'])
            
            # time.sleep(0.1)

        print("radarEmit:done")
    def signaler_run(self, soundpath):

        self.trackedContent = self.getTrackFromDetections()
        delta = 0
        reseted = True
        enemyFound = False

        while True:

            self.trackedContent = self.getTrackFromDetections()
            delta += 1

            # print("signaler_run", delta, len(self.trackedContent))

            if len(self.trackedContent) > 0:
                print("signaler_run_trackedContent\n", len(self.trackedContent), "\n")
                self.trackedContent.sort(key=lambda x: x['dist'])
                self.trackedContent[0]['closest'] = True
        
                # deted enemies
                filteredENEMIES = list(
                    filter(lambda x: x['class'] == 'enemy', self.trackedContent))
                if len(filteredENEMIES) > 0:
                    if enemyFound == False:
                        self.enemyReport("detected")
                    enemyFound = True

                    self.radarEmit(filteredENEMIES, 3)
                    
                else:
                    if enemyFound == True:
                        self.enemyReport("lost")
                    enemyFound = False


                # deted friends
                filteredFRIENDS = list(
                    filter(lambda x: x['class'] == 'friend', self.trackedContent))
                if len(filteredFRIENDS) > 0:
                    self.radarEmit(filteredFRIENDS, 3)

            else:
                if enemyFound == True:
                    # This is the code that makes the enemy disappear when it is no longer visible.
                    self.enemyReport("lost")
                    enemyFound = False
                reseted = True
            time.sleep(0.1)

    def start_sig_runner(self):
        if self.runner is None:
            self.runner = threading.Thread(target=self.signaler_run, args=(
                self.soundpath, ), daemon=True).start()
        elif not self.runner.is_alive():
            self.runner = threading.Thread(target=self.signaler_run, args=(
                self.soundpath, ), daemon=True).start()
    def run(self):
        while True:
            self.delta += 1
            time.sleep(0.1)
            self.fps = self.delta / (time.time() - self.time)
            print("signalerService frame:", self.delta, "fps:", self.fps)
            # print("signalerService", self.queue)
            sig = self.queue.get()
            # print("signalerService", sig)
            if sig == "stop":
                # print("signalerService", sig)
                self.queue.task_done()
                break
            else:
                print("signalerService sig:", sig)
            if "det:" in sig:
                self.detections.append(sig.split("det:")[1])
                self.queue.task_done()
            # print("signalerService", det)
            # self.queue.task_done()