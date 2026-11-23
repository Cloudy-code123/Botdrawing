<<<<<<< HEAD
# Auto Paint Robot

The app offers two different results:

- **Open Original Image (No Drawing)** opens the uploaded file directly in
  Paint. This displays the source; it does not draw.
- **Pencil Sketch (Approximate)** uses OpenCV to produce contours, facial
  details, texture, and tonal hatching, then traces those strokes on a new,
  blank Paint canvas. It does not open the uploaded photo in Paint. It is not
  AI-based and cannot be pixel-identical to the source.

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
2. The default **Pencil Sketch (Approximate)** mode creates a blank Paint
   canvas sized to fit the drawing and traces strokes progressively. The
   uploaded photo is used only to plan the strokes. Choose **Open Original
   Image (No Drawing)** only to display the source without drawing. Style,
   speed, and quality apply to sketch mode only.
3. Click **Start Drawing** and confirm.

Sketch mode detects the blank canvas in Paint and traces the planned strokes
inside it. Appearance is approximate and the process is algorithmic, not AI
generated. Sketches are not automatically saved. The original-image mode
opens the uploaded file unchanged and does not draw.


