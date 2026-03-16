
import cv2
import kthread
from time import strftime
from ffmpeg_screenshot_pipe.ffmpeg_screenshot_pipe_multi import runasync, procresults

procresults.dequebuffer = 24
procresults.asyncsleep = 0.001
procresults.sleeptimeafterkill = 5
procresults.sleeptimebeforekill = lambda: procresults.sleeptimeafterkill * 0.9
activethreads = []


def timest(): return strftime("%Y_%m_%d_%H_%M_%S")


def start_display_thread():
    activethreads.append(kthread.KThread(
        target=display_thread, name="cv2function"))
    activethreads[-1].daemon = True
    activethreads[-1].start()


def display_thread(stop_at_frame=None):
    co = 0
    goback = False
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    while True:
        try:
            keys = list(procresults.results.keys())
            for prore in keys:
                try:
                    # this is how you have to access the results
                    cv2.imshow(str(prore), procresults.results[prore][-1])
                except Exception:
                    pass
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    cv2.waitKey(0)
                    goback = True
                    break
                if stop_at_frame:
                    co = co + 1
                    if co > stop_at_frame:
                        cv2.destroyAllWindows()
                        goback = True
                    break
            if goback:
                break
        except Exception as e:
            print(e)
            continue

    cv2.destroyAllWindows()
    procresults.stopfunction()


def kill_active_threads():
    for th in activethreads:
        if th.is_alive():
            th.kill()


def run_parallel(dictlist):
    runasync(dictlist)
    kill_active_threads()


if __name__ == "__main__":  # don't forget that when using multiprocessing!!

    # call the function that is doing something with the screenshots (in this case just showing)
    # as a thread before you run runasync.
    start_display_thread()

    dict0 = dict(
        function="capture_one_screen_ddagrab",
        monitor_index=0,
        frames=25,
        draw_mouse=True,
    )

    dict1 = dict(
        function="capture_one_screen_ddagrab",
        monitor_index=1,
        frames=25,
        draw_mouse=True,
    )
    run_parallel([dict0, dict1])
