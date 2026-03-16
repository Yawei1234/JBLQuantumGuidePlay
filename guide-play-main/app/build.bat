@REM read version txt content
@REM --onefile ^
set /p verX=<version.txt
set arg1=%1

echo creating version file
create-version-file metadata.yml ^
 --outfile version_info.txt ^
 --version %verX%

echo starting build

pyinstaller guide-play-splashed.spec