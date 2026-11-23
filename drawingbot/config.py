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

AUTO_LINE_WIDTHS = {
    0: 3,
    1: 2,
    2: 1,
    3: 1,
    4: 2,
    5: 2,
    6: 1,
}

LINE_WIDTH_RANGES = {
    0: (2, 4),
    1: (1, 3),
    2: (1, 2),
    3: (1, 2),
    4: (1, 3),
    5: (2, 4),
    6: (1, 2),
}

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
