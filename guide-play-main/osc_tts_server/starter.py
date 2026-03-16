from subprocess import run
from time import sleep
import argparse
import sys

global crash_times
global result
global restart_timer

result = None
crash_times = 0
restart_timer = 0.5


def start_script():
    global result

    parser = argparse.ArgumentParser()
    parser.add_argument("--ip",
                        default="127.0.0.1", help="The ip to listen on")
    parser.add_argument("--port",
                        type=int, default=5005, help="The port to listen on")
    parser.add_argument("--path", default="../app",)
    parser.add_argument(
        "--exe", default="E:/projects/opencv-games/blindModeServers/Scripts/")
    parser.add_argument("--service", default="")
    args = parser.parse_args()

    finalCOMMAND = ""+str(args.exe)+""+str(args.service) + \
        " --path "+str(args.path)+" --port "+str(args.port)+""
    try:
        # Make sure 'python' command is available
        result = run(finalCOMMAND, check=True)
    except:
        # Script crashed, lets restart it!
        # get exception and handle it
        # e = sys.exc_info()[0]
        handle_crash(result, args, finalCOMMAND)


def handle_crash(e, args, cmd):
    global restart_timer
    global crash_times
    crash_times += 1
    if e is not None:
        print("CRASHED", e.stdout, e.stderr)
    print("CRASHED_RESTARTING", crash_times)
    print("CRASHED_ARGS", args)
    print("CRASHED_CMD", cmd)
    sleep(restart_timer)  # Restarts the script after 2 seconds
    start_script()


start_script()
