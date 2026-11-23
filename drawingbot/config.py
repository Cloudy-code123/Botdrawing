"""Shared drawing settings and labels."""

STAGES = [
    "Composition",
    "Outlines",
    "Facial Details",
    "Hair & Texture",
    "Light Shading",
    "Dark Shading",
    "Final Details",
]

STYLES = {
    "Realistic Pencil Portrait": [0, 1, 2, 3, 4, 5, 6],
    "Light Sketch":              [0, 1, 2, 4, 6],
    "Contour Drawing":           [0, 1, 2, 6],
}

SPEEDS = {
    "Normal":  (3, (0.006, 0.012), (0.01, 0.04)),
    "Fast":    (4, (0.004, 0.008), (0.0,  0.01)),
    "Slow":    (2, (0.012, 0.020), (0.03, 0.12)),
}

QUALITY = {
    "Draft":    (420, 1.6),
    "Standard": (600, 1.2),
    "High":     (800, 1.0),
}

EXACT_IMAGE_MODE = "Open Original Image (No Drawing)"
SKETCH_MODE = "Pencil Sketch (Approximate)"
