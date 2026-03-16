#

# C:\Program Files (x86)\Steam\config\libraryfolders.vdf"
# C:\Program Files (x86)\Steam\userdata\920322189\config\localconfig.vdf


# steam protocol schema
# Computador\HKEY_CLASSES_ROOT\steam\Shell\Open\Command
# Computador\HKEY_CLASSES_ROOT\steamlink\Shell\Open\Command
# Computador\HKEY_CURRENT_USER\Software\Classes\steam\Shell\Open\Command
# Computador\HKEY_CURRENT_USER\Software\Classes\steamlink\Shell\Open\Command

# autoexec.cfg
# E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo\cfg\autoexec.cfg
from pathlib import Path
import re
import chardet
import win32con
import win32gui
import winreg
import subprocess
import time
import shutil
import os
import vdf

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'extraLibs'))
from valve_keyvalues_python.keyvalues import KeyValues

DIRPATH = os.path.join(os.path.dirname(__file__))


class WindowMgr:
    def __init__(self):
        self._handle = None

    def find_window(self, class_name, window_name=None):
        self._handle = win32gui.FindWindow(class_name, window_name)

    def _window_enum_callback(self, hwnd, wildcard):
        if re.match(wildcard, str(win32gui.GetWindowText(hwnd))) is not None:
            self._handle = hwnd

    def find_window_wildcard(self, wildcard):
        self._handle = None
        win32gui.EnumWindows(self._window_enum_callback, wildcard)

    def set_foreground(self):
        try:
            win32gui.ShowWindow(self._handle, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self._handle)
        except Exception as e:
            print("Error setting foreground", e)

    def minimize(self):
        win32gui.ShowWindow(self._handle, win32con.SW_MINIMIZE)

    def minimize_by_wildcard(self, wildcard):
        self.find_window_wildcard(wildcard)
        if self._handle is not None:
            self.minimize()

    def focus_by_wildcard(self, wildcard):
        self.find_window_wildcard(wildcard)
        if self._handle is not None:
            self.set_foreground()


class SteamHacks:
    def __init__(self, parentRef=None):
        self.steam_path = self.find_steam_path()
        self.libraryfolders_vdf_path = self.find_libraryfolders_vdf()
        self.libraryfolders_vdf_data = self.read_libraryfolders_vdf()
        self.localconfig_vdf_path = self.find_localconfig_vdf()
        self.parentRef = parentRef
        self.windowMgr = WindowMgr()

    def minimize_steam(self):
        self.windowMgr.minimize_by_wildcard(".*Steam.*")

    def focus_guideplay(self):
        try:
            self.windowMgr.focus_by_wildcard(".*Guide Play.*")
        except Exception as e:
            print("Error focusing Guide Play", e)

    def focus_cs2(self):
        self.windowMgr.focus_by_wildcard(".*Counter-Strike 2*")

    def check_if_steam_is_running(self):
        self.windowMgr.find_window_wildcard(".*Steam.*")
        if self.windowMgr._handle is not None:
            return True
        return False

    def find_localconfig_vdf(self):
        if not self.steam_path:
            return None
        userdata_path = os.path.join(self.steam_path, "userdata")
        if os.path.isdir(userdata_path):
            for account_dir in os.listdir(userdata_path):
                localconfig_path = os.path.join(
                    userdata_path, account_dir, "config", "localconfig.vdf")
                if os.path.isfile(localconfig_path):
                    return localconfig_path

        for root, dirs, files in os.walk(self.steam_path):
            for file in files:
                if file == "localconfig.vdf":
                    return os.path.join(root, file)
        return None

    def update_localconfig_vdf(self, data):
        with open(self.localconfig_vdf_path, "w", encoding="utf-8") as f:
            vdf.dump(data, f)

    def predict_encoding(self, file_path: Path, n_lines: int = 20) -> str:
        '''Predict a file's encoding using chardet'''
        rawdata = ""
        # Open the file as binary data
        with Path(file_path).open('rb') as f:
            # Join binary lines for specified number of lines
            if n_lines > 0:
                rawdata = b''.join([f.readline() for _ in range(n_lines)])
            else:
                rawdata = f.read()

        return chardet.detect(rawdata)['encoding'], rawdata

    def parse_localconfig_vdf(self, folder=None):

        try:
            # data = vdf.load(
            #     open(self.localconfig_vdf_path,  "r", encoding="utf8").read())
            # dataParsed = vdf.parse(
            #     open(self.localconfig_vdf_path,  "r", encoding="utf8").read())
            data = None
            dataParsed = None
            encoding = "utf-8"
            realPath = self.localconfig_vdf_path
            if folder is not None:
                realPath = os.path.join(DIRPATH, folder)
                encoding, content = self.predict_encoding(realPath, -1)
                print("parse_localconfig_vdf - TESTING_PATH", encoding, realPath)
                print("parse_localconfig_vdf - TESTING_CONTENT", content)

            kv = KeyValues(filename=realPath, encoding=encoding)
            data = kv
            dataParsed = kv.dump()
            print("parse_localconfig_vdf - TESTING",
                  len(data), len(dataParsed))
            return data, dataParsed
        except Exception as e:
            print("Error parsing localconfig.vdf", e,
                  realPath)

            data = None
            dataParsed = None
            print("parse_localconfig_vdf - ERROR", data, dataParsed)
            return data, dataParsed

    def find_steam_path(self, devMode=True):
        result = None

        if devMode:
            result = r"C:\Program Files (x86)\Steam"
            return result
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Valve\\Steam") as key:
                result = winreg.QueryValueEx(key, "InstallPath")[0]
        except FileNotFoundError:
            pass

        if result is None:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\Valve\\Steam") as key:
                    result = winreg.QueryValueEx(key, "InstallPath")[0]
            except FileNotFoundError:
                pass
        if result is None:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Valve\\Steam") as key:
                    result = winreg.QueryValueEx(key, "SteamPath")[0]
            except FileNotFoundError:
                pass
        if result is None:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\WOW6432Node\\Valve\\Steam") as key:
                    result = winreg.QueryValueEx(key, "SteamPath")[0]
            except FileNotFoundError:
                pass
        if result is None:
            # get path by url protocol
            try:
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "steam") as key:
                    result = winreg.QueryValueEx(key, "")[0].split('"')[1]
            except FileNotFoundError:
                pass
        if result is None:
            try:
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "steamlink") as key:
                    result = winreg.QueryValueEx(key, "")[0].split('"')[1]
            except FileNotFoundError:
                pass

        return result

    def find_libraryfolders_vdf(self):
        if not self.steam_path:
            return None
        known_paths = [
            os.path.join(self.steam_path, "steamapps", "libraryfolders.vdf"),
            os.path.join(self.steam_path, "config", "libraryfolders.vdf"),
        ]
        for candidate in known_paths:
            if os.path.isfile(candidate):
                return candidate

        for root, dirs, files in os.walk(self.steam_path):
            for file in files:
                if file == "libraryfolders.vdf":
                    return os.path.join(root, file)
        return None

    def parse_libraryfolders_vdf(self):
        try:
            # data = vdf.load(
            #     open(self.libraryfolders_vdf_path,  "r", encoding="utf8").read())
            # dataParsed = vdf.parse(
            #     open(self.libraryfolders_vdf_path,  "r", encoding="utf8").read())
            data = None
            dataParsed = None

            kv = KeyValues(filename=self.libraryfolders_vdf_path)
            data = kv
            dataParsed = kv.dump()
        except Exception as e:
            print("Error parsing libraryfolders.vdf", e,
                  self.libraryfolders_vdf_path)
            data = None
            dataParsed = None

        return data, dataParsed

    def read_libraryfolders_vdf(self):
        with open(self.libraryfolders_vdf_path, "r") as f:
            data = vdf.load(f)

    def restart_steam(self):
        done = False
        try:
            subprocess.run("taskkill /IM steam.exe /F",
                           shell=True, close_fds=True)
            time.sleep(2)
            steam_exe_path = os.path.join(self.steam_path, "steam.exe")
            os.startfile(
                steam_exe_path, arguments="-vgui -silent -nochatui -nofriendsui -no-browser -no-dwrite -no-cef-sandbox -no-dwrite")
            done = True
            print("steam restarted mode 1")
        except Exception as e:
            print("Error restarting steam 1", e)

        if not done:
            try:
                os.startfile(
                    "steam://open/main?vgui=1&silent=1&nochatui=1&nofriendsui=1&no-browser=1&no-dwrite=1&no-cef-sandbox=1&no-dwrite=1")
                done = True
                print("steam restarted mode 2")
            except Exception as e:
                print("Error restarting steam 2", e)
        return done

    def find_app_by_id(self, app_id):
        for root, dirs, files in os.walk(self.steam_path):
            for file in files:
                if file == "appmanifest_{}.acf".format(app_id):
                    return os.path.join(root, file)
        return None

    def change_libraryfolders_vdf(self, new_library_path):
        self.libraryfolders_vdf_data["LibraryFolders"]["1"] = new_library_path
        with open(self.libraryfolders_vdf_path, "w", encoding="utf-8") as f:
            vdf.dump(self.libraryfolders_vdf_data, f)

    def find_cs2_path(self):
        res, res2 = self.parse_libraryfolders_vdf()
        found = None
        for i in range(0, 100):
            try:
                folder = res['libraryfolders'][str(i)]
                try:
                    cs2 = folder['apps']['730']
                    # print(folder)
                    if cs2 is not None:
                        print(cs2)
                        found = folder['path']
                        break
                except Exception as e:
                    # print("error", e)
                    pass
            except KeyError:
                pass
            print(i, )
        return found

    def update_autoexec(self, cs2path, data, version="starter"):
        # ref - E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo\cfg\autoexec.cfg
        done = False
        try:
            finalpath = os.path.join(cs2path, "steamapps", "common",
                                     "Counter-Strike Global Offensive", "game", "csgo", "cfg", "autoexec.cfg")

            # check if file exists
            if not os.path.exists(finalpath):
                with open(finalpath, "w") as f:
                    f.write(data)
                done = True
                print("autoexec-creating-firsttime")
                return done
            else:
                # if file exists, check if it is the same version
                with open(finalpath, "r") as f:
                    current = f.read()
                    # split "["
                    # split "]"
                    try:
                        oldVersion = current.split("[")[1].split("]")[0]
                    except IndexError:
                        oldVersion = "starter"
                    print("autoexec-oldVersion", oldVersion)
                if oldVersion == version:
                    done = True
                    print("autoexec-unnecessary-update")
                    return done
                else:
                    with open(finalpath, "w") as f:
                        f.write(data)
                    print("autoexec-updated")
                    done = True
                    return done

        except Exception as e:
            print("autoexec-Error updating autoexec.cfg", e)
        return done


steam = SteamHacks()
# print(steam.find_steam_path())
# print(steam.find_libraryfolders_vdf())
# print(steam.find_cs2_path())
# kv, parsed = steam.parse_localconfig_vdf('localconfig_alien.vdf')
# print("teste\n\n\n", kv)


# print(res['libraryfolders']['0'])

# teste = steam.predict_encoding(os.path.join(
#     DIRPATH, 'localconfig_alien.vdf'), 500)
# print(teste)
