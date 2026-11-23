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

Sketch mode detects the blank canvas in Paint and traces the planned strokes
inside it. Appearance is approximate and the process is algorithmic, not AI
generated. Sketches are not automatically saved. The original-image mode
opens the uploaded file unchanged and does not draw.

## Controls and safety

- **Pause / Resume**: use the app buttons or press **Space** while sketching.
- **Stop**: press **Esc** or use the app's STOP button.
- **Emergency stop**: move the mouse to a screen corner to trigger PyAutoGUI's
  fail-safe. The mouse button is released when the drawing thread exits.
- If Paint loses focus during sketch mode, drawing pauses to avoid sending
  strokes to another window. If you inspect the app preview, use **Resume** to
  bring Paint back and continue, or switch to Paint and press **Space**.
- Closing the app requests a safe stop and waits for the drawing thread to
  release the mouse before exiting.
- Keep Paint unobstructed while a sketch is being drawn.

## Drawing options

- **Realistic Pencil Portrait**: contours, face-region detail, texture, and
  tonal hatching.
- **Light Sketch**: lighter shading with contours and details.
- **Contour Drawing**: primarily outlines and selected details.
- **Slow / Normal / Fast**: adjust mouse movement and pauses between strokes.
- **Draft / Standard / High**: set the maximum analysis image dimension and
  texture spacing. Higher quality can take longer to plan and draw.
=======
