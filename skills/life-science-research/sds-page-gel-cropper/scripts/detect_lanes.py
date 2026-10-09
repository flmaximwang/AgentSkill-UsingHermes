"""
detect_lanes.py - Auto-detect lane boundaries in SDS-PAGE gel images via
vertical intensity projection (Pillow + numpy).

Algorithm: looks for BRIGHT columns (gaps between lanes) in the original
grayscale image. Lanes are darker (protein bands), gaps are brighter (empty gel).

LIMITATIONS: Only works for gels with clearly visible empty gaps between lanes.
High-background gels or heavily overexposed images may fail — the primary workflow
is vision model detection, with this as a fallback.
"""

from PIL import Image
import numpy as np


def detect_lanes(image_path: str, expected_lanes: int | None = None) -> list[dict]:
    """
    Detect lane boundaries from a gel image using vertical intensity projection.

    Args:
        image_path: Path to the gel image file.
        expected_lanes: Hint for number of lanes. Required for reliable detection.

    Returns:
        List of dicts: [{"lane": 1, "left_px": int, "right_px": int}, ...]
        left_px and right_px are absolute pixel coordinates (exclusive right).
    """
    img = Image.open(image_path).convert("L")  # grayscale
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape

    # Vertical projection: mean pixel value per column
    # High values = bright = empty gel (gaps between lanes)
    # Low values = dark = protein bands (lanes)
    projection = arr.mean(axis=0)  # shape (w,)

    # Apply aggressive smoothing to remove individual band structure
    # Kernel size proportional to image width — large enough to blur within-lane bands
    kernel_size = max(5, w // 20)  # ~5% of image width
    if kernel_size % 2 == 0:
        kernel_size += 1  # ensure odd
    kernel = np.ones(kernel_size) / kernel_size
    smoothed = np.convolve(projection, kernel, mode="same")

    # Find valleys (low points) in the smoothed projection
    # These correspond to the darkest columns = centers of lanes
    valleys = []
    for i in range(1, len(smoothed) - 1):
        if smoothed[i] < smoothed[i - 1] and smoothed[i] < smoothed[i + 1]:
            valleys.append(i)

    if not valleys:
        # Fallback: can't detect lanes — return whole image as one lane
        return [{"lane": 1, "left_px": 0, "right_px": w}]

    # If we know how many lanes, find the strongest N valleys
    if expected_lanes:
        # Score valleys by depth (how much darker than neighbors)
        depths = [(min(smoothed[i - 1], smoothed[i + 1]) - smoothed[i])
                  for i in valleys]
        # Pick the strongest valleys
        sorted_idx = np.argsort(depths)[::-1]
        selected = sorted_idx[:expected_lanes]
        selected = sorted(selected)  # restore left-to-right order
        valleys = [valleys[i] for i in selected]

    # Find gaps between lane centers: midpoints between adjacent valleys
    # Lane boundaries = halfway between lane centers
    boundaries = []
    # Left edge of first lane: 0
    # Left gap after first lane center: midpoint between valley[0] and valley[1]
    for i, v in enumerate(valleys):
        left = 0 if i == 0 else (valleys[i - 1] + v) // 2
        if i < len(valleys) - 1:
            right = (v + valleys[i + 1]) // 2
        else:
            right = w
        boundaries.append({"lane": i + 1, "left_px": int(left), "right_px": int(right)})

    return boundaries


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python detect_lanes.py <image_path> [expected_lanes]")
        sys.exit(1)

    expected = int(sys.argv[2]) if len(sys.argv) > 2 else None
    result = detect_lanes(sys.argv[1], expected)
    print(f"Detected {len(result)} lanes:")
    for lane in result:
        print(f"  Lane {lane['lane']}: {lane['left_px']}-{lane['right_px']} px ({lane['right_px'] - lane['left_px']}px wide)")
