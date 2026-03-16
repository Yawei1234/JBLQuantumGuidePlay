pyinstaller ^
 --noconfirm ^
 --onefile ^
 --console ^
 --icon "../app/assets/app-icon.ico" ^
 --name "guide-play-services-cli" ^
 --clean ^
 --add-data "hrtf;hrtf/" ^
 --add-data "sound.py;." ^
 --add-data "Soundstage.py;." ^
 --add-data "Speakers.py;." ^
 --add-data "tracker.py;." ^
 --add-data "utils.py;." ^
 --add-data "message_server.py;." ^
 --add-data "pyttsx3;pyttsx3/"  "server.py"

@REM Create server folder if not exists
IF NOT EXIST ..\app\server mkdir ..\app\server
@REM copy the exe to the app folder and overwrite if exists
copy /Y dist\guide-play-services-cli.exe ..\app\server\guide-play-services-cli.exe