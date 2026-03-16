import dxcam

# install OpenCV using `pip install dxcam[cv2]` command.
import cv2

TOP = 0
LEFT = 0
RIGHT = 1920
BOTTOM = 1080
region = (LEFT, TOP, RIGHT, BOTTOM)
title = "[DXcam] Capture benchmark"

target_fps = 30
print("GOT_INFO_GPU\n", dxcam.device_info())
print("GOT_INFO_MONITORS\n", dxcam.output_info_arr())

monitors = dxcam.output_info_arr()
# find the primary monitor
primary = [m for m in monitors if m["primary"] == True][0]
print("PRIMARY_MONITOR\n", primary)
# camera = dxcam.create(
#     device_idx=primary['device'], output_idx=primary['output'], output_color="BGR")

camera = dxcam.create(
    device_idx=0, output_idx=1, output_color="BGR")


camera.start(target_fps=target_fps, video_mode=True)
writer = cv2.VideoWriter(
    "video.mp4", cv2.VideoWriter_fourcc(*"mp4v"), target_fps, (1920, 1080)
)
for i in range(600):
    # print(f"Frame {i}")
    # frame = camera.grab(region=region)
    frame = camera.get_latest_frame()
    cv2.imshow(title, frame)
    # cv2.waitKey(1)
    # destroy window when ESC key is pressed
    writer.write(frame)
    if cv2.waitKey(1) == 27:
        break
camera.stop()
writer.release()
