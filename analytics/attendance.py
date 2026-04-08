"""GPS-based attendance with Haversine distance calculation."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

import math
from datetime import datetime
from database import query, execute


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth.
    Returns distance in meters.
    """
    R = 6371000  # Earth's radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def punch_in(employee_id: int, latitude: float, longitude: float) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    existing = query(
        "SELECT id FROM attendance WHERE employee_id = ? AND attendance_date = ? AND punch_out_time IS NULL",
        (employee_id, today), one=True
    )

    if existing:
        return {"success": False, "error": "Already punched in today. Please punch out first."}

    
    store = query(
        """SELECT s.store_lat, s.store_lng, s.geofence_radius, s.shift_start_time
           FROM employees e JOIN stores s ON e.store_id = s.store_id WHERE e.id = ?""",
        (employee_id,), one=True
    )

    if not store:
        return {"success": False, "error": "Employee or store not found."}

    # Calculate distance
    distance = haversine_distance(latitude, longitude, store["latitude"], store["longitude"])
    within_geofence = distance <= store["geofence_radius_meters"]

    now = datetime.now()
    status = "approved" if within_geofence else "rejected"

    # Calculate punctuality
    shift_start = datetime.strptime(f"{today} {store['shift_start_time']}", "%Y-%m-%d %H:%M")
    minutes_early = (shift_start - now).total_seconds() / 60
    is_on_time = minutes_early >= 0

    record_id = execute(
        """INSERT INTO attendance (employee_id, punch_in_time, punch_in_lat, punch_in_lng,
           punch_in_distance_meters, punch_in_status, attendance_date)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (employee_id, now.strftime("%Y-%m-%d %H:%M:%S"), latitude, longitude, round(distance, 2), status, today)
    )

    return {
        "success": within_geofence,
        "attendance_id": record_id,
        "status": status,
        "distance_meters": round(distance, 2),
        "geofence_radius": store["geofence_radius_meters"],
        "is_on_time": is_on_time,
        "minutes_early": round(minutes_early, 1) if is_on_time else 0,
        "minutes_late": round(abs(minutes_early), 1) if not is_on_time else 0,
        "message": "Attendance marked successfully!" if within_geofence else f"Outside geofence. You are {round(distance, 0)}m from the store (limit: {store['geofence_radius_meters']}m).",
    }


def punch_out(employee_id: int, latitude: float, longitude: float) -> dict:
    
    today = datetime.now().strftime("%Y-%m-%d")

    
    active = query(
        "SELECT id, punch_in_time FROM attendance WHERE employee_id = ? AND attendance_date = ? AND punch_out_time IS NULL AND punch_in_status = 'approved'",
        (employee_id, today), one=True
    )

    if not active:
        return {"success": False, "error": "No active punch-in found for today."}

    
    store = query(
        "SELECT s.store_lat, s.store_lng, s.geofence_radius FROM employees e JOIN stores s ON e.store_id = s.store_id WHERE e.id = ?",
        (employee_id,), one=True
    )

    distance = haversine_distance(latitude, longitude, store["latitude"], store["longitude"])
    now = datetime.now()

    
    punch_in_time = datetime.strptime(active["punch_in_time"], "%Y-%m-%d %H:%M:%S")
    hours_worked = (now - punch_in_time).total_seconds() / 3600

    status = "approved" if distance <= store["geofence_radius_meters"] else "rejected"

    execute(
        """UPDATE attendance SET punch_out_time = ?, punch_out_lat = ?, punch_out_lng = ?,
           punch_out_distance_meters = ?, punch_out_status = ?, hours_worked = ?
           WHERE id = ?""",
        (now.strftime("%Y-%m-%d %H:%M:%S"), latitude, longitude, round(distance, 2), status, round(hours_worked, 2), active["id"])
    )

    return {
        "success": True,
        "status": status,
        "hours_worked": round(hours_worked, 2),
        "distance_meters": round(distance, 2),
        "message": f"Punched out. Hours worked: {round(hours_worked, 1)}h",
    }


def get_attendance_status(employee_id: int) -> dict:
    
    today = datetime.now().strftime("%Y-%m-%d")

    active = query(
        """SELECT id, punch_in_time, punch_in_status FROM attendance 
           WHERE employee_id = ? AND attendance_date = ? AND punch_out_time IS NULL AND punch_in_status = 'approved'""",
        (employee_id, today), one=True
    )

    if active:
        punch_in_time = datetime.strptime(active["punch_in_time"], "%Y-%m-%d %H:%M:%S")
        hours_so_far = (datetime.now() - punch_in_time).total_seconds() / 3600
        return {
            "is_punched_in": True,
            "punch_in_time": active["punch_in_time"],
            "hours_so_far": round(hours_so_far, 2),
        }

   
    completed = query(
        "SELECT punch_in_time, punch_out_time, hours_worked FROM attendance WHERE employee_id = ? AND attendance_date = ? AND punch_out_time IS NOT NULL",
        (employee_id, today), one=True
    )

    if completed:
        return {
            "is_punched_in": False,
            "completed_today": True,
            "hours_worked": completed["hours_worked"],
            "punch_in_time": completed["punch_in_time"],
            "punch_out_time": completed["punch_out_time"],
        }

    return {"is_punched_in": False, "completed_today": False}
