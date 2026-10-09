"""
refine_boundaries.py - Refine lane boundary estimates from vision model
using column intensity analysis.

Takes approximate boundary estimates (from vision model) and finds the
exact gap positions by searching for the brightest column (max intensity =
empty gel) near each estimated gap.

Usage:
    python refine_boundaries.py <image_path> <coords> [--output-json FILE]

    coords: JSON list of {"lane": N, "left": L, "right": R} with L,R in [0,1] normalized
            OR pixel coordinates (> 1)
"""

import json
import sys
from pathlib import Path

from PIL import Image
import numpy as np


def refine_boundaries(image_path: str, estimates: list[dict]) -> list[dict]:
    """
    Refine lane boundary estimates using column intensity analysis.

    For each gap between lanes, searches a window around the estimated gap
    position for the brightest column (the gap center), then uses that as
    the precise boundary.

    Args:
        image_path: Path to the gel image.
        estimates: List of [{"lane": int, "left": float, "right": float}, ...]
                   left/right can be normalized [0,1] or pixel values (>1).

    Returns:
        List of [{"lane": int, "left_px": int, "right_px": int}, ...]
        with pixel-precise boundaries.
    """
    img = Image.open(image_path).convert("L")
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape

    # Normalize estimates to pixel coordinates
    pixel_estimates = []
    for e in estimates:
        lane = e["lane"]
        left = e["left"]
        right = e["right"]
        if left < 1 and right < 1:
            left_px = int(left * w)
            right_px = int(right * w)
        else:
            left_px, right_px = int(left), int(right)
        pixel_estimates.append({"lane": lane, "left_px": left_px, "right_px": right_px})

    # Column intensity profile
    proj = arr.mean(axis=0)  # shape (w,); high = bright = gap

    # Compute gradient of the projection (edges are where intensity changes fast)
    gradient = np.abs(np.diff(proj))  # shape (w-1,); high values = edges

    # Smooth the gradient to reduce noise
    grad_kernel_size = max(3, w // 100)
    gk = np.ones(grad_kernel_size) / grad_kernel_size
    grad_smooth = np.convolve(gradient, gk, mode="same")

    # For each gap between consecutive lanes, refine the boundary
    refined = []
    for i, e in enumerate(pixel_estimates):
        lane = e["lane"]

        # Left boundary of this lane = right edge of gap to the left
        if lane == 1:
            left_boundary = max(0, e["left_px"])
        else:
            prev_right = pixel_estimates[i - 1]["right_px"]
            gap_center = (prev_right + e["left_px"]) // 2
            search_radius = max(5, (e["left_px"] - prev_right) // 2)
            # Find the strongest gradient edge in the gap region
            # This is the boundary between the gap and the lane
            left_boundary = _find_edge(grad_smooth, gap_center, search_radius, w)

        # Right boundary of this lane = left edge of gap to the right
        if lane == len(pixel_estimates):
            right_boundary = min(w, e["right_px"])
        else:
            next_left = pixel_estimates[i + 1]["left_px"]
            gap_center = (e["right_px"] + next_left) // 2
            search_radius = max(5, (next_left - e["right_px"]) // 2)
            # Search in two halves: left side of gap (falling edge of lane)
            # and right side of gap (rising edge of next lane)
            half_radius = search_radius // 2
            _lo = max(0, gap_center - half_radius)
            _hi = min(w - 1, gap_center + half_radius)
            if _lo <= _hi:
                segment = grad_smooth[_lo:_hi]
                edge_idx = int(np.argmax(segment)) + _lo
                right_boundary = edge_idx
            else:
                right_boundary = gap_center

        refined.append({"lane": lane, "left_px": int(left_boundary), "right_px": int(right_boundary)})

    return refined


def _find_edge(grad_profile: np.ndarray, center: int, radius: int, width: int) -> int:
    """Find the strongest gradient edge near `center` within ±radius."""
    lo = max(0, center - radius)
    hi = min(len(grad_profile), center + radius + 1)
    if lo >= hi:
        return center
    segment = grad_profile[lo:hi]
    edge_idx = int(np.argmax(segment)) + lo
    return int(edge_idx)


def main():
    if len(sys.argv) < 3:
        print("Usage: python refine_boundaries.py <image_path> '<estimates_json>' [--output-json FILE]")
        sys.exit(1)

    image_path = sys.argv[1]
    estimates = json.loads(sys.argv[2])

    result = refine_boundaries(image_path, estimates)

    output_json = None
    if "--output-json" in sys.argv:
        idx = sys.argv.index("--output-json")
        output_json = sys.argv[idx + 1]

    if output_json:
        with open(output_json, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Saved refined boundaries to {output_json}")

    print(f"Refined boundaries for {len(result)} lanes (image: {Path(image_path).name}):")
    for r in result:
        print(f"  Lane {r['lane']}: {r['left_px']}-{r['right_px']} px ({r['right_px'] - r['left_px']}px wide)")


if __name__ == "__main__":
    main()
