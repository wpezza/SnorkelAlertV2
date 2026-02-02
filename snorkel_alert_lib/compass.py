"""Compass helpers for direction logic."""

COMPASS_POINTS = [
    "N",
    "NNE",
    "NE",
    "ENE",
    "E",
    "ESE",
    "SE",
    "SSE",
    "S",
    "SSW",
    "SW",
    "WSW",
    "W",
    "WNW",
    "NW",
    "NNW",
]

COMPASS_TO_DEG = {point: i * 22.5 for i, point in enumerate(COMPASS_POINTS)}


def deg_to_compass(deg):
    """Convert degrees to compass direction."""
    if deg is None:
        return ""
    return COMPASS_POINTS[int((deg + 11.25) % 360 / 22.5)]


def compass_to_deg(compass):
    """Convert compass direction to degrees."""
    return COMPASS_TO_DEG.get(compass, 0)


def angular_diff(a, b):
    """Return smallest angular difference between degrees."""
    diff = abs((a or 0) - (b or 0))
    return diff if diff <= 180 else 360 - diff


def is_sheltered_from(shelter_from, direction_deg, tolerance=30):
    """Check if location is sheltered from a direction (v5 logic)."""
    if not shelter_from or direction_deg is None:
        return False

    for shelter_dir in shelter_from:
        shelter_deg = compass_to_deg(shelter_dir)
        if angular_diff(direction_deg, shelter_deg) <= tolerance:
            return True
    return False


def shelter_weight(shelter_from, direction_deg, full=15, partial=45):
    """Directional shelter weighting for v6."""
    if not shelter_from or direction_deg is None:
        return 0.0

    weight = 0.0
    for shelter_dir in shelter_from:
        shelter_deg = compass_to_deg(shelter_dir)
        diff = angular_diff(direction_deg, shelter_deg)
        if diff <= full:
            weight = max(weight, 1.0)
        elif diff <= partial:
            weight = max(weight, 0.5)
    return weight


def is_offshore_v5(wind_dir_deg):
    """Legacy offshore logic (E/NE/SE quadrant)."""
    if wind_dir_deg is None:
        return False
    return 45 <= wind_dir_deg <= 135


def is_offshore_v6(wind_dir_deg, shore_normal_deg, tolerance=65):
    """Offshore logic using shoreline orientation."""
    if wind_dir_deg is None or shore_normal_deg is None:
        return False

    offshore_dir = (shore_normal_deg + 180) % 360
    return angular_diff(wind_dir_deg, offshore_dir) <= tolerance
