import cv2
import kthread
from time import strftime, time
from ffmpeg_screenshot_pipe.ffmpeg_screenshot_pipe_multi import runasync, procresults
from ffmpeg_screenshot_pipe import FFmpegshot, get_max_framerate


def timest(): return strftime("%Y_%m_%d_%H_%M_%S")


def show_screenshot(screenshot):
    cv2.imshow("test", screenshot)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        cv2.destroyAllWindows()
        return False
    return True


def show_screenshot_bench(
    screenshotiter, stop_at_frame=100, quitkey="q", show_screenshot=True
):
    def show_screenshotx():
        cv2.imshow("test", screenshot)
        if cv2.waitKey(1) & 0xFF == ord(quitkey):
            cv2.destroyAllWindows()
            return False
        return True

    framecounter = 0
    fps = 0
    start_time = time()
    for screenshot in screenshotiter:
        if stop_at_frame:
            if framecounter > stop_at_frame:
                break
            framecounter += 1
        if show_screenshot:
            sho = show_screenshotx()
        else:
            sho = True
        fps += 1
        if not sho:
            break
    print(f"fast_ctypes_screenshots: {fps / (time() - start_time)}")
    cv2.destroyAllWindows()


# GDIÌ METHOD

# with FFmpegshot() as sc:
#     timestamp = timest()
#     fps = 0
#     start_time = time()
#     piciter = sc.capture_window_gdigrab(  # generator
#         searchdict={
#             "title_re": ".*Counter-Strike 2.*",
#             "status": "visible",
#             "path_re": ".*cs2.exe.*",
#         },
#         frames=60,
#         draw_mouse=True,
#     )
#     cont = show_screenshot_bench(
#         piciter, stop_at_frame=1000, quitkey="q", show_screenshot=True)
#     fps += 1
#     print(f'FPS: {fps / (time() - start_time)}')


# GDI 1 SCREEN
# with FFmpegshot() as sc:
#     piciter = sc.capture_one_screen_gdigrab(
#         monitor_index=0,
#         frames=60,
#         draw_mouse=True,
#     )
# show_screenshot_bench(
#     piciter, stop_at_frame=None, quitkey="q", show_screenshot=True
# )


# DDA METHOD

# with FFmpegshot() as sc:
#     start_time, fps = time(), 0
#     for screenshot in sc.capture_one_screen_ddagrab(
#             monitor_index=0,
#             frames=60,
#             draw_mouse=True,
#     ):
#         cont = show_screenshot(screenshot)
#         if not cont:
#             break
#         fps += 1
# print(f'FPS: {fps / (time() - start_time)}')


# Reminder: Ensure to terminate FFmpeg instances if not using "with" statement
# ffmpeg_screenshot = FFmpegshot()
# # Capture and display screenshots
# piciter = ffmpeg_screenshot.capture_one_screen_ddagrab(
#     monitor_index=0,
#     frames=60,
#     draw_mouse=True,
# )
# # Terminate FFmpeg instances after usage
# show_screenshot_bench(
#     piciter, stop_at_frame=1000, quitkey="q", show_screenshot=True
# )
# # don't forget to kill the ffmpeg instances after you are done
# ffmpeg_screenshot.kill_ffmpeg()


# CTYPES METHOD
with FFmpegshot() as sc:
    piciter_ = sc.capture_all_screens_ctypes(ascontiguousarray=True)
    piciter2_ = []
    for ini, pi in enumerate(piciter_):
        piciter2_.append(pi.copy())

        if ini == 2000:
            break
