"""
Geometric utilities for local coordinates, polylines, and projections.
Origin: lat = 12.9716, lon = 77.5946 (fictional campus center)
"""
from __future__ import annotations
import math
from typing import Sequence

# Approximate meters per degree around 12.9716° N
ORIGIN_LAT = 12.9716
ORIGIN_LON = 77.5946
METERS_PER_DEG_LAT = 111320.0
METERS_PER_DEG_LON = 111320.0 * math.cos(math.radians(ORIGIN_LAT))


def xy_to_latlon(x: float, y: float, origin_lat: float = ORIGIN_LAT, origin_lon: float = ORIGIN_LON) -> tuple[float, float]:
    """Convert metric (x, y) relative to origin into (lat, lon)."""
    lat = origin_lat + (y / METERS_PER_DEG_LAT)
    lon = origin_lon + (x / METERS_PER_DEG_LON)
    return round(lat, 6), round(lon, 6)


def latlon_to_xy(lat: float, lon: float, origin_lat: float = ORIGIN_LAT, origin_lon: float = ORIGIN_LON) -> tuple[float, float]:
    """Convert (lat, lon) to metric (x, y) relative to origin in meters."""
    y = (lat - origin_lat) * METERS_PER_DEG_LAT
    x = (lon - origin_lon) * METERS_PER_DEG_LON
    return round(x, 2), round(y, 2)


def euclidean_dist(p1: Sequence[float], p2: Sequence[float]) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def polyline_length(polyline: Sequence[Sequence[float]]) -> float:
    if len(polyline) < 2:
        return 0.0
    total = 0.0
    for i in range(len(polyline) - 1):
        total += euclidean_dist(polyline[i], polyline[i + 1])
    return total


def project_point_to_segment(p: Sequence[float], a: Sequence[float], b: Sequence[float]) -> tuple[tuple[float, float], float, float]:
    """
    Project point p onto segment ab.
    Returns (closest_point, distance, segment_fraction_t)
    """
    px, py = p[0], p[1]
    ax, ay = a[0], a[1]
    bx, by = b[0], b[1]
    dx = bx - ax
    dy = by - ay
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq == 0:
        dist = math.hypot(px - ax, py - ay)
        return (ax, ay), dist, 0.0

    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg_len_sq))
    proj_x = ax + t * dx
    proj_y = ay + t * dy
    dist = math.hypot(px - proj_x, py - proj_y)
    return (proj_x, proj_y), dist, t


def project_point_to_polyline(p: Sequence[float], polyline: Sequence[Sequence[float]]) -> tuple[float, float]:
    """
    Project point p onto a polyline.
    Returns (cumulative_progress_s, distance_to_polyline).
    """
    if len(polyline) < 2:
        return 0.0, euclidean_dist(p, polyline[0]) if polyline else 0.0

    best_dist = float("inf")
    best_progress = 0.0
    cum_dist = 0.0

    for i in range(len(polyline) - 1):
        a = polyline[i]
        b = polyline[i + 1]
        seg_len = euclidean_dist(a, b)
        _, dist, t = project_point_to_segment(p, a, b)
        if dist < best_dist:
            best_dist = dist
            best_progress = cum_dist + t * seg_len
        cum_dist += seg_len

    return best_progress, best_dist
