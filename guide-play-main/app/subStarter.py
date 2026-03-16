import time
import threading
from subprocess import Popen, PIPE, STDOUT
import os
import logging

logger = logging.getLogger(__name__)

DIRPATH = os.path.join(os.path.dirname(__file__))
CLIPATH = os.path.join(DIRPATH, "server", "guide-play-services-cli.exe")


class SubStarter(threading.Thread):
    def __init__(self, path, params=None, subID="sub ->:", callback=None):
        if path is None:
            self.path = [CLIPATH]
        else:
            self.path = path
        if params is None:
            self.params = []
        else:
            self.params = params
            self.params.insert(0, self.path)
            self.path = self.params
        self.child = None
        self.started = False
        self.stdout = None
        self.stderr = None
        self.lastKeepAlive = None
        self.subID = subID
        threading.Thread.__init__(self, name="subCLI", daemon=True)
        self.requestId = None
        self.callback = callback
        self.gpuReady = False
        self.cpuReady = False

    def parseResult(self, result):

        if "defaulting to CPU" in result:
            self.gpuReady = False
            self.cpuReady = True
            print(""+self.subID+" parseResult", "GPU not ready")

        if self.requestId is not None and self.callback is not None:
            # search for requestId on result string
            # print(""+self.subID+"parseResult", result)
            try:
                result = result.split("\n")
                for line in result:
                    if "read_done" in line:
                        data = line.split("read_done(")
                        if len(data) > 1:
                            requestId = data[1].split(")")[0]
                            if self.requestId in line:
                                print(""+self.subID +
                                      " parseResult found requestId", requestId)
                                self.callback(line)
                                self.requestId = None
            except Exception as e:
                logger.error("parseResult-error", e)

    def run(self):

        print(""+self.subID+" starting", self.path)
        self.child = Popen(self.path, stdout=PIPE, stdin=PIPE,
                           stderr=STDOUT, shell=True, bufsize=1, universal_newlines=True, close_fds=True)
        self.started = True
        # self.stdout, self.stderr = self.child.communicate()
        stdout = []
        while True:
            time.sleep(0.05)
            # flush
            # self.child.stdin.flush()
            # print(""+self.subID+" waiting for line")
            line = self.child.stdout.readline()
            stdout.append(line)
            self.parseResult(line)
            # clear
            # stdout = []
            print("---- "+self.subID+" "+line)
            if line == '' and self.child.poll() != None:
                self.started = False
                break
        return ''.join(stdout)

    def stop(self):
        self.child.stdin.write('quit\n\r')
        self.child.wait()
        self.started = False

    def terminate(self):
        if self.child is not None:
            self.child.stdin.write('quit\n\r')
            time.sleep(0.5)
            self.child.terminate()
            self.started = False
            self.child.wait()

    def poll(self):
        if self.child is not None:
            return self.child.poll()
        else:
            return None

    def sendAndWait(self, message, requestId=None):

        self.requestId = requestId

        if self.cpuReady == True or self.gpuReady == True:
            if self.started:
                try:
                    finalMessage = message
                    if requestId != "":
                        finalMessage = message+" "+requestId
                        finalMessage.replace("\n", "")
                        finalMessage.replace("\r", "")

                    print(""+self.subID+" sendAndWait", "*"+finalMessage+"*")
                    self.child.stdin.write(''+finalMessage+'\n\r')
                    self.child.stdin.flush()
                except Exception as e:
                    # return
                    # print(""+self.subID+" send error", e, message)
                    logger.error(""+self.subID+" send error >>", e)
        else:
            print(""+self.subID+" sendAndWait", "cpu or gpu not ready")

    def send(self, message):
        if self.started:
            try:
                self.child.stdin.write(''+message+'\n\r')
                self.child.stdin.flush()
            except Exception as e:
                # return
                # print(""+self.subID+" send error", e, message)
                logger.error(""+self.subID+" send error >>", e)

    def show_output(self):
        return self.child.communicate()[0]


# test = SubStarter(CLIPATH)
# test.start()

# time.sleep(1)

# print("started_check", test)

# if test.started:
#     print("started")
#     test.send('say this is the world premiere\n\r')
#     time.sleep(1)
#     test.send('say the number 1 record in the world\n\r')
#     time.sleep(5)
#     test.stop()
