"""Seed data generator for PerformIQ — creates realistic dummy data."""

import sqlite3
import random
import os
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "performiq.db"
SCHEMA_PATH = Path(__file__).parent.parent / "server" / "db" / "schema.sql"

random.seed(42)

# Employee archetypes for realistic variation
ARCHETYPES = {
    "star": {"rev_range": (8000, 15000), "basket_range": (5000, 12000), "consistency": 0.85, "growth": 0.05},
    "steady": {"rev_range": (5000, 9000), "basket_range": (3000, 7000), "consistency": 0.92, "growth": 0.01},
    "growing": {"rev_range": (3000, 7000), "basket_range": (2500, 5500), "consistency": 0.7, "growth": 0.08},
    "inconsistent": {"rev_range": (2000, 12000), "basket_range": (1500, 10000), "consistency": 0.4, "growth": -0.02},
    "underperformer": {"rev_range": (1500, 4000), "basket_range": (1000, 3000), "consistency": 0.6, "growth": -0.03},
}

EMPLOYEE_DATA = [
    ("Rahul Sharma", "rahul@example.com", "9876543210", "employee", "star"),
    ("Priya Patel", "priya@example.com", "9876543211", "employee", "star"),
    ("Amit Kumar", "amit@example.com", "9876543212", "employee", "steady"),
    ("Neha Gupta", "neha@example.com", "9876543213", "employee", "steady"),
    ("Vikram Singh", "vikram@example.com", "9876543214", "employee", "growing"),
    ("Ananya Reddy", "ananya@example.com", "9876543215", "employee", "growing"),
    ("Rohan Joshi", "rohan@example.com", "9876543216", "employee", "growing"),
    ("Kavita Nair", "kavita@example.com", "9876543217", "employee", "inconsistent"),
    ("Suresh Menon", "suresh@example.com", "9876543218", "employee", "inconsistent"),
    ("Deepika Rao", "deepika@example.com", "9876543219", "employee", "underperformer"),
    ("Arjun Verma", "arjun@example.com", "9876543220", "employee", "steady"),
    ("Sanya Mehta", "sanya@example.com", "9876543221", "employee", "star"),
    ("Karan Malhotra", "karan@example.com", "9876543222", "employee", "growing"),
    ("Meera Shah", "meera.s@example.com", "9876543223", "employee", "steady"),
    ("Rajesh Khanna", "rajesh@example.com", "9876543224", "employee", "growing"),
    ("Sneha Kapoor", "sneha@example.com", "9876543225", "employee", "star"),
    ("Vijay Mallya", "vijay@example.com", "9876543226", "employee", "underperformer"),
    ("Ayesha Khan", "ayesha@example.com", "9876543227", "employee", "steady"),
    ("Zaid Shaikh", "zaid@example.com", "9876543228", "employee", "growing"),
    ("Ishita Bhalla", "ishita@example.com", "9876543229", "employee", "inconsistent"),
    ("Tushar Deshpande", "tushar@example.com", "9876543232", "employee", "growing"),
    ("Pooja Hegde", "pooja@example.com", "9876543233", "employee", "star"),
    ("Manish Pandey", "manish@example.com", "9876543234", "employee", "steady"),
    ("Jahnvi Kapoor", "jahnvi@example.com", "9876543235", "employee", "growing"),
    # Managers
    ("Alex Thompson", "alex@example.com", "9876543230", "manager", "star"),
    ("Meera Iyer", "meera@example.com", "9876543231", "manager", "steady"),
]

DEPARTMENTS = [
    ("Shirts", 450000, 6500, 0.12),
    ("Kurtas", 300000, 5000, 0.08),
    ("Polos", 250000, 4000, 0.10),
    ("Tees", 200000, 3000, 0.05),
    ("Shorts", 150000, 2500, 0.07),
    ("Denims", 500000, 8000, 0.15),
    ("Trousers", 400000, 7000, 0.13),
    ("Cargos", 350000, 6000, 0.11),
]

STORES = [
    ("Blue Buddha Flagship", "Ahmedabad, Gujarat", 22.991573, 72.539284, 200),
    ("Blue Buddha Outlet", "Surat, Gujarat", 21.170240, 72.831061, 150),
]

BADGE_DEFINITIONS = [
    ("target_crusher", "Target Crusher", "🎯"),
    ("rock_solid", "Rock Solid", "🪨"),
    ("on_the_rise", "On The Rise", "📈"),
    ("never_miss", "Never Miss", "✅"),
    ("early_bird", "Early Bird", "🌅"),
    ("app_champion", "App Champion", "📱"),
    ("fan_favourite", "Fan Favourite", "⭐"),
]


def create_db():
    os.makedirs(DB_PATH.parent, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(str(DB_PATH))
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    return conn


def seed_stores(conn):
    for name, address, lat, lng, radius in STORES:
        conn.execute(
            "INSERT INTO stores (name, address, latitude, longitude, geofence_radius_meters) VALUES (?, ?, ?, ?, ?)",
            (name, address, lat, lng, radius),
        )
    conn.commit()


def seed_departments(conn):
    for name, target, basket, app_rate in DEPARTMENTS:
        for store_id in [1, 2]:
            factor = 1.0 if store_id == 1 else 0.8
            conn.execute(
                "INSERT INTO departments (store_id, name, weekly_revenue_target, avg_basket_size, avg_app_conversion_rate) VALUES (?, ?, ?, ?, ?)",
                (store_id, name, target * factor, basket, app_rate),
            )
    conn.commit()


def seed_employees(conn):
    emp_ids = []
    for i, (name, email, phone, role, archetype) in enumerate(EMPLOYEE_DATA):
        if role == "manager":
            store_id = 1 if "Thompson" in name else 2
            dept_id = 1 if store_id == 1 else 2
        else:
            # 24 employees, 14 in store 1, 10 in store 2
            store_id = 1 if i < 14 else 2
            dept_idx = i % 8
            if store_id == 1:
                dept_id = (dept_idx * 2) + 1
            else:
                dept_id = (dept_idx * 2) + 2

        conn.execute(
            "INSERT INTO employees (name, email, phone, role, department_id, store_id) VALUES (?, ?, ?, ?, ?, ?)",
            (name, email, phone, role, dept_id, store_id),
        )
        emp_ids.append((i + 1, archetype, dept_id, store_id))
    conn.commit()
    return emp_ids


def seed_sales(conn, employees):
    start_date = datetime(2026, 1, 12)

    for emp_id, archetype, dept_id, store_id in employees:
        if EMPLOYEE_DATA[emp_id - 1][3] == "manager":
            continue

        arch = ARCHETYPES[archetype]
        base_rev = sum(arch["rev_range"]) / 2

        for week in range(8):
            growth_factor = 1 + (arch["growth"] * week)
            week_start = start_date + timedelta(weeks=week)

            for day_offset in range(6):
                day = week_start + timedelta(days=day_offset)
                if day > datetime(2026, 3, 9):
                    break

                num_sales = random.randint(5, 15)

                if random.random() > arch["consistency"]:

                    num_sales = random.randint(2, 6)

                for _ in range(num_sales):
                    rev = random.uniform(*arch["rev_range"]) / num_sales * growth_factor
                    rev = max(200, rev)
                    basket = random.uniform(*arch["basket_range"]) / num_sales * growth_factor
                    basket = max(100, basket)
                    num_items = random.randint(1, 5)
                    app_dl = 1 if random.random() < 0.15 else 0

                    conn.execute(
                        """INSERT INTO sales (employee_id, revenue, basket_size, num_items, app_download,
                           status, submitted_at, sale_date, receipt_photo_path)
                           VALUES (?, ?, ?, ?, ?, 'approved', ?, ?, ?)""",
                        (
                            emp_id,
                            round(rev, 2),
                            round(basket, 2),
                            num_items,
                            app_dl,
                            day.strftime("%Y-%m-%d %H:%M:%S"),
                            day.strftime("%Y-%m-%d"),
                            f"uploads/receipts/placeholder_{emp_id}_{day.strftime('%Y%m%d')}.jpg",
                        ),
                    )

    conn.commit()


def seed_app_downloads(conn, employees):
    start_date = datetime(2026, 1, 12)

    for emp_id, archetype, dept_id, store_id in employees:
        if EMPLOYEE_DATA[emp_id - 1][3] == "manager":
            continue

        daily_downloads = {"star": (2, 5), "steady": (1, 3), "growing": (1, 4), "inconsistent": (0, 3), "underperformer": (0, 2)}
        dl_range = daily_downloads[archetype]

        for week in range(8):
            week_start = start_date + timedelta(weeks=week)
            for day_offset in range(6):
                day = week_start + timedelta(days=day_offset)
                if day > datetime(2026, 3, 9):
                    break

                num_downloads = random.randint(*dl_range)
                for j in range(num_downloads):
                    conn.execute(
                        """INSERT INTO app_downloads (employee_id, status, submitted_at, download_date, screenshot_photo_path)
                           VALUES (?, 'approved', ?, ?, ?)""",
                        (
                            emp_id,
                            day.strftime("%Y-%m-%d %H:%M:%S"),
                            day.strftime("%Y-%m-%d"),
                            f"uploads/screenshots/placeholder_{emp_id}_{day.strftime('%Y%m%d')}_{j}.jpg",
                        ),
                    )

    conn.commit()


def seed_attendance(conn, employees, stores_data=STORES):
    """Generate attendance records with GPS coordinates."""
    start_date = datetime(2026, 1, 12)

    for emp_id, archetype, dept_id, store_id in employees:
        if EMPLOYEE_DATA[emp_id - 1][3] == "manager":
            continue

        store_lat = stores_data[store_id - 1][2]
        store_lng = stores_data[store_id - 1][3]

        attendance_rate = {"star": 0.98, "steady": 0.95, "growing": 0.90, "inconsistent": 0.80, "underperformer": 0.75}
        punctuality = {"star": 0.95, "steady": 0.90, "growing": 0.85, "inconsistent": 0.65, "underperformer": 0.60}

        for week in range(8):
            week_start = start_date + timedelta(weeks=week)
            for day_offset in range(6):
                day = week_start + timedelta(days=day_offset)
                if day > datetime(2026, 3, 9):
                    break

                if random.random() > attendance_rate[archetype]:
                    continue

                if random.random() < punctuality[archetype]:
                    punch_in_hour = 8
                    punch_in_min = random.randint(40, 59)
                else:
                    punch_in_hour = 9
                    punch_in_min = random.randint(5, 30)

                punch_in = day.replace(hour=punch_in_hour, minute=punch_in_min)

                punch_out_hour = random.randint(20, 21)
                punch_out_min = random.randint(0, 30)
                punch_out = day.replace(hour=punch_out_hour, minute=punch_out_min)

                hours = (punch_out - punch_in).total_seconds() / 3600

                lat_offset = random.uniform(-0.0005, 0.0005)  # ~50m
                lng_offset = random.uniform(-0.0005, 0.0005)

                conn.execute(
                    """INSERT INTO attendance (employee_id, punch_in_time, punch_out_time,
                       punch_in_lat, punch_in_lng, punch_out_lat, punch_out_lng,
                       punch_in_distance_meters, punch_out_distance_meters,
                       punch_in_status, punch_out_status, hours_worked, attendance_date)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved', 'approved', ?, ?)""",
                    (
                        emp_id,
                        punch_in.strftime("%Y-%m-%d %H:%M:%S"),
                        punch_out.strftime("%Y-%m-%d %H:%M:%S"),
                        store_lat + lat_offset,
                        store_lng + lng_offset,
                        store_lat + lat_offset,
                        store_lng + lng_offset,
                        random.uniform(5, 80),
                        random.uniform(5, 80),
                        round(hours, 2),
                        day.strftime("%Y-%m-%d"),
                    ),
                )

    conn.commit()


def seed_manager_ratings(conn, employees):
    start_date = datetime(2026, 1, 12)
    manager_ids = [eid for eid, arch, did, sid in employees if EMPLOYEE_DATA[eid - 1][3] == "manager"]

    for emp_id, archetype, dept_id, store_id in employees:
        if EMPLOYEE_DATA[emp_id - 1][3] == "manager":
            continue

        rating_base = {"star": 4.2, "steady": 3.8, "growing": 3.5, "inconsistent": 3.0, "underperformer": 2.5}
        base = rating_base[archetype]
        manager_id = manager_ids[0] if store_id == 1 else manager_ids[-1]

        for week in range(8):
            week_start = start_date + timedelta(weeks=week)
            for day_offset in range(6):
                day = week_start + timedelta(days=day_offset)
                if day > datetime(2026, 3, 9):
                    break

                if random.random() < 0.85:
                    rating = min(5, max(1, round(base + random.uniform(-0.8, 0.8))))
                    try:
                        conn.execute(
                            """INSERT INTO manager_ratings (employee_id, manager_id, rating, rating_date)
                               VALUES (?, ?, ?, ?)""",
                            (emp_id, manager_id, rating, day.strftime("%Y-%m-%d")),
                        )
                    except sqlite3.IntegrityError:
                        pass

    conn.commit()


def seed_badges(conn, employees):
    """Assign some badges based on archetype."""
    badge_map = {
        "star": [("target_crusher", "Target Crusher", "🎯"), ("fan_favourite", "Fan Favourite", "⭐")],
        "steady": [("rock_solid", "Rock Solid", "🪨"), ("never_miss", "Never Miss", "✅")],
        "growing": [("on_the_rise", "On The Rise", "📈")],
        "inconsistent": [],
        "underperformer": [],
    }

    for emp_id, archetype, dept_id, store_id in employees:
        if EMPLOYEE_DATA[emp_id - 1][3] == "manager":
            continue

        for badge_type, badge_name, emoji in badge_map.get(archetype, []):
            conn.execute(
                "INSERT INTO badges (employee_id, badge_type, badge_name, badge_emoji) VALUES (?, ?, ?, ?)",
                (emp_id, badge_type, badge_name, emoji),
            )

    conn.commit()


def calculate_xp(conn, employees):
    level_thresholds = [(10000, 5, "Champion"), (6000, 4, "Expert"), (3000, 3, "Performer"), (1000, 2, "Associate"), (0, 1, "Rookie")]
    xp_map = {"star": 8500, "steady": 5500, "growing": 3200, "inconsistent": 1800, "underperformer": 800}

    for emp_id, archetype, dept_id, store_id in employees:
        if EMPLOYEE_DATA[emp_id - 1][3] == "manager":
            continue

        xp = xp_map[archetype] + random.randint(-500, 500)
        xp = max(0, xp)

        level, title = 1, "Rookie"
        for threshold, lvl, ttl in level_thresholds:
            if xp >= threshold:
                level, title = lvl, ttl
                break

        conn.execute(
            "UPDATE employees SET total_xp = ?, level = ?, level_title = ? WHERE id = ?",
            (xp, level, title, emp_id),
        )

    conn.commit()


def main():
    print("🚀 Seeding PerformIQ database...")
    conn = create_db()

    print("  → Stores...")
    seed_stores(conn)

    print("  → Departments...")
    seed_departments(conn)

    print("  → Employees...")
    employees = seed_employees(conn)

    print("  → Sales records (8 weeks)...")
    seed_sales(conn, employees)

    print("  → App downloads...")
    seed_app_downloads(conn, employees)

    print("  → Attendance records...")
    seed_attendance(conn, employees)

    print("  → Manager ratings...")
    seed_manager_ratings(conn, employees)

    print("  → Badges...")
    seed_badges(conn, employees)

    print("  → Calculating XP & levels...")
    calculate_xp(conn, employees)

    cursor = conn.cursor()
    tables = ["stores", "departments", "employees", "sales", "app_downloads", "attendance", "manager_ratings", "badges"]
    print("\n📊 Database Summary:")
    for table in tables:
        count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"   {table}: {count} records")

    conn.close()
    print(f"\n✅ Database seeded at {DB_PATH}")


if __name__ == "__main__":
    main()
