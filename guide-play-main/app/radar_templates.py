import cv2 as cv
import numpy as np
from matplotlib import pyplot as pltimg
image_rgb = cv.imread('ocr_wrapper/template.png', 0)
image_gray = image_rgb.copy()
img_template = cv.imread('ocr_wrapper/template_ref.png', 0)
# We store the width and height of the template image
w, h = img_template.shape[::-1]
# We will use all six methods in order to check how they work
methods = ['cv.TM_CCOEFF', 'cv.TM_CCOEFF_NORMED', 'cv.TM_CCORR',
           'cv.TM_CCORR_NORMED', 'cv.TM_SQDIFF', 'cv.TM_SQDIFF_NORMED']
for match_method in methods:
    image = image_gray.copy()
    method = eval(match_method)
    # Here we will perform the match operation with template image
    res = cv.matchTemplate(image_rgb, img_template, method)
    minval, maxval, minloc, maxloc = cv.minMaxLoc(res)
    # When we use method as TM_SQDIFF or TM_SQDIFF_NORMED then take minimum of the metric value
    if method in [cv.TM_SQDIFF, cv.TM_SQDIFF_NORMED]:
        topleft = minloc
    else:
        topleft = maxloc
    btm_right = (topleft[0] + w, topleft[1] + h)
    cv.rectangle(image_rgb, topleft, btm_right, 255, 2)
    pltimg.subplot(121), pltimg.imshow(res, cmap='gray')
    pltimg.title('Result that matches'), pltimg.xticks([]), pltimg.yticks([])
    pltimg.subplot(122), pltimg.imshow(image_rgb, cmap='gray')
    pltimg.title('Detection Point of image'), pltimg.xticks(
        []), pltimg.yticks([])
    pltimg.suptitle(match_method)
    pltimg.show()
