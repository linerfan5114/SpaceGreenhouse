# SpaceGreenhouse

A plant health monitoring pipeline that estimates a health score from
photos using classic computer-vision color analysis (HSV
thresholding), tracks it over time, and raises simple alerts when a
plant looks stressed or diseased.

## What this actually is (please read)

This is **not** a trained machine-learning disease classifier and it
cannot identify a specific disease, pest, or nutrient deficiency. It
uses a well-understood heuristic: healthy leaf tissue tends to be
green, water/nutrient-stressed tissue tends to yellow, and
dead/necrotic tissue tends to brown. By measuring the proportion of
each color band in a photo (after excluding background/soil), we get
a cheap, explainable proxy for overall plant health and a reasonable
early-warning signal.

If you wanted real disease *identification* (e.g. "this is powdery
mildew"), you'd need a labeled image dataset per crop/disease and a
trained model (e.g. a CNN) -- a meaningfully bigger project than this
one, and out of scope here.

"Long-duration space missions" is a fun frame for *why* automated
plant monitoring matters (a real research topic for controlled-
environment agriculture), but this project itself is a general-
purpose, ground-based plant-health tool -- nothing here is
spaceflight-specific or hardware-qualified.

## How it works

1. `vision.py` converts an RGB photo to HSV and classifies each pixel
   as green / yellow / brown plant tissue (or "not plant" -- e.g.
   soil, pot, background).
2. `plant.py`'s `PlantMonitor` stores a history of readings for a
   plant and raises alerts when the health score crosses a threshold,
   or when brown/necrotic tissue jumps sharply between readings.
3. `report.py` turns that history into a text summary and a trend
   chart (health score over time, with threshold lines).
4. `main.py` ties it together: point it at a folder of photos (named
   so they sort chronologically) and it processes them in order.

## Running it

```bash
pip install -r requirements.txt

# Generate synthetic demo photos (green -> yellow -> brown over time),
# since this repo doesn't ship real plant photos:
cd scripts
python generate_demo_images.py

# Run the monitor over the demo photos:
cd ../src
python main.py --images ../data/demo_images --name "Demo-Leaf"
```

This prints a per-photo health readout, a text report, and saves a
trend chart to `data/health_trend.png`.

## Running the tests

```bash
pip install pytest
pytest tests/
```

## Project layout

```
SpaceGreenhouse/
├── README.md
├── requirements.txt
├── src/
│   ├── vision.py    # HSV color-based health metrics (the core algorithm)
│   ├── plant.py       # PlantMonitor: history + threshold-based alerts
│   ├── report.py        # text report + trend chart
│   └── main.py            # CLI entry point
├── scripts/
│   └── generate_demo_images.py  # synthetic photos for demo/testing
├── data/
│   └── demo_images/               # generated at runtime
└── tests/
    └── test_vision.py               # unit tests for the health heuristic
```

## Known limitations

- Color thresholds (hue/saturation/value cutoffs) were tuned against
  synthetic test images, not a real photo dataset. Real photos have
  more lighting variation, shadows, and background clutter, and will
  likely need threshold tuning (or a proper segmentation step) to
  work reliably.
- No disease-specific identification -- see above.
- The "brown = necrotic" heuristic can be fooled by anything else
  brown in frame (soil visible through gaps in leaves, wooden plant
  stakes, etc.) -- a real deployment would need better plant/background
  segmentation, e.g. via a simple trained segmentation model.

## Possible next steps

- Replace the color-threshold plant/background split with a trained
  segmentation model for more robust masking on real photos.
- Add per-species threshold presets (a cactus and a tomato plant have
  very different "normal" color ranges).
- Log readings to a CSV/database instead of only in-memory history,
  so long-running deployments don't lose data on restart.
