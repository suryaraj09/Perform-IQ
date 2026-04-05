-- PerformIQ Database Schema
-- SQLite

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- Stores
CREATE TABLE IF NOT EXISTS stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    geofence_radius_meters REAL NOT NULL DEFAULT 100,
    shift_start_time TEXT NOT NULL DEFAULT '09:00',
    shift_end_time TEXT NOT NULL DEFAULT '21:00',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Departments
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    weekly_revenue_target REAL NOT NULL DEFAULT 0,
    avg_basket_size REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (store_id) REFERENCES stores(id)
);

-- Employees
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    phone TEXT,
    role TEXT NOT NULL CHECK(role IN ('employee', 'manager')) DEFAULT 'employee',
    department_id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    firebase_uid TEXT,
    total_xp INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 1,
    level_title TEXT NOT NULL DEFAULT 'Rookie',
    profile_photo_path TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL CHECK(status IN ('pending', 'approved', 'rejected')) DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (department_id) REFERENCES departments(id),
    FOREIGN KEY (store_id) REFERENCES stores(id)
);

-- Per-sale records
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    revenue REAL NOT NULL,
    basket_size REAL NOT NULL,
    num_items INTEGER NOT NULL DEFAULT 1,
    receipt_photo_path TEXT,
    status TEXT NOT NULL CHECK(status IN ('pending', 'approved', 'rejected')) DEFAULT 'pending',
    rejection_reason TEXT,
    reviewed_by INTEGER,
    reviewed_at TEXT,
    is_flagged INTEGER NOT NULL DEFAULT 0,
    flags TEXT DEFAULT '[]',
    resolved_by_admin INTEGER NOT NULL DEFAULT 0,
    admin_action TEXT,
    resolved_at TEXT,
    auto_confirmed_at TEXT,
    submitted_at TEXT NOT NULL DEFAULT (datetime('now')),
    sale_date TEXT NOT NULL DEFAULT (date('now')),
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (reviewed_by) REFERENCES employees(id)
);



-- Attendance
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    punch_in_time TEXT,
    punch_out_time TEXT,
    punch_in_lat REAL,
    punch_in_lng REAL,
    punch_out_lat REAL,
    punch_out_lng REAL,
    punch_in_distance_meters REAL,
    punch_out_distance_meters REAL,
    punch_in_status TEXT CHECK(punch_in_status IN ('approved', 'rejected')),
    punch_out_status TEXT CHECK(punch_out_status IN ('approved', 'rejected')),
    hours_worked REAL,
    attendance_date TEXT NOT NULL DEFAULT (date('now')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

-- Manager daily ratings
CREATE TABLE IF NOT EXISTS manager_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    manager_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
    notes TEXT,
    rating_date TEXT NOT NULL DEFAULT (date('now')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (manager_id) REFERENCES employees(id),
    UNIQUE(employee_id, rating_date)
);

-- Badges
CREATE TABLE IF NOT EXISTS badges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    badge_type TEXT NOT NULL,
    badge_name TEXT NOT NULL,
    badge_emoji TEXT,
    earned_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

-- Geofence Alerts
CREATE TABLE IF NOT EXISTS geofence_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    employee_name TEXT NOT NULL,
    punch_in_time TEXT NOT NULL,
    first_fail_time TEXT NOT NULL,
    second_fail_time TEXT NOT NULL,
    alert_type TEXT NOT NULL DEFAULT 'GEOFENCE_ABSENCE',
    resolved INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_sales_employee ON sales(employee_id);
CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(sale_date);
CREATE INDEX IF NOT EXISTS idx_sales_status ON sales(status);
CREATE INDEX IF NOT EXISTS idx_attendance_employee ON attendance(employee_id);
CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(attendance_date);
CREATE INDEX IF NOT EXISTS idx_manager_ratings_employee ON manager_ratings(employee_id);
CREATE INDEX IF NOT EXISTS idx_badges_employee ON badges(employee_id);
CREATE INDEX IF NOT EXISTS idx_geofence_alerts_employee ON geofence_alerts(employee_id);
CREATE INDEX IF NOT EXISTS idx_geofence_alerts_resolved ON geofence_alerts(resolved);
