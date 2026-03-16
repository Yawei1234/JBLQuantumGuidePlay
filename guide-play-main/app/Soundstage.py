import numpy as np
from utils import pad, read, play_audio, get_audio
from pydub.playback import play
from pydub import AudioSegment
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from Speakers import BasicSpeaker, AmbisonicSpeakers, HRTFSpeaker
import matplotlib as mpl
import matplotlib.lines as mlines


class Soundstage():
    def __init__(self, size, speakers=[]):
        self.size = size
        self.speakers = speakers

    def play(self, op="overlay", save_name=None, callback=None):

        # print("SPEAKERS_SIZE", len(self.speakers))
        """
        Combine all speakers on a Soundstage by either appending them
        or ovelaying them.
        """
        # assert (len(self.speakers) > 0)
        # SORT SOUNDS BY LENGTH (LONGEST TO SHORTEST)
        if len(self.speakers) == 0:
            return
        mixed = self.speakers[0].get_audio()
        for s in self.speakers[1:]:
            if op == "overlay":
                mixed = mixed.overlay(s.get_audio())
            elif op == "append":
                mixed = mixed.append(s.get_audio())
        if save_name is not None:
            mixed.export(save_name, format="wav")
            # song = AudioSegment.from_wav(save_name)
            # play(song)
        play(mixed)

        if callback is not None:
            callback(self)

    def update_speaker(self, speaker, id):
        # iterate through speakers and find speaker by id
        for s in self.speakers:
            if s.id == id:
                s = speaker
                return
        pass

    def add_speaker(self, speaker):
        self.speakers.append(speaker)

    def add_speakers(self, speakers):
        self.speakers += speakers

    def remove_speaker(self, id):
        self.speakers = [x for x in self.speakers if x.id != id]
        # for s in self.speakers:
        #     if s.id == id:
        #         # self.speakers.remove(s)

        #         return

    def plot(self, title="BlindMode Soundstage"):
        """
        Construct a simple spatial plot of a user and the speakers on the soundstage.
        """
        width = self.size[0]
        height = self.size[1]
        fig, ax = plt.subplots()

        ax.add_patch(plt.Rectangle((-height/2, -width/2), width, height,
                                   edgecolor='brown',
                                   fill=False,
                                   lw=2))

        ax.autoscale_view()

        for s in self.speakers:
            if type(s) is BasicSpeaker:
                plt.plot(s.point[0], s.point[1], marker="x",
                         markersize=10, markeredgecolor="red")
                plt.plot(s.ear_dist, 0, marker="o", markersize=10,
                         markeredgecolor="black", markerfacecolor="pink")
                plt.plot(-s.ear_dist, 0, marker="o", markersize=10,
                         markeredgecolor="black", markerfacecolor="pink")

            if type(s) is AmbisonicSpeakers:
                for k in s.speakers:
                    plt.plot(k.point[0], k.point[1], marker="h", markersize=10,
                             markeredgecolor="black", markerfacecolor="c")

            if type(s) is HRTFSpeaker:
                plt.plot(s.point[0], s.point[1], marker="v", markersize=10,
                         markeredgecolor="black", markerfacecolor="yellow")
                plt.plot(s.ear_dist, 0, marker="o", markersize=10,
                         markeredgecolor="black", markerfacecolor="pink")
                plt.plot(-s.ear_dist, 0, marker="o", markersize=10,
                         markeredgecolor="black", markerfacecolor="pink")

        ear = mlines.Line2D([], [], color='pink', markeredgecolor="black",  marker='o', linestyle='None',
                            markersize=10, label='Ears')
        basic = mlines.Line2D([], [], color='red', marker='x', linestyle='None',
                              markersize=10, label='Basic Speaker')
        ambi = mlines.Line2D([], [], color='c', markeredgecolor="black", marker='h', linestyle='None',
                             markersize=10, label='Ambisonic Speaker')
        hrtf = mlines.Line2D([], [], color='yellow', markeredgecolor="black", marker='v', linestyle='None',
                             markersize=10, label='HRTF Speaker')

        plt.legend(handles=[ear, basic, ambi, hrtf])
        plt.title(title)
        plt.axis('equal')
        plt.show()

    def rotate(self, theta):
        for s in self.speakers:
            s.rotate(theta)
