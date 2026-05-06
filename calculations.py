# calculations.py — Məsafə və ssenari hesablamaları
from haversine import haversine, Unit
from data_loader import HOTEL_COORDS, BOS

def calc_distance_km(lat1, lon1, lat2, lon2) -> float:
    return round(haversine((lat1, lon1), (lat2, lon2), unit=Unit.KILOMETERS), 3)

def hotel_distances() -> list:
    """Hər oteldən BOS-a məsafə"""
    result = []
    for hotel, coords in HOTEL_COORDS.items():
        km = calc_distance_km(coords["lat"], coords["lon"], BOS["lat"], BOS["lon"])
        result.append({"hotel": hotel, "lat": coords["lat"], "lon": coords["lon"],
                        "color": coords["color"], "distance_km": km})
    return sorted(result, key=lambda x: x["distance_km"])

def seconds_to_hhmm(secs: int) -> str:
    secs = max(0, int(secs))
    h = secs // 3600
    m = (secs % 3600) // 60
    return f"{h:02d}:{m:02d}"

def hhmm_to_seconds(t: str) -> int:
    try:
        p = t.strip().split(":")
        return int(p[0]) * 3600 + int(p[1]) * 60
    except:
        return 0

def scenario_simultaneous(arrival_time: str, speed_kmh: float = 40) -> list:
    """Hamı eyni anda BOS-a çatsın → hər oteldən çıxış vaxtı"""
    arr_sec = hhmm_to_seconds(arrival_time)
    result  = []
    for row in hotel_distances():
        travel_sec = int((row["distance_km"] / speed_kmh) * 3600)
        dep_sec    = arr_sec - travel_sec
        result.append({
            "hotel":            row["hotel"],
            "distance_km":      row["distance_km"],
            "travel_min":       round(travel_sec / 60, 1),
            "departure_time":   seconds_to_hhmm(dep_sec),
            "arrival_time":     arrival_time,
        })
    return result

def scenario_staggered(first_arrival: str, interval_sec: int = 50,
                        speed_kmh: float = 40) -> list:
    """N saniyə intervalla BOS-a çatmaq → çıxış cədvəli"""
    first_sec = hhmm_to_seconds(first_arrival)
    rows      = hotel_distances()
    result    = []
    for i, row in enumerate(rows):
        arr_sec    = first_sec + i * interval_sec
        travel_sec = int((row["distance_km"] / speed_kmh) * 3600)
        dep_sec    = arr_sec - travel_sec
        result.append({
            "sira":           i + 1,
            "hotel":          row["hotel"],
            "distance_km":    row["distance_km"],
            "travel_min":     round(travel_sec / 60, 1),
            "arrival_time":   seconds_to_hhmm(arr_sec),
            "departure_time": seconds_to_hhmm(dep_sec),
        })
    return result

def time_diff_min(plan: str, actual: str) -> float | None:
    if not plan or not actual:
        return None
    return round((hhmm_to_seconds(actual) - hhmm_to_seconds(plan)) / 60, 1)

def infer_status(plan: str, actual: str) -> str:
    if not actual or actual.strip() == "":
        return "Pending"
    d = time_diff_min(plan, actual)
    if d is None:
        return "Pending"
    return "Delay" if d > 3 else "OK"
