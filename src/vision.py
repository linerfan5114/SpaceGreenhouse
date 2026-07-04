"""
vision.py - Plant health estimation from a single RGB photo, using
classic HSV color thresholding.

IMPORTANT - what this actually is:
This is NOT a trained machine-learning disease classifier. It's a
color-heuristic method: healthy leaf tissue tends to be green, water-
or nutrient-stressed tissue tends to yellow, and dead/diseased tissue
tends to brown. By measuring the proportion of each color band across
the plant pixels in an image, we get a reasonable, cheap proxy for
overall plant health and a rough alert signal -- not a diagnosis of
which disease or deficiency is present. A real diagnostic system
would need a labeled dataset and a trained model (e.g. a CNN) per
crop species.
"""
from dataclasses import dataclass

import numpy as np
from matplotlib.colors import rgb_to_hsv


@dataclass
class HealthMetrics:
    plant_pixel_fraction: float  # fraction of the image classified as plant material
    green_pct: float             # % of plant pixels that look healthy/green
    yellow_pct: float            # % of plant pixels that look yellowing/stressed
    brown_pct: float             # % of plant pixels that look dead/diseased
    health_score: float          # 0-100 heuristic composite score


def compute_health_metrics(image_rgb: np.ndarray) -> HealthMetrics:
    """
    `image_rgb`: HxWx3 uint8 array with values in [0, 255].

    Classifies each pixel by hue/saturation/value into "green",
    "yellow", or "brown" plant-tissue bands (pixels too dark or too
    desaturated to be plant material, e.g. soil or background, are
    excluded from the percentages).
    """
    if image_rgb.dtype != np.float64 and image_rgb.dtype != np.float32:
        rgb_float = image_rgb.astype(np.float64) / 255.0
    else:
        rgb_float = image_rgb

    hsv = rgb_to_hsv(rgb_float)
    hue = hsv[..., 0] * 360.0
    sat = hsv[..., 1]
    val = hsv[..., 2]

    # Exclude background/soil/shadow: plant tissue is reasonably
    # saturated and not near-black. (Dark soil in typical photos sits
    # around value~0.15-0.18, so we require a bit more brightness
    # than that to avoid misclassifying soil as necrotic tissue.)
    plant_mask = (sat > 0.15) & (val > 0.22)
    total_plant = int(np.sum(plant_mask))

    if total_plant == 0:
        return HealthMetrics(0.0, 0.0, 0.0, 0.0, 0.0)

    green_mask = plant_mask & (hue >= 70) & (hue <= 170)
    yellow_mask = plant_mask & (hue >= 35) & (hue < 70)
    # "Brown" here means low-value (dark), low-saturation-ish reddish
    # or orange hues -- typical of necrotic/dead tissue.
    brown_mask = plant_mask & (val < 0.55) & (
        (hue < 35) | (hue > 300)
    )

    green_pct = float(np.sum(green_mask)) / total_plant * 100.0
    yellow_pct = float(np.sum(yellow_mask)) / total_plant * 100.0
    brown_pct = float(np.sum(brown_mask)) / total_plant * 100.0

    # Heuristic composite: green tissue contributes fully, yellow
    # tissue (mild/early stress) contributes partially, brown tissue
    # (necrotic/dead) is penalized heavily. E.g. a fully yellow plant
    # scores as "moderately stressed" rather than "as dead as a fully
    # brown one" -- yellowing and browning are different severities.
    raw_score = green_pct + 0.4 * yellow_pct - 0.6 * brown_pct
    health_score = float(np.clip(raw_score, 0.0, 100.0))

    return HealthMetrics(
        plant_pixel_fraction=total_plant / image_rgb.shape[0] / image_rgb.shape[1],
        green_pct=green_pct,
        yellow_pct=yellow_pct,
        brown_pct=brown_pct,
        health_score=health_score,
    )


def annotate_stress_regions(image_rgb: np.ndarray) -> np.ndarray:
    """
    Returns a copy of the image with brown/necrotic regions
    highlighted in solid red, for visual inspection. Useful for a
    human to sanity-check what the heuristic is flagging.
    """
    rgb_float = image_rgb.astype(np.float64) / 255.0
    hsv = rgb_to_hsv(rgb_float)
    hue = hsv[..., 0] * 360.0
    sat = hsv[..., 1]
    val = hsv[..., 2]

    plant_mask = (sat > 0.15) & (val > 0.22)
    brown_mask = plant_mask & (val < 0.55) & ((hue < 35) | (hue > 300))

    annotated = image_rgb.copy()
    annotated[brown_mask] = [255, 0, 0]
    return annotated
