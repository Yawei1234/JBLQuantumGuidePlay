from UltraDict import UltraDict
import threading
import sys
import data
import time

global ultra
global ultraTimer
global ultraThread

ultraTimer = None
path = "UI"


def threadStarter(retries, path):
    global ultraTimer
    if retries > 5:
        print("ultraTimer retries exceeded")
        return
    try:
        ultraTimer = threading.Timer(1, threadStarter, args=[0, path])
        ultraTimer.start()
    except Exception as e:
        print("ultraTimer waiting-for-ultra-node\n", e)
        retryUltra(ultraTimer, retries)


def retryUltra(ultraTimer, retries):

    if ultraTimer is not None:
        ultraTimer.cancel()
        print("ultraTimer retry 1 sec")
        ultraTimer = threading.Timer(1, ultraStarter, args=[retries+1, path])
        ultraTimer.start()
    else:
        print("ultraTimer 1s retry 1 sec")
        ultraTimer = threading.Timer(1, ultraStarter, args=[retries+1, path])
        ultraTimer.start()


def ultraListener():

    global ultra
    global ultraTimer

    while True:
        try:
            ultra = UltraDict(shared_lock=True,
                              recurse=True, name='very_unique_name', full_dump_size=10000*4)
            print("UltraDict initialized")
            # break
        except:
            print("Error: ", sys.exc_info()[0])
            print("Retrying...")
            time.sleep(1)
            retryUltra(ultraTimer, 0)
            continue


def ultraStarter():
    global ultraThread

    if ultraThread is not None:
        ultraThread.cancel()
        print("ultraThread retry 1 sec")
        ultraThread = threading.Thread(
            target=ultraListener, daemon=True, name="ultraThread")
        ultraThread.start()
    else:
        ultraThread = threading.Thread(
            target=ultraListener, daemon=True, name="ultraThread")

        ultraThread.start()


threadStarter(0, path)

while True:
    pass
