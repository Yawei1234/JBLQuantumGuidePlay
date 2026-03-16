'''
Code formally written by Alexander James Porter (Contact: AlexanderPorter1234@gmail.com) 20/02/2023
Code has been optimised for reading screenshots of final scoreboard in the game VALORANT
Lots of code is utilised from https://github.com/eihli/image-table-ocr#org67b1fc2
'''
import sys
import cv2
import numpy as np
import pytesseract
import subprocess
import math
import csv
from tqdm import tqdm
from PIL import Image, ImageFilter
from ocrToolsV2 import functions as srf
from utils import resource_path
import os
import time
DIR_PATH = os.path.dirname(os.path.realpath(__file__))

# Setting up tesseract - only needs this if you have directly installed tesseract (I think).
pytesseract.pytesseract.tesseract_cmd = resource_path(
    'tesseract/tesseract.exe')

# # Reads in your file and crops out the table using find_tables
# image_filename = input(
#     "Please input the name of your screenshot i.e ScreenShot.png:   ")
image_filename = "232306_home_settings_audio.png"
# show
# test file exists
if not os.path.exists(image_filename):
    print("File does not exist")
    sys.exit()

image = cv2.imread(os.path.join(DIR_PATH, image_filename.split("/")[-1]),
                   cv2.IMREAD_GRAYSCALE)
# show
# cv2.imshow("image", image)
# cv2.waitKey(0)
# cv2.destroyAllWindows()
# sleep
# time.sleep(2)
image = srf.find_tables(image)
# cv2.imwrite("table.png",image)

# Extracts each row of elements from the table
cell_images_rows = srf.extract_cell_images_from_table(image)

# Reads the extracted rows and converts them to a list of lists.
output = srf.read_table_rows(cell_images_rows)

# Writes the output.
inp = input("Do you want your CSV in EU or UK format?   ")
if inp == "EU":
    delim = ';'
elif inp == "UK":
    delim = ","
else:
    print("You must choose between EU and UK")
srf.write_csv(output, delim)

print("Done. Output written to scoreboard.csv.")
