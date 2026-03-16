# GUIDE PLAY

Welcome to Guide Play an innovative technology to help the visually impaired play games like never before.

This software leverages AI and machine learning to turn the objects and structures in the Counter-Strike 2 environment into sounds, emulating echolocation and allowing the visually impaired to perceive their spatial environment.

Guide Play is offered as a free tool, and although the use of JBL Quantum headphones enhances the experience, they are not required for gameplay.

We recommend that those who with 0% vision seek assistance insetting up the program and while using it for the first time.

Find out more here: [https://jblquantumguideplay.com/](https://jblquantumguideplay.com/)

### **TECH STACK**

The majority of the system is based on Computer Vision and image processing obtained through screen capture. The capture is then submitted to a pipeline with several layers responsible for capturing the Gamestate and some fundamental elements to enable the player to access the game menu, settings, start of the match, and gameplay. Currently, the system is prepared to detect entities such as nearby friends, nearby enemies, objects, bombs, navigation in the environment, and direction of damage.

The processing is quite intense in parallel to the cost of the game running in real-time. For better performance, we recommend a setup of **Intel Core i7, 8700, 16 GB RAM RTX 3060 8GB** or equivalent.

# REQUIREMENTS

- Windows 11
- 16gb RAM
- 8GB GPU
- Python 3.8>
- Steam and Counter-Strike 2 updated
- 20 gb disk space
- Visual Studio Code (optional / recommended)

# HOW TO START

- **DEV MODE / TEST MODE**
  - clone the repository
  - cd into the directory
  - create virtual env and activate (use the name "envGuidePlay" for convinience)
    - `python -m venv envGuidePlay`
    - `envGuidePlay\Scripts\activate.bat`
  - install requirements
    - `pip install -r requirements.txt`
  - download tesseract binaries
    - go to [Index of /tesseract (uni-mannheim.de)](https://digi.bib.uni-mannheim.de/tesseract/)
    - download the latest version ([5.3.0](https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-v5.3.0.20221214.exe))
    - extract the files on `.\app\tesseract`
  - build guide-play-services-cli.exe
    - `cd osc_tts_server`
    - `build.bat`
    - `cd ..\app`
    - `python -m pip install pynput`
  - start guiBeta.py
    - python cli dev mode
      - `python guiBeta.py --dev 1 --prod 0`
    - python cli test mode
      - `python guiBeta.py`
    - vscode dev and debug mode
      - Open the `guiBeta.py` file on vscode
      - find the Run icon on top right side and select "_Debug using launch.json_"
- **PROD MODE / BUILD**
  - Run `build.bat`
  - Run the .exe in `.\app\dist\guide-play.exe`

# Third Party

- OpenCV
- scipy
- Pytorch
- Tesseract
- Ultralytics
- SurroundPy
- pywebview
- pygame
- OSC protocol
- Ultradict
- ffmpeg
- pydub
- and a lot of other helpers (thirdparty.txt)

# Contribution

Feel free to collaborate and provide feedback or ask questions about any subject related to the project.Sinta-se livre para colaborar e fornecer feedback ou tirar dúvidas sobre qualquer assunto relacionado ao projet
