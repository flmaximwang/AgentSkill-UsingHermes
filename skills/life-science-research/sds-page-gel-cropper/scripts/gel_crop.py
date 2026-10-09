"""
gel_crop.py - Crop specific lanes from SDS-PAGE gel images.

Usage:
    python gel_crop.py <image_path> <lane_spec> [--output-dir DIR] [--coord-type {normalized,pixel}]

Three lane boundary sources (mutually exclusive):
  --vision-coords LANE:LEFT:RIGHT ...     Vision-model coordinates, one triplet per lane
                                          e.g. --vision-coords 1:0.05:0.25 2:0.30:0.50
                                          Supports normalized [0,1] or pixel values.
  --auto-lanes [N]                        Auto-detect via intensity projection; optional N = expected lanes.
  --lane-boundaries FILE                  JSON file with lane boundary data [{"lane":1,"left":...,"right":...},...]

Examples:
    python gel_crop.py gel.jpeg "2,4" --auto-lanes
    python gel_crop.py gel.jpeg "1-3" --vision-coords 1:0.05:0.25 2:0.30:0.50 3:0.55:0.75 4:0.80:0.95
"""

import argparse
import json
import sys
import re
from pathlib import Path

from PIL import Image

from parse_lane_spec import parse_lane_spec


def resolve_lane_boundaries(
    image_path: str,
    vision_coords: list[str] | None = None,
    auto_lanes: bool = False,
    expected_lanes: int | None = None,
    lane_boundaries_file: str | None = None,
) -> list[dict]:
    """
    Resolve lane boundaries from one of three sources.

    Returns list of dicts: [{"lane": int, "left_px": int, "right_px": int}, ...]
    """
    img = Image.open(image_path)
    w, h = img.size

    if lane_boundaries_file:
        with open(lane_boundaries_file) as f:
            data = json.load(f)
        # Normalize if needed
        boundaries = []
        for entry in data:
            lane = entry["lane"]
            left, right = entry["left"], entry["right"]
            # Heuristic: if < 1, assume normalized; else pixel
            if left < 1 and right < 1:
                left = int(left * w)
                right = int(right * w)
            boundaries.append({"lane": lane, "left_px": int(left), "right_px": int(right)})
        return boundaries

    if vision_coords:
        boundaries = []
        for triplet in vision_coords:
            parts = triplet.split(":")
            if len(parts) != 3:
                raise ValueError(f"Invalid vision-coord format: {triplet!r} (expected lane:left:right)")
            lane, left, right = int(parts[0]), float(parts[1]), float(parts[2])
            if left < 1 and right < 1:
                left = int(left * w)
                right = int(right * w)
            boundaries.append({"lane": lane, "left_px": int(left), "right_px": int(right)})
        return boundaries

    if auto_lanes:
        from detect_lanes import detect_lanes
        return detect_lanes(image_path, expected_lanes)

    raise ValueError("No lane boundary source provided (--vision-coords, --auto-lanes, or --lane-boundaries)")


def crop_lanes(
    image_path: str,
    lane_spec: str,
    vision_coords: list[str] | None = None,
    auto_lanes: bool = False,
    expected_lanes: int | None = None,
    lane_boundaries_file: str | None = None,
    output_dir: str | None = None,
) -> list[str]:
    """
    Crop requested lanes from a gel image.

    Args:
        image_path: Path to the gel image.
        lane_spec: Lane specification string, e.g. "1,3-5", "lane 2".
        vision_coords: Vision-model lane coordinate triplets "lane:left:right".
        auto_lanes: Auto-detect lanes via intensity projection.
        expected_lanes: Hint for auto detection.
        lane_boundaries_file: JSON file with lane boundaries.
        output_dir: Output directory (default: <image_dir>/cropped_lanes/<image_stem>/).

    Returns:
        List of absolute paths to cropped lane images.
    """
    img_path = Path(image_path)
    img = Image.open(image_path)
    w, h = img.size

    # Resolve boundaries
    all_boundaries = resolve_lane_boundaries(
        image_path, vision_coords, auto_lanes, expected_lanes, lane_boundaries_file
    )

    # Parse the lane spec
    requested = parse_lane_spec(lane_spec)

    # Validate
    max_lane = max(b["lane"] for b in all_boundaries)
    for lane in requested:
        if lane < 1 or lane > max_lane:
            raise ValueError(f"Lane {lane} out of range (gel has {max_lane} lanes, 1-{max_lane})")

    # Build a lookup
    boundary_map = {b["lane"]: b for b in all_boundaries}

    # Output dir
    if output_dir is None:
        output_dir = img_path.parent / "cropped_lanes" / img_path.stem
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for lane_num in requested:
        b = boundary_map[lane_num]
        cropped = img.crop((b["left_px"], 0, b["right_px"], h))
        out_path = output_dir / f"{img_path.stem}_lane{lane_num}.png"
        cropped.save(out_path)
        results.append(str(out_path.resolve()))

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Crop specific lanes from SDS-PAGE gel images."
    )
    parser.add_argument("image_path", help="Path to the gel image")
    parser.add_argument("lane_spec", help="Lane specification, e.g. '1,3-5', 'lane 2'")

    source = parser.add_argument_group("Lane boundary source (choose one)")
    source.add_argument(
        "--vision-coords", nargs="+", metavar="LANE:LEFT:RIGHT",
        help="Vision-model coordinates, e.g. '1:0.05:0.25' '2:0.30:0.50'"
    )
    source.add_argument(
        "--auto-lanes", nargs="?", const=-1, type=int, default=None,
        help="Auto-detect lanes via intensity projection (optionally specify expected lane count)"
    )
    source.add_argument("--lane-boundaries", help="JSON file with lane boundary data")

    parser.add_argument("--output-dir", help="Output directory for cropped images")

    args = parser.parse_args()

    expected_lanes = args.auto_lanes if args.auto_lanes is not None and args.auto_lanes > 0 else None
    auto_lanes_flag = args.auto_lanes is not None

    try:
        results = crop_lanes(
            image_path=args.image_path,
            lane_spec=args.lane_spec,
            vision_coords=args.vision_coords,
            auto_lanes=auto_lanes_flag,
            expected_lanes=expected_lanes,
            lane_boundaries_file=args.lane_boundaries,
            output_dir=args.output_dir,
        )
        print(f"Cropped {len(results)} lane(s):")
        for r in results:
            print(f"  {r}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
