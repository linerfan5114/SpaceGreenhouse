"""
test_vision.py - Unit tests for the health-metric heuristic.
Run with: pytest tests/
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vision import compute_health_metrics  # noqa: E402


def solid_color_image(rgb, size=100):
    img = np.zeros((size, size, 3), dtype=np.uint8)
    img[:, :] = rgb
    return img


def test_pure_green_scores_high():
    img = solid_color_image([40, 160, 60])
    metrics = compute_health_metrics(img)
    assert metrics.green_pct > 90
    assert metrics.health_score > 80


def test_pure_brown_scores_low():
    img = solid_color_image([110, 70, 30])
    metrics = compute_health_metrics(img)
    assert metrics.brown_pct > 50
    assert metrics.health_score < 30


def test_background_only_image_has_zero_plant_fraction():
    # Very dark, low-saturation "background" should not be classified
    # as plant tissue at all.
    img = solid_color_image([10, 10, 10])
    metrics = compute_health_metrics(img)
    assert metrics.plant_pixel_fraction == 0.0
    assert metrics.health_score == 0.0


def test_yellowing_scores_between_green_and_brown():
    green_img = solid_color_image([40, 160, 60])
    yellow_img = solid_color_image([190, 180, 40])
    brown_img = solid_color_image([110, 70, 30])

    green_score = compute_health_metrics(green_img).health_score
    yellow_score = compute_health_metrics(yellow_img).health_score
    brown_score = compute_health_metrics(brown_img).health_score

    assert brown_score < yellow_score < green_score
