import logging
import os
import ctypes.wintypes

CSIDL_PERSONAL = 5       # My Documents
SHGFP_TYPE_CURRENT = 0   # Get current, not default value
pathBUF = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
ctypes.windll.shell32.SHGetFolderPathW(
    None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, pathBUF)

documentsPath = pathBUF.value

logPath = os.path.join(documentsPath, "guideplay_logs.log")

# check if logs folder exist else make folder
# if not os.path.isdir("logs"):
#     os.mkdir("logs")

# write log file to local system + Format options
logging.basicConfig(filename=logPath, level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger(__name__)
