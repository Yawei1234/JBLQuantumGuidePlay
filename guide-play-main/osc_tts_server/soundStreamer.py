import pyaudio
import numpy as np
import pylab
import time
import sys
import matplotlib.pyplot as plt
from pynput.keyboard import Key, Listener
import threading
from pydub import AudioSegment
from pydub.playback import play
from UltraDict import UltraDict

RATE = 44100
CHUNK = int(RATE/10)  # RATE / number of updates per second

global ultra

ultra = UltraDict({1: 1}, ownerId='UI', shared_lock=True,
                  recurse=True, name='very_unique_name')
ultra['aim'] = {'silence': 0, 'x': 0, 'y': 0, 'dist': 0, 'multiplier': 1}
ultra['enemy'] = {'silence': 0.2, 'x': -25, 'y': 0, 'dist': 0, 'multiplier': 1}
print(ultra)


testPath = '../app'


global stream


def soundplot(stream):

    t1 = time.time()
    # use np.frombuffer if you face error at this line

    data = np.frombuffer(stream.read(CHUNK), dtype=np.int16)
    # data = np.fromstring(stream.read(CHUNK), dtype=np.int16)
    # print(data)


def seg_to_nparray(asg):
    # asg = pydub.AudioSegment.from_file(file_name)
    # Or could create a mapping: {1: np.int8, 2: np.int16, 4: np.int32, 8: np.int64}
    dtype = getattr(np, "int{:d}".format(asg.sample_width * 8))
    arr = np.ndarray((int(asg.frame_count()), asg.channels),
                     buffer=asg.raw_data, dtype=dtype)
    print("\n", asg.frame_rate, arr.shape, arr.dtype, arr.size, len(
        asg.raw_data), len(asg.get_array_of_samples()))  # @TODO: Comment this line!!!
    return arr, asg.frame_rate


def playWaveFile(filename='beep_enemy0_trimmed_5times.wav'):
    soundSeg = AudioSegment.from_file(''+testPath+'/sounds/'+filename+'')
    return seg_to_nparray(soundSeg)
    # play(song)


def generateSignal():
    # generate signal
    t = np.linspace(0, 1, RATE)
    f = 440
    signal = np.sin(2 * np.pi * f * t)
    return signal


def generateSquareWave():
    # generate signal
    t = np.linspace(0, 1, RATE)
    f = 440
    signal = np.sin(2 * np.pi * f * t)
    return signal


def generatSilence(duration):
    signal = np.zeros(int(RATE*duration))
    return signal

# overlay signal to the stream


def overlaySignal(signal, stream):
    stream.write(signal.astype(np.float16).tobytes())


def overlayWaveFile(signal, stream):
    stream.write(signal.tobytes())

# on key press event
# def onKeyPress(event):
#     global stream


def on_release(key):
    pass
    # print('{0} pressed'.format(
    #     key))


def on_press(key):
    # print("rls",key)
    splited = str(key).split("'")
    if len(splited) > 1:
        keyStr = splited[1]
        # print(keyStr)
        if keyStr == 'q':
            print('quitting')
            if stream.is_active():
                stream.stop_stream()
                stream.close()
                p.terminate()
            sys.exit(0)
        elif keyStr == 'p':
            signal = generateSignal()
            overlaySignal(signal, stream)
        elif keyStr == 's':
            signal = generatSilence(1)
            overlaySignal(signal, stream)
        elif keyStr == 'w':
            signal = playWaveFile()
            overlayWaveFile(signal[0], stream)
            print(ultra.name)
        elif keyStr == 'e':
            signal = playWaveFile('beep_aim.wav')
            overlayWaveFile(signal[0], stream)
            print(ultra.name)
    else:
        print(key)
        if key == Key.up:
            ultra['aim']['silence'] += 1
            print(ultra['aim']['silence'])
            print(ultra.name)
        elif key == Key.down:
            if ultra['aim']['silence'] > 0:
                ultra['aim']['silence'] -= 1
                print(ultra['aim']['silence'])
                print(ultra.name)
        elif key == Key.left:
            if ultra['aim']['x'] > -500:
                ultra['aim']['x'] -= 1
                print(ultra['aim']['x'])
                print(ultra.name)
        elif key == Key.right:
            if ultra['aim']['x'] < 500:
                ultra['aim']['x'] += 1
                print(ultra['aim']['x'])
                print(ultra.name)
        if key == Key.esc:
            # Stop listener
            return False

# Collect events until released


def keyListener():
    with Listener(
            on_press=on_press,
            on_release=on_release) as listener:
        listener.join()


if __name__ == "__main__":
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=2, rate=RATE, input=True,
                    frames_per_buffer=CHUNK, output=True)

    q = threading.Thread(target=keyListener)
    q.start()
    # update plot while stream is open
    for i in range(sys.maxsize**10):
        soundplot(stream)

    stream.stop_stream()
    stream.close()
    p.terminate()
