import win32gui
import win32console
import ctypes
import platform
import subprocess
import re
import pywintypes
import win32api
import win32con
from screeninfo import get_monitors
import tkinter as tk
import ctypes
import os
import pygame
import sys
import pytesseract
from PIL import Image
from utils import resource_path
DIRPATH = os.path.join(os.path.dirname(__file__))
win = win32console.GetConsoleWindow()
win32gui.ShowWindow(win, 0)

pytesseract.pytesseract.tesseract_cmd = resource_path(
    'tesseract/tesseract.exe')


def hideConsole():
    """
    Hides the console window in GUI mode. Necessary for frozen application, because
    this application support both, command line processing AND GUI mode and theirfor
    cannot be run via pythonw.exe.
    """

    whnd = ctypes.windll.kernel32.GetConsoleWindow()
    if whnd != 0:
        ctypes.windll.user32.ShowWindow(whnd, 0)
        # if you wanted to close the handles...
        # ctypes.windll.kernel32.CloseHandle(whnd)


def showConsole():
    """Unhides console window"""
    whnd = ctypes.windll.kernel32.GetConsoleWindow()
    if whnd != 0:
        ctypes.windll.user32.ShowWindow(whnd, 1)


def getVideoModes(resolution=(1920, 1080)):
    # dll = "SDL.dll"
    # sdl_dll = ctypes.CDLL(os.path.join(DIRPATH, dll))
    # modes = sdl_dll.SDL_ListModes(None, None)
    pygame.init()
    modes = pygame.display.list_modes()
    # check if (1920, 1080) is supported
    if resolution in modes:
        print(""+str(resolution)+" supported")
        supported = True
    else:
        print(""+str(resolution)+" not supported")
        supported = False

    pygame.quit()
    return modes, supported
    # print("Modes:", modes)


def get_screen_resolution_methods():
    result = get_screen_resolution()

    monitorsList = result[0]
    findPrimary = result[1]
    monitorIndex = result[2]

    if findPrimary is not None:
        # convert value to tuple (width, height)
        primaryResolution = findPrimary[1].split("x")
        findPrimary = (int(primaryResolution[0]), int(
            primaryResolution[1]))
        return findPrimary
    else:
        return get_screen_resolution_by_point()


def get_screen_resolution_by_point():
    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


def get_screen_resolution():
    monitors = []
    for monitor in get_monitors():
        resolution = f"{monitor.width}x{monitor.height}"
        dpi = f"{monitor.width_mm / monitor.width:.2f}"
        monitors.append((monitor.name, resolution, dpi, monitor.is_primary))
        # print(
        #     f"Monitor: {monitor.name}, isPrimary: {monitor.is_primary}, Resolution: {monitor.width}x{monitor.height}, DPI: {monitor.width_mm / monitor.width:.2f}")
    # find primary
    primary = [monitor for monitor in monitors if monitor[3] == True]
    # find index of primary
    primaryIndex = monitors.index(primary[0])
    return monitors, primary[0], primaryIndex


def on_set_resolution(width: int, height: int):
    # adapted from Peter Wood: https://stackoverflow.com/a/54262365
    try:
        devmode = pywintypes.DEVMODEType()
        devmode.PelsWidth = width
        devmode.PelsHeight = height

        devmode.Fields = win32con.DM_PELSWIDTH | win32con.DM_PELSHEIGHT

        win32api.ChangeDisplaySettings(devmode, 0)
    except Exception as e:
        print("Error setting resolution", e)


def get_screen_dpi():
    """Gets the screen DPI.
    Returns:
      A tuple of (horizontal DPI, vertical DPI).
    """
    if platform.system() == "Windows":
        return get_screen_dpi_windows()
    elif platform.system() == "Linux":
        return get_screen_dpi_linux()
    else:
        raise NotImplementedError(
            "Screen DPI is not supported on this platform.")


def get_screen_dpi_windows():
    """Gets the screen DPI on Windows.
    Returns:
      A tuple of (horizontal DPI, vertical DPI).
    """
    user32 = ctypes.windll.user32
    screen_size = user32.GetSystemMetrics(78)  # SM_CXSCREEN
    screen_dpi = user32.GetSystemMetrics(90)  # SM_DPISCALE
    return (screen_size * screen_dpi, screen_size * screen_dpi)


def get_screen_dpi_linux():
    """Gets the screen DPI on Linux.
    Returns:
      A tuple of (horizontal DPI, vertical DPI).
    """
    output = subprocess.check_output(["xrandr", "--dpi"])
    lines = output.decode("utf-8").splitlines()
    for line in lines:
        match = re.match(r"^ *\d+\.\d+ *x *\d+\.\d+ *\dpi", line)
        if match:
            return (int(match.group(1)), int(match.group(2)))
    return None


def getDPITK():
    tkDPI = tk.Tk()
    # Hide the tkDPI window
    tkDPI.withdraw()
    # Get the screen width and height in pixels
    screen_width = tkDPI.winfo_screenwidth()
    screen_height = tkDPI.winfo_screenheight()
    # Get the screen width and height in millimeters
    screen_width_mm = tkDPI.winfo_screenmmwidth()
    screen_height_mm = tkDPI.winfo_screenmmheight()
    # Calculate the DPI
    dpi_x = screen_width / (screen_width_mm / 25.4)
    dpi_y = screen_height / (screen_height_mm / 25.4)
    print(f"Screen DPI (X): {dpi_x}")
    print(f"Screen DPI (Y): {dpi_y}")
    # Destroy the tkDPI window
    tkDPI.destroy()
    return dpi_x, dpi_y


def verify_license():

    text = pytesseract.image_to_string(Image.open(os.path.join(DIRPATH, "UI/images/200x200.png")), lang='eng',
                                       config='--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789')

    print("TESSERACT_TEST", text)


print("Screen resolution:", get_screen_resolution())
horizontal_dpi, vertical_dpi = get_screen_dpi()

print("Horizontal DPI:", horizontal_dpi)
print("Vertical DPI:", vertical_dpi)
print("Using tkinter:", getDPITK())
print("Using screeninfo:", get_screen_resolution_by_point())
print("Video modes:", getVideoModes())

# if getattr(sys, 'frozen', False):
# hideConsole()

# verify_license()

# while True:
#     width = int(input("Enter the width: "))
#     height = int(input("Enter the height: "))
#     on_set_resolution(width, height)
#     print("Screen resolution:", get_screen_resolution())
#     print("Horizontal DPI:", horizontal_dpi)
#     print("Vertical DPI:", vertical_dpi)
#     print("Using tkinter:", getDPITK())
#     print("Using screeninfo:", get_screen_dpi())
#     print()
