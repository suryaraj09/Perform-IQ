"""Phase 4 Multi-store Database Migration."""

import sqlite3
import random
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "performiq.db"

def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def run_phase4_migration():
    print("Checking Phase 4 multi-store migration...")
    conn = get_connection()
    c = conn.cursor()
    
    try:
        # Check if phase4_multistore exists in migrations if it exists
        try:
            c.execute("SELECT * FROM migrations WHERE migration_id = 'phase4_multistore'")
            if c.fetchone():
                print("Phase 4 migration already completed. Skipping.")
                conn.close()
                return
        except sqlite3.OperationalError:
            pass
            
        print("Running Phase 4 migration...")
        
        # Step 1: CREATE TABLE migrations
        c.execute("DROP TABLE IF EXISTS migrations")
        c.execute('''
            CREATE TABLE migrations (
                migration_id TEXT PRIMARY KEY,
                ran_at TEXT NOT NULL
            )
        ''')

        c.execute("PRAGMA foreign_keys = OFF")

        # Step 2: Create stores table
        c.execute("DROP TABLE IF EXISTS stores")
        c.execute('''
            CREATE TABLE stores (
                store_id TEXT PRIMARY KEY,
                store_name TEXT NOT NULL,
                store_location TEXT NOT NULL,
                store_lat REAL NOT NULL,
                store_lng REAL NOT NULL,
                geofence_radius INTEGER NOT NULL DEFAULT 100,
                shift_start_time TEXT NOT NULL DEFAULT '09:00',
                shift_end_time TEXT NOT NULL DEFAULT '21:00',
                created_at TEXT NOT NULL
            )
        ''')
        
        now_str = datetime.now().isoformat()
        stores = [
            ('S001', 'Blue Buddha Navrangpura', 'Navrangpura, Ahmedabad', 23.0395, 72.5561, 100, '09:00', '21:00', now_str),
            ('S002', 'Blue Buddha Satellite', 'Satellite, Ahmedabad', 23.0274, 72.5074, 100, '09:00', '21:00', now_str),
            ('S003', 'Blue Buddha Bopal', 'Bopal, Ahmedabad', 23.0354, 72.4673, 100, '09:00', '21:00', now_str),
        ]
        c.executemany("INSERT INTO stores (store_id, store_name, store_location, store_lat, store_lng, geofence_radius, shift_start_time, shift_end_time, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", stores)

        # Step 3: Add store_id to tables
        # The user said: "Only add store_id to: employees, sales, attendance, weekly_scores, geofence_alerts, manager_ratings."
        tables_to_alter = ["employees", "sales", "attendance", "weekly_scores", "geofence_alerts", "manager_ratings"]
        for table in tables_to_alter:
            c.execute(f"PRAGMA table_info({table})")
            columns = [col['name'] for col in c.fetchall()]
            if 'store_id' not in columns:
                c.execute(f"ALTER TABLE {table} ADD COLUMN store_id TEXT DEFAULT 'S001'")
            c.execute(f"UPDATE {table} SET store_id = 'S001' WHERE store_id IS NULL OR store_id = 1")
            
        # Add store_id to departments if needed so new departments have a store_id column that works with text
        c.execute("PRAGMA table_info(departments)")
        dept_cols = [col['name'] for col in c.fetchall()]
        if 'store_id_text' not in dept_cols:
            c.execute("ALTER TABLE departments ADD COLUMN store_id_text TEXT DEFAULT 'S001'")
            c.execute("UPDATE departments SET store_id_text = 'S001' WHERE store_id = 1")

        # Step 4: Create users table
        c.execute("DROP TABLE IF EXISTS users")
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                store_id TEXT,
                employee_id TEXT,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        seed_users = [
            ('U_HO_001', 'headoffice@bluebuddha.com', 'HO@PerformIQ2024', 'HEAD_OFFICE', None, None, 'Head Office Admin', now_str),
            ('U_MGR_S001', 'manager.navrangpura@bluebuddha.com', 'Mgr@S001', 'STORE_MANAGER', 'S001', None, 'Manager Navrangpura', now_str),
            ('U_MGR_S002', 'manager.satellite@bluebuddha.com', 'Mgr@S002', 'STORE_MANAGER', 'S002', None, 'Manager Satellite', now_str),
            ('U_MGR_S003', 'manager.bopal@bluebuddha.com', 'Mgr@S003', 'STORE_MANAGER', 'S003', None, 'Manager Bopal', now_str),
        ]
        
        c.executemany('''
            INSERT OR IGNORE INTO users 
            (user_id, email, password_hash, role, store_id, employee_id, name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', seed_users)

        c.execute("SELECT id, name FROM employees WHERE store_id = 'S001'")
        existing_emps = c.fetchall()
        for emp in existing_emps:
            emp_id = str(emp['id'])
            user_id = f"U_EMP_{emp_id}"
            email = f"{emp_id.lower()}@bluebuddha.com"
            pwd = f"Emp@{emp_id}"
            c.execute('''
                INSERT OR IGNORE INTO users 
                (user_id, email, password_hash, role, store_id, employee_id, name, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, email, pwd, 'EMPLOYEE', 'S001', emp_id, emp['name'], now_str))

        # Step 5: Reseed employees for S002 and S003
        depts = ["Women's Wear", "Men's Wear", "Accessories"]
        names = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Ayaan", "Krishna", "Ishaan", "Shaurya",
                 "Saanvi", "Aanya", "Aadhya", "Aaradhya", "Ananya", "Pari", "Diya", "Navya", "Myra", "Kavya"]
        
        c.execute("SELECT count(*) as c FROM employees WHERE store_id = 'S002'")
        if c.fetchone()['c'] == 0:
            departments_map = {}
            for store_id in ['S002', 'S003']:
                departments_map[store_id] = {}
                for d_name in depts:
                    # check if department exists
                    c.execute("SELECT id FROM departments WHERE name = ? AND store_id_text = ?", (d_name, store_id))
                    res = c.fetchone()
                    if res:
                        departments_map[store_id][d_name] = res['id']
                    else:
                        c.execute("INSERT INTO departments (store_id, name, store_id_text) VALUES (0, ?, ?)", (d_name, store_id))
                        departments_map[store_id][d_name] = c.lastrowid

            random.seed(42)
            
            def generate_employee(store_id, idx, is_s002):
                name = random.choice(names) + f" {idx}"
                dept = random.choice(depts)
                dept_id = departments_map[store_id][dept]
                
                c.execute('''
                    INSERT INTO employees (name, role, department_id, store_id, total_xp, level, level_title, is_active, status, created_at)
                    VALUES (?, 'employee', ?, ?, 0, 1, 'Rookie', 1, 'approved', ?)
                ''', (name, dept_id, store_id, now_str))
                emp_id = str(c.lastrowid)
                
                user_id = f"U_EMP_{emp_id}"
                email = f"{emp_id.lower()}@bluebuddha.com"
                pwd = f"Emp@{emp_id}"
                c.execute('''
                    INSERT INTO users 
                    (user_id, email, password_hash, role, store_id, employee_id, name, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, email, pwd, 'EMPLOYEE', store_id, emp_id, name, now_str))
                
                current_year = 2026
                current_week = 14
                start_week = current_week - 8
                
                if is_s002: # Satellite
                    m1_base = random.randint(60, 95)
                    m2_base = random.randint(50, 80)
                    m7_base = random.randint(70, 90)
                else: # Bopal
                    m1_base = random.randint(40, 60)
                    m2_base = random.randint(40, 70)
                    m7_base = random.randint(85, 100)
                
                for w in range(start_week, current_week):
                    if is_s002:
                        m1 = max(0, min(100, m1_base + random.randint(-10, 10)))
                        m2 = max(0, min(100, m2_base + random.randint(-10, 10)))
                        m4 = random.randint(40, 60)
                    else:
                        m1 = max(0, min(100, m1_base + (w - start_week) * 3 + random.randint(-5, 5)))
                        m2 = max(0, min(100, m2_base + random.randint(-5, 5)))
                        m4 = random.randint(70, 95)
                        
                    m3 = random.randint(70, 100)
                    m5 = random.randint(60, 95)
                    m7 = max(0, min(100, m7_base + random.randint(-5, 5)))
                    m8 = max(0, min(100, m7_base + random.randint(-10, 5)))
                    
                    p = (0.30*m1) + (0.25*m2) + (0.15*m3) + (0.10*m4) + (0.10*m5) + (0.05*m7) + (0.05*m8)
                    p = max(0, min(100, p))
                    
                    c.execute('''
                        INSERT INTO weekly_scores (employee_id, store_id, department, week_number, year, M1, M2, M3, M4, M5, M7, M8, P_score, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (emp_id, store_id, dept, w, current_year, m1, m2, m3, m4, m5, m7, m8, p, now_str))

            for i in range(10):
                generate_employee('S002', i+1, True)
                
            for i in range(10):
                generate_employee('S003', i+1, False)

        # Step 6: Mark migration complete
        c.execute("INSERT INTO migrations (migration_id, ran_at) VALUES ('phase4_multistore', ?)", (now_str,))
        
        c.execute("PRAGMA foreign_keys = ON")
        conn.commit()
        print("Phase 4 migration completed successfully.")
        
    except Exception as e:
        conn.rollback()
        import traceback
        traceback.print_exc()
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_phase4_migration()
