from pythonosc import udp_client
from pythonosc import osc_server
from pythonosc import dispatcher
from winsound import PlaySound, SND_FILENAME, SND_ASYNC
import queue
import threading

import time


class oscQUEUE:

    def __init__(self, cancellation_event: threading.Event, msg_queue: queue.Queue[tuple[bool, int, int]], ip="127.0.0.1", port=5006,):

        # use OSC port and address that was set in the config
        self.client = udp_client.SimpleUDPClient(ip, int(port))
        self.cancellation_event = cancellation_event
        self.msg_queue = msg_queue

        print("OSC Queue initialized", self.client)

    def run(self):

        while True:
            if self.cancellation_event.is_set():
                print("Exiting OSC Queue")
                return
            try:
                (topic, payload) = self.msg_queue.get(block=True, timeout=0.1)
            except:
                continue

            self.client.send_message(topic, payload)


class oscRECEIVER:
    def __init__(self, cancellation_event: threading.Event,ip="127.0.0.1", port=5005):
        self.cancellation_event = cancellation_event
        self.dispatcher = dispatcher.Dispatcher()
        self.port = port
        try:
            self.server = osc_server.ThreadingOSCUDPServer(
                (ip, int(port)), self.dispatcher)
        except:
            print(
                f"[ERROR] OSC Recieve port: {port} occupied. ")

    def shutdown(self):
        print("Shutting down OSC receiver")
        try:
            self.server.shutdown()
        except:
            pass

    def pong(self, address, *args):
        print("PONG", args)
        return

    def mapDispatcher(self, topic, callback, str):
        self.dispatcher.map(topic, callback, str)

    def run(self):

        # bind what function to run when specified OSC message is received
        try:
            self.dispatcher.map('/pong', self.pong)
            self.server.serve_forever()

        except:
            # show exception
            
            print(
                f"[ERROR] OSC Recieve port: {self.port} occupied. ")
