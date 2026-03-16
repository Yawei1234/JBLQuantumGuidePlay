import sys
import argparse
import cmd
import json
from ttsService import TTSThread
from queue import Queue
from threading import Timer
# from soundMixer import SoundMixer
from message_server import mainWorker as messageWorker
# from signalerService import SignalerThread
import data
import time

class GuidePlayCLI(cmd.Cmd):

    def __init__(self):
        super().__init__(argDict)
        self.args = argDict
        self.soundpath = self.args['path']+"/sounds/"
        self.prompt = '> '
        self.intro  = ""
        self.lastSay = ""
        self.lastSayResetTimer = None
        self.queueTTS = Queue()
        self.threadTTS = TTSThread(self.queueTTS)  # note: thread is auto-starting
        self.queueTTS.put("")
        self.queueSignaler = Queue()
        # self.threadSignaler = SignalerThread(self.queueSignaler, self.soundpath)  # note: thread is auto-starting
        # self.threadMixer = SoundMixer(self.args['path'])
        self.threadMixerRef = None
        self.mixerNeeded = False
        self.threadMixerRetries = 0
        self.detections = []
        self.messageWorkerON = False
        self.messageWorkerStatus = None
        self.livenessCheck = -1
        self.livenessTimer = None
        self.isQuitting = False

        print("app_args____", self.args)
        sys.path.append(self.args['path'])
        data.path_prefix = self.args['path']

        self.path = self.args['path']

    def resetLastSay(self):
        self.lastSay = ""

    def checkLiveness(self):
        if self.livenessCheck > 0 and time.time() - self.livenessCheck > 10:
            print("liveness-check-failed")
            self.livenessCheck = -1
            self.messageWorkerON = False
            self.messageWorkerStatus = None
            # self.startMessageWorker()
        # else:
        #     print("liveness-check-ok")
        self.livenessTimer = Timer(5, self.checkLiveness)
        self.livenessTimer.start()

    def startMessageWorker(self):
        if self.isQuitting == True:
            if self.livenessTimer is not None:
                self.livenessTimer.cancel()
            return
        if self.messageWorkerON:
            print("message-worker-already-started")
            self.livenessCheck = time.time()
            return
        self.messageWorkerStatus = messageWorker(self.args, self)
        self.messageWorkerON = True
        self.livenessCheck = time.time()
        self.livenessTimer = Timer(5, self.checkLiveness)
        self.livenessTimer.start()

    def startMixer(self):
        self.mixerNeeded = True
        self.threadMixer.start()
        self.threadMixerRef = self.threadMixer.threadStarter(self.threadMixerRetries, self.path)

    def stopMixer(self):
        self.mixerNeeded = False
        self.threadMixerRetries = 0
        self.threadMixer.stop()

    def removeDetection(self, uniqueId):
        self.detections = list(filter(lambda x: x['uniqueId'] != uniqueId, self.detections))
        print("detection-removed>>", uniqueId, len(self.detections))

    def queueSay(self, text, reset = False):
        if reset:
            self.queueTTS.queue.clear()
            if self.threadTTS is not None and self.threadTTS.is_alive():
                self.threadTTS.reset()
                time.sleep(0.4)
        self.queueTTS.put(text)

    def do_startMessenger(self, line):
        if self.messageWorkerStatus is not None:
            self.messageWorkerStatus.stop()
        self.startMessageWorker()
    
    def do_getMixer(self, line):
        print(self.threadMixer)

    def do_stopMixer(self, line):
        self.stopMixer()
        print("mixer-stopped")

    def do_startMixer(self, line):
        self.startMixer()
        print("mixer-started")

    def do_say(self, line):
        """Say something, with a voice."""
        # replace - with space 
        line = line.replace("-", " ")
        print("TODO: say", line)
        if self.lastSay == line:
            print("already-said")
            return
        self.queueTTS.put(line)
        # time to reset
        self.lastSay = line
        if self.lastSayResetTimer is not None:
            self.lastSayResetTimer.cancel()
        self.lastSayResetTimer = Timer(3, self.resetLastSay)

    
    def do_play(self, line):
        print("TODO: play sound", line)

    # Your CLI commands and functionality will go here
    def do_getArgs(self, line):
        print(self.args)

    def do_detections(self, line):
        # reset detections
        # parse json
        try:
            model = json.loads(line)
            self.detections = model
            print("detections>>", len(self.detections))
            # print(json.dumps(self.detections, indent=4))
        except:
            print("ERROR: could not parse detections")

    def do_detection(self, line):
        # append detection
        # parse json
        try:
            model = json.loads(line)
            self.detections.append(model[0])

            x = str(model[0]['x'])
            y = str(model[0]['y'])
            w = str(model[0]['w'])
            h = str(model[0]['h'])
            dist = str(model[0]['dist'])
            angle = str(model[0]['angle'])
            classType = str(model[0]['class'])
            uniqueId = str(model[0]['uniqueId'])
            index = str(model[0]['index'])

            strData = 'det:'+x+'_'+y+'_'+w+'_'+h+'_'+dist+'_'+angle+'_'+classType+'_'+uniqueId+'_'+index+''
            self.queueSignaler.put(strData)
            print("detection>>", len(self.detections))
            # print(json.dumps(self.detections, indent=4))1
        except:
            print("ERROR: could not parse detection")

    def do_getDetections(self, line):
        print(json.dumps(self.detections, indent=4))
    

    def do_appendArgs(self, line):
        # append to the args
        key = line.split(":")[0]
        value = line.split(":")[1]
        self.args.update({key: value})

    def do_ping(self, line):
        print("pong")

    def do_quit(self, line):
        """Exit the CLI."""
        print("bye")
        self.isQuitting = True
        self.resetLastSay()
        # put empty string to clear queue
        self.queueTTS.put("")
        # destroy tts
        self.threadTTS.kill()

        if self.messageWorkerStatus is not None:
            self.messageWorkerStatus.stop()
        if self.livenessTimer is not None:
            self.livenessTimer.cancel()
        return True
    
    def preloop(self):
        # Add custom initialization here
        print("pre-loop")

    def postloop(self):
        # Add custom cleanup or finalization here
        print("post-loop")
    
    def postcmd(self, stop, line):
        # print("input-received:\n", line)  # Add an empty line for better readability
        return stop
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip",
                        default="127.0.0.1", help="The ip to listen on")
    parser.add_argument("--port",
                        type=int, default=5005, help="The port to listen on")
    parser.add_argument("--port_app",
                        type=int, default=5006, help="The port emit")
    parser.add_argument("--path", default="../app/UI", help="The path to the app")
    
    args = parser.parse_args()

    print("DEBUG_SERVER", args.path, args.port_app, args.port, args.ip, flush=True)
    argDict = vars(args)

    GuidePlayCLI().cmdloop(argDict)


    # [{"id": "1_2_3_4", "uniqueId": "id_unico-1", "w": 50, "h": 50, "x": 0, "y": 0, "angle": 0, "class": "enemy", "closest": false, "index": -1, "dist": 50}]