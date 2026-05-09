from enum import StrEnum


class Marker(StrEnum):
    CHECK       = "✓"
    HEAVY_CHECK = "✔"
    CROSS       = "✗"
    HEAVY_CROSS = "✘"
    SKIP        = "•"
