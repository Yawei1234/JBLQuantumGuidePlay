from UltraDict import UltraDict
import threading
import time
import random
import json
import csv

global ultra
global ultraTimer
global ultraListenerTimer
global entities
global isRunning
global q

entities = [
    {
        'silence': 5,
        'x': 0,
        'y': 0,
        'dist': 0,
        'multiplier': 1,
        'stopped': False,
        'encoded': "null",
        'class': 'aim',
        'isRunning': True,
        'id': 1,
    },
    {
        'silence': 5,
        'x': 0,
        'y': 0,
        'dist': 0,
        'multiplier': 1,
        'stopped': True,
        'encoded': "null",
        'class': 'enemy',
        'isRunning': True,
        'id': 2,
    },
    {
        'silence': 5,
        'x': 0,
        'y': 0,
        'dist': 0,
        'multiplier': 1,
        'stopped': True,
        'encoded': "null",
        'class': 'friend',
        'isRunning': True,
        'id': 3,
    }
]

ultraTimer = None

ultra = UltraDict(shared_lock=True,
                  recurse=True, name='very_unique_name', full_dump_size=10000*4)

for entitie in entities:
    ultra[entitie['class']] = entitie

print("sharedmemo-ultra-started", ultra)


def update_friend(newFriend):
    # print("sharedmemo-ultra-update_friend", newFriend)
    # convert to dict
    if not isinstance(newFriend, dict):
        newFriend = newFriend.to_dict()

    global ultra
    if ultra is None:
        return
    try:
        ultra['friend']['silence'] = float(newFriend['silence'])
        ultra['friend']['x'] = int(newFriend['x'])
        ultra['friend']['y'] = int(newFriend['y'])
        ultra['friend']['dist'] = float(newFriend['dist'])
        ultra['friend']['multiplier'] = float(newFriend['multiplier'])
        ultra['friend']['stopped'] = bool(newFriend['stopped'])
        ultra['friend']['id'] = int(newFriend['id'])
    except Exception as e:
        print("sharedmemo-ultra-update_friend-error", e)
        return


def update_enemy(newEnemy):
    # print("sharedmemo-ultra-update_enemy", newEnemy)
    # convert to dict
    if not isinstance(newEnemy, dict):
        newEnemy = newEnemy.to_dict()

    global ultra
    if ultra is None:
        return
    try:
        ultra['enemy']['silence'] = float(newEnemy['silence'])
        ultra['enemy']['x'] = int(newEnemy['x'])
        ultra['enemy']['y'] = int(newEnemy['y'])
        ultra['enemy']['dist'] = float(newEnemy['dist'])
        ultra['enemy']['multiplier'] = float(newEnemy['multiplier'])
        ultra['enemy']['stopped'] = bool(newEnemy['stopped'])
        ultra['enemy']['id'] = int(newEnemy['id'])
    except Exception as e:
        print("sharedmemo-ultra-update_enemy-error", e)
        return


def update_aim(newAim):
    print("\n__", newAim)
    # convert to dict
    if not isinstance(newAim, dict):
        newAim = newAim.to_dict()

    global ultra
    if ultra is None:
        return
    try:
        ultra['aim']['silence'] = float(newAim['silence'])
        ultra['aim']['x'] = int(newAim['x'])
        ultra['aim']['y'] = int(newAim['y'])
        ultra['aim']['dist'] = float(0)
        ultra['aim']['multiplier'] = float(newAim['multiplier'])
        ultra['aim']['stopped'] = bool(newAim['stopped'])
        ultra['aim']['id'] = int(1)

        if ultra['aim']['encoded'] != "null":
            return ultra['aim']['encoded']
        return None
    except Exception as e:
        print("sharedmemo-ultra-update_aim-error", e)
        return


def retryUltra(ultraTimer, retries):
    if ultraTimer is not None:
        ultraTimer.cancel()
        print("ultraTimer retry 1 sec")
        ultraTimer = threading.Timer(1, ultraChangeListener, args=[retries+1])
        ultraTimer.start()
    else:
        print("ultraTimer setretry 1 sec")
        ultraTimer = threading.Timer(1, ultraChangeListener, args=[retries+1])
        ultraTimer.start()


def processChange(entity, ultraChanges):
    global ultraListenerTimer
    if entity['class'] == 'aim':
        if ultraChanges['aim'] is not None:
            if ultraChanges['aim']['encoded'] != 'null':
                print("ultraChangeListener-aim-base64",
                      ultraChanges['aim']['encoded'])
                # wait 1 sec and set ultraListenerTimer to 0.1
                time.sleep(1)
                ultraListenerTimer = 0.1
    pass


def ultraChangeListener(isRetry=0):
    global entities
    global isRunning
    global ultraTimer
    global ultraListenerTimer
    retries = isRetry

    print("ultraChangeListener-starting", retries)
    while isRunning == True:

        try:

            try:
                ultraChanges = ultra
            except Exception as e:
                print("waiting-for-ultra-node\n", e)
                retryUltra(ultraTimer, retries)
                break

            for entity in entities:
                if entity['isRunning'] == False:
                    pass

                if entity['class'] == 'aim':
                    ultraListenerTimer = 1
                    processChange(entity, ultraChanges)
                    pass

                if entity['class'] == 'enemy':
                    ultraListenerTimer = 1
                    processChange(entity, ultraChanges)
                    pass

                if entity['class'] == 'friend':
                    ultraListenerTimer = 1
                    processChange(entity, ultraChanges)
                    pass

        except Exception as e:
            print("waiting-for-dependepencies\n", e)
            # try again in 1
            retryUltra(ultraTimer, retries)
            break

        time.sleep(ultraListenerTimer)


def clearUltra():
    global ultra
    global ultraTimer
    global ultraListenerTimer
    global entities
    global q
    global isRunning

    isRunning = False
    for entitie in entities:
        ultra[entitie['class']].clear()

    ultra = None
    ultraTimer = None
    ultraListenerTimer = None
    entities = None
    q = None


isRunning = True
q = threading.Thread(target=ultraChangeListener,
                     daemon=True, name='ultraChangeListener')
q.start()


# # debug
# # generate 100 random update_aim

# maxRadius = 1000
# debuglist = []
# xBase = -maxRadius

# for i in range(5000):

#     # x = random.randint(-maxRadius, maxRadius)
#     y = random.randint(-maxRadius, maxRadius)
#     # y = 0

#     if xBase < maxRadius:
#         xBase += 1
#     else:
#         xBase = -maxRadius

#     x = xBase

#     # cartesian distance from 0,0
#     dist = int((x**2 + y**2)**0.5)
#     silence = (dist / (maxRadius+maxRadius/2) * 100) * 0.01

#     if q is None:
#         print("waiting-sharedmemo-ultra-update_aim", i)
#         break

#     payload = {
#         'silence': 0,
#         'x': x,
#         'y': y,
#         'dist': dist,
#         'multiplier': 1,
#         'stopped': False,
#         'encoded': "null",
#         'class': 'aim',
#         'isRunning': True,
#         'id': int(time.time()),
#     }
#     debuglist.append(payload)

#     t1 = time.time()
#     update_aim(payload)
#     # time.sleep(0.1)
#     t2 = time.time()
#     print("sharedmemo-ultra-update_aim", (t2-t1))


# with open('debuglist.csv', 'w') as f:  # You will need 'wb' mode in Python 2.x
#     w = csv.DictWriter(f, debuglist[0].keys())
#     w.writeheader()
#     for i in range(len(debuglist)):
#         w.writerow(debuglist[i])
#         print("--- ", debuglist[i])
