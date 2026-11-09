"""Run offline model compatibility test on two permitted local images.

This is developer QA only, not a Photo Mode or user-facing image editor.
Does NOT save images or use the internet.
"""
import argparse
import time
from pathlib import Path

import cv2
import numpy as np

from faceweave.engine import LiveEngine


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True, type=Path)
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--target", required=True, type=Path)
    args = ap.parse_args()
    source = cv2.imread(str(args.source))
    target = cv2.imread(str(args.target))
    if source is None or target is None:
        raise SystemExit("Source or target QA image could not be read")
    engine = LiveEngine(args.models)
    try:
        t = time.perf_counter()
        engine.prepare(source, lambda message: print("SETUP", message, flush=True))
        print("PREPARE_SECONDS", round(time.perf_counter()-t,2), flush=True)
        t = time.perf_counter()
        result = engine.swap(target)
        duration = time.perf_counter()-t
        # Engine downsamples target to a max width/height 640px.
        expected = cv2.resize(target, (result.shape[1], result.shape[0]))
        difference = np.abs(result.astype(np.int16)-expected.astype(np.int16))
        print("FRAME_SECONDS", round(duration,2), flush=True)
        print("MEAN_ABSOLUTE_DIFFERENCE", round(float(difference.mean()),3), flush=True)
        print("P99_DIFFERENCE", float(np.percentile(difference, 99)), flush=True)
        print("CHANGED_PIXELS_OVER_20", float(np.any(difference > 20,axis=2).mean()), flush=True)
        print("INPUT_OUTPUT_DIMENSIONS",target.shape,result.shape,flush=True)
        assert difference.mean() > 0.2, "Expected nontrivial neural frame changes"
        assert result.ndim == 3 and result.shape[2] == 3
        print("ENGINE_SMOKE_PASS",flush=True)
    finally:
        engine.close()


if __name__ == "__main__":
    main()
