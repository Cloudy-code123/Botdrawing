"""Image analysis and stroke-preview generation."""

import math
import random

import cv2
import numpy as np
from PIL import Image

from .config import (
    AUTO_LINE_WIDTHS,
    LINE_WIDTH_RANGES,
    QUALITY,
    STYLES,
)


def adaptive_line_width(stage, points, image_width, image_height):
    """Estimate a Paint brush size from the stroke length and drawing stage."""
    if points is None or len(points) < 2:
        return AUTO_LINE_WIDTHS[stage]

    points = np.asarray(points, dtype=np.float32)
    segments = np.diff(points, axis=0)
    segment_lengths = np.linalg.norm(segments, axis=1)
    path_length = float(np.sum(segment_lengths))
    if path_length <= 0:
        return AUTO_LINE_WIDTHS[stage]

    diagonal = math.hypot(image_width, image_height)
    normalized_length = path_length / max(diagonal, 1.0)
    median_segment = float(np.median(segment_lengths))
    normalized_segment = median_segment / max(diagonal, 1.0)
    bounds = np.ptp(points, axis=0)
    bounding_span = max(float(np.linalg.norm(bounds)), 1.0)
    complexity = path_length / bounding_span

    if (normalized_length < 0.018
            or normalized_segment < 0.002
            or complexity < 1.08):
        adjustment = -1
    elif (normalized_length > 0.12
            or normalized_segment > 0.018
            or complexity > 2.5):
        adjustment = 1
    else:
        adjustment = 0

    minimum, maximum = LINE_WIDTH_RANGES[stage]
    width = min(maximum, max(
        minimum, AUTO_LINE_WIDTHS[stage] + adjustment))
    return width


def _order_paths(paths, limit=3000):
    paths = sorted(paths, key=len, reverse=True)[:limit]
    if not paths:
        return []
    cleaned = []
    for path in paths:
        path = np.asarray(path, dtype=np.float64)
        if len(path) >= 2:
            keep = np.r_[True, np.linalg.norm(
                np.diff(path, axis=0), axis=1) >= 0.8]
            path = path[keep]
            if len(path) >= 2:
                cleaned.append(path)
    paths = cleaned
    if not paths:
        return []
    starts = np.array([p[0] for p in paths], float)
    ends = np.array([p[-1] for p in paths], float)
    used = np.zeros(len(paths), bool)
    cur = np.array([0.0, 0.0])
    out = []
    for _ in range(len(paths)):
        ds = np.linalg.norm(starts - cur, axis=1)
        de = np.linalg.norm(ends - cur, axis=1)
        ds[used] = de[used] = 1e18
        i = int(np.argmin(np.minimum(ds, de)))
        path = paths[i] if ds[i] <= de[i] else paths[i][::-1]
        used[i] = True
        cur = path[-1].astype(float)
        out.append(path.astype(float))
    return out


def _contour_paths(edges, min_len, eps):
    contours, _ = cv2.findContours(
        edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    result = []
    for contour in contours:
        if len(contour) >= min_len:
            approx = cv2.approxPolyDP(
                contour, eps, False).reshape(-1, 2)
            if len(approx) >= 2:
                result.append(_smooth_path(approx, iterations=2))
    return _order_paths(result)


def _smooth_path(points, iterations=2):
    """Smooth noisy edges while keeping their overall shape."""
    points = np.asarray(points, dtype=np.float32)
    if len(points) < 3:
        return points.astype(np.float64)

    points = cv2.approxPolyDP(
        points.reshape(-1, 1, 2), 0.7, False
    ).reshape(-1, 2)
    if len(points) < 3:
        return points.astype(np.float64)

    for _ in range(iterations):
        smoothed = [points[0]]
        for start, end in zip(points[:-1], points[1:]):
            smoothed.append(start * 0.75 + end * 0.25)
            smoothed.append(start * 0.25 + end * 0.75)
        smoothed.append(points[-1])
        points = np.asarray(smoothed, dtype=np.float32)
    return points.astype(np.float64)


def _hatch(gray, angle, spacing, threshold):
    height, width = gray.shape
    radians = math.radians(angle)
    direction = np.array([math.cos(radians), math.sin(radians)])
    normal = np.array([-direction[1], direction[0]])
    diagonal = int(math.hypot(height, width))
    ts = np.arange(-diagonal / 2, diagonal / 2, 1.0)
    centre = np.array([width / 2, height / 2])
    strokes, offset, flip = [], -diagonal / 2, False
    while offset < diagonal / 2:
        points = centre + normal * offset + ts[:, None] * direction
        xi = points[:, 0].round().astype(int)
        yi = points[:, 1].round().astype(int)
        inside = (xi >= 0) & (xi < width) & (yi >= 0) & (yi < height)
        dark = np.zeros(len(ts), np.int8)
        dark[inside] = gray[yi[inside], xi[inside]] < threshold
        indices = np.flatnonzero(
            np.diff(np.concatenate(([0], dark, [0]))))
        for start, end in zip(indices[::2], indices[1::2]):
            current = start
            while current < end:
                next_point = min(end, current + random.randint(18, 40))
                if next_point - current >= 4:
                    segment = points[[current, next_point - 1]]
                    strokes.append(segment[::-1] if flip else segment)
                if next_point >= end:
                    break
                current = next_point - 2
        flip = not flip
        offset += spacing * random.uniform(0.8, 1.2)
    return strokes


def _hair_strokes(gray, threshold, step):
    blurred = np.float32(cv2.GaussianBlur(gray, (0, 0), 2))
    gx = cv2.GaussianBlur(
        cv2.Sobel(blurred, cv2.CV_32F, 1, 0), (0, 0), 4)
    gy = cv2.GaussianBlur(
        cv2.Sobel(blurred, cv2.CV_32F, 0, 1), (0, 0), 4)
    height, width = gray.shape
    result = []
    for y in range(0, height, step):
        for x in range(0, width, step):
            if gray[y, x] >= threshold:
                continue
            px = x + random.uniform(-1, 1) * step / 2
            py = y + random.uniform(-1, 1) * step / 2
            points = [(px, py)]
            for _ in range(random.randint(3, 6)):
                xi = int(min(max(px, 0), width - 1))
                yi = int(min(max(py, 0), height - 1))
                angle = math.atan2(gy[yi, xi], gx[yi, xi]) + math.pi / 2
                px += 3 * math.cos(angle)
                py += 3 * math.sin(angle)
                points.append((px, py))
            result.append(np.array(points))
    random.shuffle(result)
    return result


def plan_drawing(path, style, quality):
    """Return the planned strokes and the analysis image dimensions."""
    max_dimension, spacing_factor = QUALITY[quality]
    image = cv2.imread(path)
    if image is None:
        raise ValueError(f"Cannot read image: {path}")
    height, width = image.shape[:2]
    scale = max_dimension / max(height, width)
    image = cv2.resize(
        image, (int(width * scale), int(height * scale)),
        interpolation=cv2.INTER_AREA)
    gray = cv2.createCLAHE(2.0, (8, 8)).apply(
        cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
    height, width = gray.shape
    soft = cv2.GaussianBlur(gray, (0, 0), 1.2)
    enabled_stages = STYLES[style]
    plan = {}

    clean_edges = cv2.morphologyEx(
        cv2.Canny(cv2.GaussianBlur(gray, (0, 0), 6), 15, 45),
        cv2.MORPH_CLOSE,
        np.ones((3, 3), dtype=np.uint8),
    )
    plan[0] = _contour_paths(
        clean_edges, 55, 5.0)
    plan[1] = _contour_paths(cv2.Canny(soft, 50, 130), 25, 2.0)

    face_edges = []
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = cascade.detectMultiScale(
        gray, 1.1, 5, minSize=(width // 8, height // 8))
    if len(faces):
        mask = np.zeros_like(gray)
        for (face_x, face_y, face_width, face_height) in faces:
            mask[face_y:face_y + face_height,
                 face_x:face_x + face_width] = 255
        fine = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 35, 100)
        face_edges = _contour_paths(cv2.bitwise_and(fine, mask), 8, 1.0)
    plan[2] = face_edges

    plan[3] = _hair_strokes(
        gray, 105, max(6, int(7 * spacing_factor)))
    plan[4] = (
        _hatch(soft, 45, 9 * spacing_factor, 195)
        + _hatch(soft, 135, 11 * spacing_factor, 155)
    )
    plan[5] = (
        _hatch(soft, 135, 7 * spacing_factor, 115)
        + _hatch(soft, 20, 6 * spacing_factor, 65)
    )
    plan[6] = _contour_paths(cv2.Canny(gray, 90, 190), 25, 1.5)

    strokes = [
        (stage, points)
        for stage in range(7)
        if stage in enabled_stages
        for points in plan.get(stage, [])
        if len(points) >= 2
    ]
    return strokes, (width, height)


def render_preview(strokes, width, height, max_size=(500, 320)):
    scale = min(max_size[0] / width, max_size[1] / height, 1.0)
    display_width = max(1, int(width * scale))
    display_height = max(1, int(height * scale))
    canvas = np.full((display_height, display_width, 3), 255, np.uint8)
    for stroke in strokes:
        stage, points = stroke
        thickness = max(
            1,
            int(round(adaptive_line_width(
                stage, points, width, height) * scale)),
        )
        preview_points = np.rint(points * scale).astype(np.int32)
        cv2.polylines(
            canvas, [preview_points], False,
            (40, 40, 40), thickness, cv2.LINE_AA)
    return Image.fromarray(canvas)
