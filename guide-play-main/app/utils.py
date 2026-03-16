import pydub
import numpy as np
from pydub.playback import play
import cv2
import sys
import ctypes
import win32gui
import win32con
import re
import os
import psutil
import subprocess
import re
from subprocess import Popen, PIPE, DEVNULL


def get_running_processes(look_for='', pid=None, add_exe=True):
    # TODO: Linux implementation
    cmd = f'tasklist /NH'
    if look_for:
        if not look_for.endswith('.exe') and add_exe:
            look_for += '.exe'
        cmd += f' /FI "IMAGENAME eq {look_for}"'
    if pid is not None:
        cmd += f' /FI "PID eq {pid}"'
    p = Popen(cmd, shell=True, stdout=PIPE, stdin=DEVNULL,
              stderr=DEVNULL, text=True, encoding='iso8859-2', close_fds=True)
    p.stdout.readline()
    for task in iter(lambda: p.stdout.readline().strip(), ''):
        m = re.match(r'(.+?) +(\d+) (.+?) +(\d+) +(\d+.* K).*', task)
        if m is not None:
            yield {'name': m.group(1), 'pid': int(m.group(2)), 'session_name': m.group(3),
                   'session_num': m.group(4), 'mem_usage': m.group(5)}


def is_running_as_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def checkNarrator():
    # detect if narrator process is running on windows
    for proc in psutil.process_iter(['pid', 'name']):
        # print(proc.info['name'])
        name = proc.info['name'].lower()
        if "narrator.exe" in name:
            return True, proc
    return False, psutil.process_iter()


def checkRunningProcess(processName):
    for proc in psutil.process_iter(['pid', 'name']):
        name = proc.info['name'].lower()
        if processName in name:
            return True, proc
    return False, psutil.process_iter()


def coordsToPercent(coords):
    return (coords[0] / 1920, coords[1] / 1080)


def percentToCoords(percent, width=1920, height=1080):
    return (int(percent[0] * width), int(percent[1] * height))


def getRelativeCoords(coords, width=1920, height=1080):
    percentTL = coordsToPercent([coords[0], coords[1]])
    percentBR = coordsToPercent([coords[2], coords[3]])
    return [(percentToCoords(percentTL, width, height)[0],
             percentToCoords(percentTL, width, height)[1]),
            (percentToCoords(percentBR, width, height)[0],
                percentToCoords(percentBR, width, height)[1])]


def _window_enum_callback(hwnd, wildcard, cb):
    # print("FIND_WINDOW_WILDCARD_CB", wildcard,
    #       str(win32gui.GetWindowText(hwnd)))
    if re.match(wildcard, str(win32gui.GetWindowText(hwnd))) is not None:
        textName = win32gui.GetWindowText(hwnd)
        split = textName.split(" ")
        if len(split) > 2:
            return None
        if "Microsoft Edge" in textName:
            return None
        if "Microsoft Store" in textName:
            return None
        if "Windows Security" in textName:
            return None
        if "Google Chrome" in textName:
            return None
        if "Microsoft Text Input Application" in textName:
            return None
        if "Settings" in textName:
            return None
        print("WINDOW_ENUM_CALLBACK", hwnd, textName)
        cb(hwnd)
        return hwnd
    else:
        return None


def find_window(class_name, window_name=None):
    win32gui.FindWindow(class_name, window_name)


def focus_guideplay():
    find_window_wildcard(".*Guide Play.*", set_foreground)


def set_foreground(window_handle):
    try:
        win32gui.ShowWindow(window_handle, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(window_handle)
    except Exception as e:
        print("Error setting foreground window", e)


def find_window_wildcard(wildcard, cb):
    print("FIND_WINDOW_WILDCARD", wildcard, cb)
    win32gui.EnumWindows(
        lambda x, y: _window_enum_callback(x, y, cb), wildcard)


def set_active_on_top(handle=None, name="Counter-Strike 2"):
    if handle is None:
        handle = win32gui.FindWindow(None, name)
    hwnd = handle
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0,
                          0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)


def get_active_window():
    """
    Get the currently active window.

    Returns
    -------
    string :
        Name of the currently active window.
    """

    active_window_name = None
    window = None
    if sys.platform in ['Windows', 'win32', 'cygwin']:
        # https://stackoverflow.com/a/608814/562769

        window = win32gui.GetForegroundWindow()
        active_window_name = win32gui.GetWindowText(window)

    else:
        print("sys.platform={platform} is unknown. Please report."
              .format(platform=sys.platform))
        print(sys.version)
    return active_window_name, window


def lerp(a, b, t):
    """
    Linear interpolation between two points
    """
    return a + (b - a) * t


def read_transparent_png(filename):
    image_4channel = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
    alpha_channel = image_4channel[:, :, 3]
    rgb_channels = image_4channel[:, :, :3]

    # White Background Image
    white_background_image = np.ones_like(rgb_channels, dtype=np.uint8) * 255

    # Alpha factor
    alpha_factor = alpha_channel[:, :, np.newaxis].astype(np.float32) / 255.0
    alpha_factor = np.concatenate(
        (alpha_factor, alpha_factor, alpha_factor), axis=2)

    # Transparent Image Rendered on White Background
    base = rgb_channels.astype(np.float32) * alpha_factor
    white = white_background_image.astype(np.float32) * (1 - alpha_factor)
    final_image = base + white
    return final_image.astype(np.uint8)


def pad(signal, time, front=True, samples=-1):
    """
    Pad a signal in the front or back to simmulate delays (i.e. signal enters one ear before another)
    """
    if samples == -1:
        samples = int(time * 1000)
    if front:
        return samples, np.pad(signal, (samples, 0), 'constant')
    else:
        return samples, np.pad(signal, (0, samples), 'constant')


def read(f, normalized=False):
    """MP3 to numpy array"""
    a = pydub.AudioSegment.from_mp3(f)
    y = np.array(a.get_array_of_samples())
    duration = len(y) / a.frame_rate
    if a.channels == 2:
        y = y.reshape((-1, 2))
    if normalized:
        return a.frame_rate, np.float32(y) / 2**15, duration
    else:
        return a.frame_rate, y, duration


def play_audio(sr, x, normalized=False):
    """numpy array to MP3"""
    channels = 2 if (x.ndim == 2 and x.shape[1] == 2) else 1
    if normalized:  # normalized array - each item should be a float in [-1, 1)
        y = np.int16(x * 2 ** 15)
    else:
        y = np.int16(x)
    song = pydub.AudioSegment(
        y.tobytes(), frame_rate=sr, sample_width=2, channels=channels)
    play(song)
    # song.export(f, format="mp3", bitrate="320k")


def get_audio(sr, x, normalized=False):
    """numpy array to MP3"""
    channels = 2 if (x.ndim == 2 and x.shape[1] == 2) else 1
    if normalized:  # normalized array - each item should be a float in [-1, 1)
        y = np.int16(x * 2 ** 15)
    else:
        y = np.int16(x)
    song = pydub.AudioSegment(
        y.tobytes(), frame_rate=sr, sample_width=2, channels=channels)
    return song


def nround(x, base=5):
    """
    Rounding function to pick optimal discretized HRTF file
    """
    return base * round(x/base)


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(
        os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


# print("CHECKNARRATOR", checkNarrator())
# def cb(result):
#     print("CB", result)


# find_window_wildcard(".*Guide Play.*", cb)
