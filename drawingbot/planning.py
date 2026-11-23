"""Image analysis and stroke-preview generation."""

import math
import random

import cv2
import numpy as np
from PIL import Image

from .config import QUALITY, STYLES


def _order_paths(paths, limit=3000):
    paths = sorted(paths, key=len, reverse=True)[:limit]
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
                result.append(approx)
    return _order_paths(result)


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

    plan[0] = _contour_paths(
        cv2.Canny(cv2.GaussianBlur(gray, (0, 0), 6), 15, 45), 40, 4.0)
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
        gray, 105, max(4, int(5 * spacing_factor)))
    plan[4] = (
        _hatch(soft, 45, 7 * spacing_factor, 205)
        + _hatch(soft, 45, 7 * spacing_factor, 165)
    )
    plan[5] = (
        _hatch(soft, 135, 5 * spacing_factor, 120)
        + _hatch(soft, 20, 4 * spacing_factor, 70)
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
    canvas = np.full((height, width, 3), 255, np.uint8)
    for _, points in strokes:
        cv2.polylines(
            canvas, [points.astype(np.int32)], False,
            (40, 40, 40), 1, cv2.LINE_AA)
    scale = min(max_size[0] / width, max_size[1] / height, 1.0)
    display_width = max(1, int(width * scale))
    display_height = max(1, int(height * scale))
    return Image.fromarray(cv2.resize(
        canvas, (display_width, display_height),
        interpolation=cv2.INTER_AREA))
