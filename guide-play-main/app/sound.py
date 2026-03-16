from Soundstage import Soundstage
from Speakers import BasicSpeaker, AmbisonicSpeakers, HRTFSpeaker, Track
import numpy as np
from threading import Timer, Thread
import gc
size = np.array([1000, 1000])
rootStage = Soundstage(size)


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


wave = Generate(440, 0.09, 44100, 10000, "square")


class Emission:
    def __init__(self, _id, _file, _position, _volume, _wave_type):
        self.id = _id
        self.track = Track(_file)
        self.duration = self.track.duration
        self.position = _position
        self.isPlaying = False

        self.speaker = HRTFSpeaker(
            np.array(self.position), self.track, self.id)
        rootStage.add_speaker(self.speaker)

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
        # print("BEEP_ENDED", self.id)
        self.isPlaying = False
        if autoDestroy:
            # print("BEEP_ENDED ---DESTROYING", self.id)
            self.autoDestroy()

    def autoDestroy(self):
        # print("AUTO_DESTROY", self.id)
        rootStage.remove_speaker(self.id)
        self.speaker = None
        self.track = None
        self.position = None
        self.id = None
        # gc.collect()

    def play(self, overlap=True, autoDestroy=False, silence=0.0):
        if self.isPlaying and overlap == False:
            print("BEEP_ALREADY_PLAYING")
            return
        # play and get the callback
        if overlap == False:
            self.isPlaying = True
            rootStage.play(callback=lambda x: self.setEnded(x))
            # print("BEEP_STARTED")
        else:
            rootStage.play(
                op="overlay", callback=lambda x: self.setEnded(x, autoDestroy))
            # print("BEEP_OVERLAY_STARTED")

        if autoDestroy:
            # auto destroy after silence
            t = Timer(silence, self.autoDestroy)
            t.start()

    def test(self):
        print('Hello, my name is ' + self.name + '')
