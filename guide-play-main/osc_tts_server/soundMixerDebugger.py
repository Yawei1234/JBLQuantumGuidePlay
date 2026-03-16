from soundMixer import SoundMixer

path = "../app/UI"

threadMixer = SoundMixer(path)

threadMixer.start()
threadMixerRef = threadMixer.threadStarter(0, path)

# start loop
while True:
    pass