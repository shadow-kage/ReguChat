from enum import StrEnum


class Marker(StrEnum):
    CHECK       = "✓"  # ✓  sub-item success
    HEAVY_CHECK = "✔"  # ✔  step success
    CROSS       = "✗"  # ✗  sub-item failure
    HEAVY_CROSS = "✘"  # ✘  step failure
    SKIP        = "•"  # •  skipped / neutral info
