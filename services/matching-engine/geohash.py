"""Pure-Python geohash encode (no external dependency).

Used to cluster surplus orders into geographic cells before routing.
A geohash prefix of length N groups points into cells of roughly:
  precision 5 -> ~4.9km x 4.9km cells
  precision 6 -> ~1.2km x 0.6km cells
We cluster at precision 5 (~5km cells) by default.
"""

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def encode(lat: float, lng: float, precision: int = 5) -> str:
    """Encode a (lat, lng) pair into a geohash string."""
    lat_range = [-90.0, 90.0]
    lng_range = [-180.0, 180.0]
    bits = []
    even = True  # longitude first
    while len(bits) < precision * 5:
        if even:
            mid = (lng_range[0] + lng_range[1]) / 2
            if lng >= mid:
                bits.append(1)
                lng_range[0] = mid
            else:
                bits.append(0)
                lng_range[1] = mid
        else:
            mid = (lat_range[0] + lat_range[1]) / 2
            if lat >= mid:
                bits.append(1)
                lat_range[0] = mid
            else:
                bits.append(0)
                lat_range[1] = mid
        even = not even
    out = []
    for i in range(0, len(bits), 5):
        chunk = bits[i:i + 5]
        value = 0
        for b in chunk:
            value = (value << 1) | b
        out.append(_BASE32[value])
    return "".join(out)


def cell_key(lat: float, lng: float, precision: int = 5) -> str:
    """Cell key for clustering: the geohash prefix at the given precision."""
    return encode(lat, lng, precision)
