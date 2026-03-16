# GUIDE PLAY

Welcome to Guide Play — an innovative technology to help the visually impaired play games like never before.

This software leverages AI and machine learning to turn the objects and structures in the Counter-Strike 2 environment into sounds, emulating echolocation and allowing the visually impaired to perceive their spatial environment.

Guide Play is offered as a free tool, and although the use of JBL Quantum headphones enhances the experience, they are not required for gameplay.

We recommend that those with 0% vision seek assistance in setting up the program and while using it for the first time.

Find out more here: [https://jblquantumguideplay.com/](https://jblquantumguideplay.com/)

---

## Features

- **Proximity Audio** — Spatial 3D audio cues for nearby enemies and teammates using echolocation
- **Compass Direction Voice** — Real-time spoken compass direction of detected entities (North, South East, etc.)
- **In-Game Location Voice** — OCR-based map sector name announcements (e.g. "Bombsite B", "CT Start", "Middle") every 6 seconds
- **Incoming Damage Direction** — Audio indicator of the direction you are taking damage from
- **Enemy Killed** — Audio notification when an enemy is eliminated (requires score OCR)
- **AimPlus** — AI-assisted enemy alignment detection with CUDA GPU acceleration
- **In-Game Screen Reader** — Reads on-screen text via OCR to assist navigation

---

## Tech Stack

The majority of the system is based on Computer Vision and image processing obtained through screen capture. The capture is submitted to a multi-layer pipeline responsible for detecting game state, nearby friends and enemies, map location, damage direction, and more.

Key components:

| Component | Role |
|---|---|
| `pipe_radar.py` | Minimap HSV color detection for entity tracking |
| `aimPlus.py` | YOLO-based enemy detection with CUDA acceleration |
| `pipe_ocr.py` | Tesseract OCR for map location text |
| `pipe_ocr_score.py` | Score/alive count OCR for enemy killed detection |
| `pipe_lifelevel.py` | Pixel-based health detection |
| `pipe_aim_damage.py` | Incoming damage direction detection |
| `capture_WC.py` | Central capture coordinator and state router |
| `guiBeta.py` | Main application logic, TTS, and state management |
| UI (`index.html`) | pywebview frontend with Tone.js spatial audio |

Processing is GPU-intensive and runs in parallel with the game. Recommended specs: **Intel Core i7-8700, 16 GB RAM, RTX 3060 8 GB** or equivalent.

---

## Requirements

- Windows 10 / 11
- 16 GB RAM
- 8 GB GPU (NVIDIA recommended for CUDA support)
- Python 3.10+ (Miniconda/Anaconda recommended)
- CUDA Toolkit (for AimPlus GPU acceleration)
- Steam and Counter-Strike 2 (updated)
- ~20 GB disk space
- Visual Studio Code (optional, recommended)

---

## How to Start

### Dev Mode / Test Mode

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd guide-play-main
   ```

2. **Create and activate a Conda environment** (recommended over venv)
   ```bash
   conda create -n guideplay python=3.10
   conda activate guideplay
   ```

   Or using venv:
   ```bash
   python -m venv envGuidePlay
   envGuidePlay\Scripts\activate.bat
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Tesseract OCR**
   - Download from [uni-mannheim.de Tesseract index](https://digi.bib.uni-mannheim.de/tesseract/)
   - Recommended: [v5.3.0](https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-v5.3.0.20221214.exe)
   - Extract into `.\app\tesseract\`

5. **Build the TTS/OSC service**
   ```bash
   cd osc_tts_server
   build.bat
   cd ..\app
   python -m pip install pynput
   ```

6. **Run as Administrator** (required for screen capture via dxcam)
   ```bash
   # In an Administrator terminal:
   python guiBeta.py --dev 1 --prod 0   # dev mode
   python guiBeta.py                     # test mode
   ```

   Or in VS Code: open `guiBeta.py` and select **"Debug using launch.json"** from the Run menu.

> **Note:** The application must be run as Administrator for dxcam screen capture to function correctly.

### Prod Mode / Build

```bash
build.bat
# Run the output: .\app\dist\guide-play.exe
```

---

## Configuration

Settings are stored in `app/config.json`. Key options:

| Setting | Description |
|---|---|
| `InGameSectorVoice` | Enable map location announcements (on/off) |
| `IncomingDamageDirection` → `DamageDirectionAlerts` | Enable damage direction audio (on/off) |
| `ScreenReader` → `InGameSectorVoice` | Enable in-game OCR text reading (on/off) |
| `AimPlus` | AI enemy alignment detection (on/off) |

---

## Third Party

- OpenCV
- PyTorch (with CUDA support)
- Tesseract / pytesseract
- Ultralytics (YOLO)
- pywebview
- Tone.js (spatial audio)
- python-osc
- dxcam
- pydub / ffmpeg
- pygame
- UltraDict
- scipy
- and more (see `thirdparty.txt`)

---

## Contribution

Feel free to collaborate and provide feedback or ask questions about any subject related to the project.

Sinta-se livre para colaborar e fornecer feedback ou tirar dúvidas sobre qualquer assunto relacionado ao projeto.
