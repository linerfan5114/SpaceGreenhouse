"""
main.py - CLI entry point: processes a folder of plant photos in
chronological order (by filename) and produces a health report + trend chart.

Usage:
    python main.py --images ../data/demo_images --name "Tomato-1"
"""
import argparse
import glob
import os

import numpy as np
from PIL import Image

from plant import PlantMonitor
from report import generate_text_report, plot_health_trend


def load_image_rgb(path: str) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    return np.array(img)


def main():
    parser = argparse.ArgumentParser(description="Plant health monitor from photos.")
    parser.add_argument("--images", required=True, help="Folder of photos, processed in filename order.")
    parser.add_argument("--name", default="Plant-1", help="Name/label for this plant.")
    parser.add_argument("--out", default="../data/health_trend.png", help="Where to save the trend chart.")
    args = parser.parse_args()

    image_paths = sorted(glob.glob(os.path.join(args.images, "*.png")) +
                          glob.glob(os.path.join(args.images, "*.jpg")))
    if not image_paths:
        print(f"No images found in {args.images}")
        return

    monitor = PlantMonitor(name=args.name)

    for path in image_paths:
        image_rgb = load_image_rgb(path)
        reading = monitor.add_reading(image_rgb, source=os.path.basename(path))
        print(f"{os.path.basename(path)}: health={reading.metrics.health_score:.1f} "
              f"green={reading.metrics.green_pct:.1f}% "
              f"yellow={reading.metrics.yellow_pct:.1f}% "
              f"brown={reading.metrics.brown_pct:.1f}%")

    print()
    print(generate_text_report(monitor))

    plot_health_trend(monitor, args.out)
    print(f"\nTrend chart saved to {args.out}")


if __name__ == "__main__":
    main()
