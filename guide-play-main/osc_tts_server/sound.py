from Soundstage import Soundstage
from Speakers import BasicSpeaker, AmbisonicSpeakers, HRTFSpeaker, Track
import base64
import numpy as np
from threading import Timer, Thread
from pydub import AudioSegment
import gc
import time
import pydub
size = np.array([500, 500])
rootStage = Soundstage(size)


class DynamicEmission:
    def __init__(self, _id, _className, _file, _position, _volume, _callback=None):
        self.id = _id
        self.className = _className
        self.trackFile = _file
        self.lastTrackFile = _file
        self.track = Track(self.trackFile)
        self.position = _position
        self.lastPosition = None
        self.isPlaying = False
        self.volume = _volume
        self.isRunning = False
        self.speaker = HRTFSpeaker(
            np.array(self.position), self.track, self.id)
        rootStage.add_speaker(self.speaker)
        self.callback = _callback
        self.thread = None

    def __getitem__(self, item):
        return getattr(self, item)
    
    def getBase64(self):
        audio_data = base64.b64encode(rootStage.getAudio(self.id).raw_data)
        if not isinstance(audio_data, str):
            audio_data = audio_data.decode('ascii')
        data_url = 'data:audio/wav;base64,' + audio_data
        return data_url
    
    def startLoop(self):
        self.isRunning = True
        if self.thread is None:
            self.thread = Thread(target=self.trackUpdater, daemon=True, name="DynamicEmissionThread"+str(self.id)+"_"+self.className+"")
            self.thread.start()
        else:
            if self.thread.is_alive():
                print("THREAD_ALREADY_RUNNING")
            else:
                self.thread = Thread(target=self.trackUpdater, daemon=True, name="DynamicEmissionThread"+str(self.id)+"_"+self.className+"")
                self.thread.start()

    def stopLoop(self):
        self.isRunning = False
        if self.thread is not None:
            if self.thread.is_alive():
                self.thread.join()
                self.thread = None
            else:
                self.thread = None

    def updatePosition(self, _position):
        if self.lastPosition != _position:
            self.position = _position
            self.speaker.translate(np.array(self.position))
            rootStage.update_speaker(self.speaker, self.id)
            
            self.sendCallback('POSITION_UPDATED_1')
            

    def updateTrack(self, _track):
        self.track = Track(_track)
        self.speaker = HRTFSpeaker(
            np.array(self.position), self.track, self.id)
        rootStage.update_speaker(self.speaker, self.id)

    def updateTrackFile(self, _trackFile):
        self.trackFile = _trackFile


    def getAudio(self):
        # print("GETTING_AUDIO", self.id)
        return rootStage.getAudio(self.id)
    
    def sendCallback(self, motif):
        if self.callback is not None:
            seg = self.getAudio()
            if seg is not None:
                # print("SENDING_CALLBACK", self.className, motif, seg)
                self.callback(seg, self.id, self.isRunning, motif)

    def trackUpdater(self):
        while self.isRunning:
            t1 = time.time()
            updated = False
            if self.lastPosition != self.position:
                self.lastPosition = self.position
                
                self.sendCallback('POSITION_UPDATED_0')
                updated = True
                
            if self.lastTrackFile != self.trackFile:
                self.lastTrackFile = self.trackFile
                
                self.sendCallback('TRACK_UPDATED_0')
                updated = True
            t2 = time.time()
            if updated:
                print("\nTRACK_UPDATER", t2-t1, self.className)
            # time.sleep(0.01)
        

class Emission:
    def __init__(self, _id, _file, _position, _volume, _wave_type):
        self.id = _id
        self.track = Track(_file)
        self.position = _position
        self.isPlaying = False
        self.volume = _volume

        self.speaker = HRTFSpeaker(
            np.array(self.position), self.track, self.id)
        rootStage.add_speaker(self.speaker)

        self.playback = None

    def __getitem__(self, item):
        return getattr(self, item)

    def updatePosition(self, _position, _overlap=True):
        self.position = _position
        self.speaker.translate(np.array(self.position))
        rootStage.update_speaker(self.speaker, self.id)
        self.play(_overlap)

    def updateTrack(self, _track):
        self.track = Track(_track)
        self.speaker = HRTFSpeaker(np.array(self.position), self.track)
        rootStage.update_speaker(self.speaker, self.id)

    def setEnded(self, x, autoDestroy=False):
        # rootStage.remove_speaker(self.speaker)
        # self.speaker = None
        print("BEEP_ENDED", self.id)
        if self.playback is not None:
            self.playback.stop()
        self.isPlaying = False
        if autoDestroy:
            print("BEEP_ENDED ---DESTROYING", self.id)
            self.autoDestroy()

    def autoDestroy(self):
        print("AUTO_DESTROY", self.id)
        rootStage.remove_speaker(self.id)
        self.speaker = None
        self.track = None
        self.position = None
        self.id = None
        
    
    def play(self, overlap=True, autoDestroy=False, silence=0.0):
        if self.isPlaying and overlap == False:
            print("BEEP_ALREADY_PLAYING")
            return
        # play and get the callback
        if overlap == False:
            self.isPlaying = True,
            self.playback = rootStage.play(callback=lambda x: self.setEnded(x), volume=self.volume, simpleaudio=True)
            # print("BEEP_STARTED")
        else:
            self.playback = rootStage.play(
                op="overlay", callback=lambda x: self.setEnded(x, autoDestroy), volume=self.volume, simpleaudio=True)
            # print("BEEP_OVERLAY_STARTED")

        if autoDestroy:
            # auto destroy after silence
            t = Timer(silence, self.autoDestroy)
            t.start()
        gc.collect()

    def test(self):
        print('Hello, my name is ' + self.name + '')


class WhiteNoise:
    def __init__(self, samples, samplerate, filename):
        self.samples = samples
        self.samplerate = samplerate
        self.filename = filename


    def generate(self):
        x = []
        l = []

        x.append(np.random.random(size = self.samples))

        for i in x:
            for j in i:
                l.append(j)
        l = np.array(l)
        
        segmentReady = AudioSegment(l.tobytes(), frame_rate=self.samplerate, channels=2, sample_width=2)
        # wavio.write(self.filename, l, self.samplerate, sampwidth=2)
        # generate segment from array
        return segmentReady


def detectLeadingSilence(sound, silence_threshold=-100.0, chunk_size=10):
    '''
    sound is a pydub.AudioSegment
    silence_threshold in dB
    chunk_size in ms

    iterate over chunks until you find the first one with sound
    '''
    trim_ms = 0  # ms

    assert chunk_size > 0  # to avoid infinite loop
    while sound[trim_ms:trim_ms+chunk_size].dBFS < silence_threshold and trim_ms < len(sound):
        trim_ms += chunk_size

    return trim_ms

def trimSilence(sound):
    start_trim = detectLeadingSilence(sound)
    end_trim = detectLeadingSilence(sound.reverse())

    duration = len(sound)
    trimmed_sound = sound[start_trim:duration-end_trim]

    trimmedDuration = len(trimmed_sound)

    return trimmed_sound, trimmedDuration

def addSilence(sound, duration):
    # sound = AudioSegment.from_wav(input_wav_file)
    silence = AudioSegment.silent(duration=duration)
    combined = sound + silence
    return combined

def setGain(sound, gain):
    return sound.apply_gain(gain)

def concatenateSound(sound, times):
    combined_segment = sound
    for i in range(times):
        combined_segment += sound
    return combined_segment

def segToNP(asg):
    # asg = pydub.AudioSegment.from_file(file_name)
    dtype = getattr(np, "int{:d}".format(asg.sample_width * 8))  # Or could create a mapping: {1: np.int8, 2: np.int16, 4: np.int32, 8: np.int64}
    arr = np.ndarray((int(asg.frame_count()), asg.channels), buffer=asg.raw_data, dtype=dtype)
    # print("\n", asg.frame_rate, arr.shape, arr.dtype, arr.size, len(asg.raw_data), len(asg.get_array_of_samples()))  # @TODO: Comment this line!!!
    return arr, asg.frame_rate

def TestSound():
    time = 2.0
    frequency = 440

    # Generate time of samples between 0 and two seconds
    samples = np.arange(44100 * time) / 44100.0
    # Recall that a sinusoidal wave of frequency f has formula w(t) = A*sin(2*pi*f*t)
    wave = 10000 * np.sin(2 * np.pi * frequency * samples)
    # Convert it to wav format (16 bits)
    wav_wave = np.array(wave, dtype=np.int16)

    return wav_wave

def Generate(frequency, duration, sr, amplitude, wave_type):
    """
    Generate a sine wave of a given frequency, duration, and amplitude.
    """
    # t = np.linspace(0, duration, duration * sr)
    t = np.arange(sr * duration) / sr
    wav_wave = np.zeros(int(sr * duration))
    if wave_type == "sine":
        wav_wave = amplitude * np.sin(2 * np.pi * frequency * t)
    elif wave_type == "square":
        wav_wave = amplitude * np.sign(np.sin(2 * np.pi * frequency * t))
    elif wave_type == "sawtooth":
        wav_wave = amplitude * \
            (2 * (frequency * t - np.floor(1/2 + frequency * t)))
    elif wave_type == "triangle":
        wav_wave = amplitude * \
            np.abs(2 * (frequency * t - np.floor(1/2 + frequency * t))) - 1

    return np.array(wav_wave, dtype=np.int16)


# wave = Generate(440, 0.09, 44100, 10000, "square")

