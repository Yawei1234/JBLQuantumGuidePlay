import threading
import time
import pyttsx3


class TTSThread(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue
        self.daemon = True
        self.volume = 0.5
        self.speed = 220
        self.tts_engine = None
        self.time = time.time()
        self.start()

    def onStart(self, name):
        print ('speech-starting', name)
        return
    
    def onEnd(self, name, completed):
        # print ('finishing', name, completed)
        return
        # if completed == True:
        #     self.engine.endLoop()
        #     self.engine.startLoop(False)
        #     self.engine = self.setup()

    def onWord(self, name, location, length):
        # print ('on word', name, location, length)
        
        return None
        if name is None:
            return
        if location > 10:
            print("onWord_STOP", location)
            self.tts_engine.stop()

    def setup(self):

        voices = self.tts_engine.getProperty('voices')
        for voice in voices:
            
            if voice.name == 'Microsoft Zira Desktop - English (United States)':
                self.tts_engine.setProperty('voice', voice.id)
                break
            # if voice name contains English
            if 'English' in voice.name:
                # if voice name contains Zira
                if 'Zira' in voice.name:
                    self.tts_engine.setProperty('voice', voice.id)
                    break
                # if voice name contains Hazel
                if 'Hazel' in voice.name:
                    self.tts_engine.setProperty('voice', voice.id)
                    break
                self.tts_engine.setProperty('voice', voice.id)

        # print("voices", voices)
        # tts_engine.setProperty('voice', voices[1].id)
        self.tts_engine.setProperty('volume', self.volume)
        # print("SPEED SET", self.speed)
        self.tts_engine.setProperty("rate", self.speed)
        
        return self.tts_engine

    def reset(self):
        print("RESET TIME", self.time)
        # clear queue
        # get queue size
        self.queue.queue.clear()
        size = self.queue.qsize()
        print("RESET queue size", size)

        if self.tts_engine is not None:
            self.tts_engine.stop()
            self.tts_engine.endLoop()
            self.tts_engine.startLoop(False)
            self.tts_engine = self.setup()

    def kill(self):
        # kill tts_engine
        self.reset()

    
    def run(self):
        self.tts_engine = pyttsx3.init()
        self.tts_engine.startLoop(False)
        self.tts_engine = self.setup()
        self.tts_engine.connect('started-utterance', self.onStart)
        self.tts_engine.connect('finished-utterance', self.onEnd)
        self.tts_engine.connect('started-word', self.onWord)

        t_running = True
        while t_running:
            if self.queue.empty():
                self.tts_engine.iterate()
            else:
                # get the last item on queue
                size = self.queue.qsize()
                # print("queue size", size)
                data = self.queue.get()
                self.queue.empty()
                size = self.queue.qsize()
                # print("queue size cleared", size)
                # data = self.queue.get()
                if data == "exit":
                    t_running = False
                else:
                    # clear self.tts_engine queue

                    self.tts_engine.endLoop()
                    self.tts_engine.startLoop(False)
                    self.tts_engine = self.setup()
                    self.tts_engine.say(data)
        self.tts_engine.endLoop()