"""
generate_demo_images.py - Creates a sequence of synthetic "leaf photo"
images that gradually shift from healthy green to yellowing to
browning, so the rest of the pipeline can be demoed/tested without
needing real plant photos.

Run from the scripts/ directory:
    python generate_demo_images.py
"""
import os

import numpy as np
from PIL import Image

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "demo_images")
IMAGE_SIZE = 200
NUM_FRAMES = 8


def make_leaf_image(decay: float) -> np.ndarray:
    """
    `decay`: 0.0 = fully healthy green, 1.0 = fully browned/dead.
    Builds a simple circular "leaf" on a dark soil-colored background.
    """
    img = np.zeros((IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8)
    img[:, :] = [40, 30, 20]  # dark soil background

    yy, xx = np.mgrid[0:IMAGE_SIZE, 0:IMAGE_SIZE]
    cx, cy = IMAGE_SIZE / 2, IMAGE_SIZE / 2
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    leaf_mask = r < IMAGE_SIZE * 0.4

    # Add a little noise so the "leaf" isn't a flat color.
    noise = (np.random.rand(IMAGE_SIZE, IMAGE_SIZE) * 20 - 10)

    # Interpolate leaf color: green -> yellow -> brown as decay increases.
    green = np.array([40, 160, 60])
    yellow = np.array([190, 180, 40])
    brown = np.array([110, 70, 30])

    if decay < 0.5:
        t = decay / 0.5
        color = (1 - t) * green + t * yellow
    else:
        t = (decay - 0.5) / 0.5
        color = (1 - t) * yellow + t * brown

    for c in range(3):
        channel = np.clip(color[c] + noise, 0, 255)
        img[..., c] = np.where(leaf_mask, channel.astype(np.uint8), img[..., c])

    return img


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for i in range(NUM_FRAMES):
        decay = i / (NUM_FRAMES - 1)
        image = make_leaf_image(decay)
        path = os.path.join(OUT_DIR, f"frame_{i:02d}.png")
        Image.fromarray(image).save(path)
        print(f"Wrote {path} (decay={decay:.2f})")


if __name__ == "__main__":
    main()
