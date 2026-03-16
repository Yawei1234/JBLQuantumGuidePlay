from PIL import ImageColor
import json
import os
import cv2
from svgpathtools import svg2paths2
from matplotlib import colors


def listTemplates(folder):
    files = []
    for filename in os.listdir(folder):
        if filename.endswith('.svg'):
            if 'debug' in filename:
                continue
            files.append(filename)
    return files


def rgbToBGR(rgb):
    # split rgb string into list
    if 'rgb(' in rgb:
        rgb = rgb.replace('rgb(', '').replace(')', '')
        rgb = rgb.split(',')
        # iterate rgb list
        for i in range(len(rgb)):
            # remove leading and trailing whitespaces
            rgb[i] = rgb[i].strip()
        # create new rgb string
        new_rgb = [rgb[2], rgb[1], rgb[0]]
        return new_rgb
    else:
        # check if # is in rgb string
        if '#' in rgb:
            # rgb = rgb.replace('#', '')
            color = ImageColor.getcolor(rgb, "RGB")
            # convert color to bgr
            # rgb = color
            return [color[2], color[1], color[0]]
        else:
            rgba = colors.to_rgba(rgb)
            r = int(rgba[0]*255)
            g = int(rgba[1]*255)
            b = int(rgba[2]*255)
            return [b, g, r]


def parseInts(attributes):
    for attr in attributes:
        for key in attr.keys():
            if key == 'data-name':
                attr['id'] = attr[key]
            if key == 'style':
                # split style string into list
                style = attr[key].split(';')
                newObj = {}
                # iterate style list
                for s in style:
                    # split style list into key value pair
                    s = s.split(':')
                    # iterate key value pair
                    for i in range(len(s)):
                        # print("S", s[i])
                        if s[i] == 'fill' or s[i] == 'stroke':
                            val = s[i+1]
                            # remove leading and trailing whitespaces
                            val = val.strip()
                            if s[i+1] == 'none':
                                val = 'transparent'
                            else:
                                newObj[s[i]] = rgbToBGR(val)

                        # create new key value pair
                        # if len(s) == 2:
                        #     new_key = s[0]
                        #     new_value = s[1]
                        #     if new_key is not None and new_value is not None:
                        #         attr[new_key] = new_value
                        # remove leading and trailing whitespaces
                attr[key] = newObj

            if key == 'x' or key == 'y':
                attr[key] = float(attr[key])
                # round to 1 decimal places~
                attr[key] = round(attr[key])
            if key == 'width' or key == 'height':
                attr[key] = float(attr[key])
                # round to 1 decimal places~
                attr[key] = round(attr[key])
    return attributes


def parseTemplates(svgTemplates, path='assets/gamestates_ref/'):

    finalFiles = []
    # iterate svgTemplates
    for svg in svgTemplates:
        # parse svg
        paths, attributes, svg_attributes = svg2paths2(
            path + svg)
        # parse attributes
        treated = parseInts(attributes)
        name = svg.replace('.svg', '')
        # append parsed svg to parsedTemplates
        # find trated with id == name
        idFound = next(
            (index for (index, d) in enumerate(treated) if d["id"] == name), None)
        info = {
            "id": name,
            "width": 0,
            "height": 0
        }
        if idFound is not None:
            info = treated[idFound]

        # filter out the svg with id == name
        treated = list(filter(lambda x: x["id"] != name, treated))

        # iterate and apply default values
        for element in treated:
            if 'weight' not in element:
                element['weight'] = 1

            if 'GO' in element['id'] or 'Play' in element['id']:
                element['weight'] = 50
            # if x not exist
            if 'x' not in element:
                element['x'] = 0
            # if y not exist
            if 'y' not in element:
                element['y'] = 0
            # if width not exist
            if 'width' not in element:
                # remove element
                treated.remove(element)
            # if height not exist
            if 'height' not in element:
                # remove element
                treated.remove(element)

        finalFiles.append({
            "name": name,
            "image": ""+name+".png",
            "id": info["id"],
            "width": info["width"],
            "height": info["height"],
            "elements": treated
        })
    return finalFiles


# svgTemplates = listTemplates('assets/gamestates_ref')
# parsedTemplates = parseTemplates(svgTemplates, 'assets/gamestates_ref')

# currentId = 0
# maxId = len(parsedTemplates)

# while True:

#     img = cv2.imread('assets/gamestates_ref/' +
#                      parsedTemplates[currentId]['image'])
#     cv2.namedWindow('image', cv2.WINDOW_NORMAL)
#     cv2.resizeWindow(
#         'image', parsedTemplates[currentId]['width'], parsedTemplates[currentId]['height'])

#     for element in parsedTemplates[currentId]['elements']:
#         if 'fill' in element['style']:
#             fill = element['style']['fill']
#             if fill != 'transparent':
#                 color = (int(element['style']['fill'][0]), int(element['style']
#                          ['fill'][1]), int(element['style']['fill'][2]))
#                 x1 = int(element['x'])
#                 y1 = int(element['y'])
#                 x2 = int(element['x'])+int(element['width'])
#                 y2 = int(element['y'])+int(element['height'])

#                 center = (x1 + int(element['width']) //
#                           2, y1 + int(element['height']) // 2)
#                 # put text
#                 font = cv2.FONT_HERSHEY_SIMPLEX

#                 cv2.rectangle(img, (x1, y1), (x2, y2), color, -1)

#                 cv2.putText(img, element['id'], center,
#                             font, 0.4, (0, 0, 0), 1, 1)

#     cv2.imshow('image', img)
#     # if key press q break
#     if cv2.waitKey(1) & 0xFF == ord('q'):
#         break
#     # if key press n next
#     if cv2.waitKey(1) & 0xFF == ord('n'):
#         if currentId < maxId-1:
#             currentId += 1
#         else:
#             currentId = 0
