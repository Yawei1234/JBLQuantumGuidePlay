import pydub
import numpy as np
from pydub.playback import play
import cv2
import data

path_prefix = data.path_prefix

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
