import pyaudio
import wave
import numpy as np
# import noisereduce as nr

#This library helps us in plotting the  audio
import matplotlib.pyplot as plt 

def plotAudio2(output):
        fig, ax = plt.subplots(nrows=1,ncols=1, figsize=(20,4))
        plt.plot(output, color='blue')
        ax.set_xlim((0, len(output)))
        plt.show()

CHUNK = 22050
FORMAT = pyaudio.paFloat32
CHANNELS = 2
RATE = 44100
RECORD_SECONDS = 20

p = pyaudio.PyAudio()

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

print("* recording")

frames = []


for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    data = stream.read(CHUNK)
    data_sample = np.frombuffer(data, dtype=np.float32)

    print("data sample")
    plotAudio2(data_sample)

stream.stop_stream()
stream.close()
p.terminate()