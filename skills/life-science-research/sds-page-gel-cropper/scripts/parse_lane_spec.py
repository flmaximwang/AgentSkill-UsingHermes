"""
parse_lane_spec.py - Parse lane specification strings into sorted lane number lists.

Supported formats:
  "1,3-5"    -> [1, 3, 4, 5]
  "lane 2"   -> [2]
  "2"        -> [2]
  "1-4"      -> [1, 2, 3, 4]
  "1,3-5,7"  -> [1, 3, 4, 5, 7]
  "泳道2,4-6" -> [2, 4, 5, 6]
"""

import re


def parse_lane_spec(spec: str) -> list[int]:
    """
    Parse a lane specification string into a sorted, deduplicated list of integers.

    Args:
        spec: Lane spec string, e.g. "1,3-5", "lane 2", "泳道 1,3-5"

    Returns:
        Sorted list of lane numbers.

    Raises:
        ValueError: If the spec cannot be parsed.
    """
    # Strip common prefixes: "lane", "泳道", "Lane", etc.
    spec = spec.strip()
    spec = re.sub(r"^(lane|泳道|Lane|泳道\s*)[:\s]*", "", spec, flags=re.IGNORECASE).strip()
    if not spec:
        raise ValueError(f"Empty lane specification: {spec!r}")

    lanes: set[int] = set()
    parts = spec.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(\d+)\s*-\s*(\d+)$", part)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            if start > end:
                raise ValueError(f"Invalid range: {part} (start > end)")
            lanes.update(range(start, end + 1))
        else:
            m = re.match(r"^(\d+)$", part)
            if m:
                lanes.add(int(m.group(1)))
            else:
                raise ValueError(f"Cannot parse lane spec part: {part!r}")

    result = sorted(lanes)
    return result


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        try:
            result = parse_lane_spec(arg)
            print(f"{arg!r} -> {result}")
        except ValueError as e:
            print(f"{arg!r} -> ERROR: {e}")
