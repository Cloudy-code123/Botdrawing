# Auto Paint Robot

The app offers a pencil-sketch drawing mode:

- **Pencil Sketch (Approximate)** draws the original monochrome pencil-style
  sketch on a blank Paint canvas.

Line width adjusts automatically: broad composition and fill strokes are
thicker, while fine details are thinner. Brush thickness is also estimated
from each stroke's length and complexity before it is sent to Paint.

## Requirements

- Windows with Microsoft Paint installed
- Python 3.10 or later
- The packages listed in `requirements.txt`

Install the dependencies and start the app from this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python bot.py
```

The code is organized in the `drawingbot` package: `app.py` contains the GUI,
`planning.py` analyzes images and creates strokes, `robot.py` manages drawing,
`windows.py` handles Paint and Windows input, and `config.py` holds shared
drawing settings. `bot.py` remains the app entry point.

## Using the app

The application window is named **Auto Sketch Robot** so it cannot be
mistaken for Microsoft Paint during window detection.

1. Upload a JPG, JPEG, PNG, BMP, or WebP image.
2. The **Pencil Sketch (Approximate)** mode creates a blank Paint canvas sized
   to fit the drawing and traces contours, details, texture, and tonal
   hatching. Style, speed, and quality adjust the sketch.
3. Click **Start Drawing** and confirm.

The app sizes the blank canvas and Paint window to fit the available screen
space, then detects the canvas and scales the planned strokes to fit inside it.
Appearance is approximate and the process is algorithmic, not AI generated.
Drawings are not automatically saved.
