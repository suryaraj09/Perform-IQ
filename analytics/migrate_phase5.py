"""Phase 5 Data Warehouse Database Migration."""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "performiq.db"

def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def run_phase5_migration():
    print("Checking Phase 5 data warehouse migration...")
    conn = get_connection()
    c = conn.cursor()
    
    try:
        # Check if migration already ran
        try:
            c.execute("SELECT * FROM migrations WHERE migration_id = 'phase5_warehouse'")
            if c.fetchone():
                print("Phase 5 migration already completed. Skipping.")
                conn.close()
                return
        except sqlite3.OperationalError:
            # Table migrations might not exist if init_db was never called (shouldn't happen here)
            pass
            
        print("Running Phase 5 migration...")
        
        # TABLE 1 — store_weekly_summary
        c.execute('''
            CREATE TABLE IF NOT EXISTS store_weekly_summary (
                summary_id TEXT PRIMARY KEY,
                store_id TEXT NOT NULL,
                week_number INTEGER NOT NULL,
                year INTEGER NOT NULL,
                total_revenue REAL NOT NULL DEFAULT 0,
                avg_p_score REAL NOT NULL DEFAULT 0,
                top_performer_id TEXT,
                top_performer_name TEXT,
                top_performer_score REAL,
                total_employees_active INTEGER NOT NULL DEFAULT 0,
                total_sales_logged INTEGER NOT NULL DEFAULT 0,
                avg_attendance_rate REAL NOT NULL DEFAULT 0,
                avg_punctuality_score REAL NOT NULL DEFAULT 0,
                total_flagged_sales INTEGER NOT NULL DEFAULT 0,
                total_geofence_alerts INTEGER NOT NULL DEFAULT 0,
                employees_above_target INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(store_id, week_number, year)
            )
        ''')

        # TABLE 2 — department_weekly_summary
        c.execute('''
            CREATE TABLE IF NOT EXISTS department_weekly_summary (
                summary_id TEXT PRIMARY KEY,
                store_id TEXT NOT NULL,
                department TEXT NOT NULL,
                week_number INTEGER NOT NULL,
                year INTEGER NOT NULL,
                dept_avg_revenue REAL NOT NULL DEFAULT 0,
                dept_avg_basket_size REAL NOT NULL DEFAULT 0,
                dept_avg_p_score REAL NOT NULL DEFAULT 0,
                dept_avg_attendance REAL NOT NULL DEFAULT 0,
                headcount INTEGER NOT NULL DEFAULT 0,
                employees_above_target INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(store_id, department, week_number, year)
            )
        ''')

        # TABLE 3 — cross_store_weekly_comparison
        c.execute('''
            CREATE TABLE IF NOT EXISTS cross_store_weekly_comparison (
                comparison_id TEXT PRIMARY KEY,
                week_number INTEGER NOT NULL,
                year INTEGER NOT NULL,
                store_id TEXT NOT NULL,
                store_rank INTEGER NOT NULL,
                avg_p_score REAL NOT NULL DEFAULT 0,
                total_revenue REAL NOT NULL DEFAULT 0,
                avg_attendance_rate REAL NOT NULL DEFAULT 0,
                top_performer_name TEXT,
                top_performer_score REAL,
                revenue_rank INTEGER NOT NULL,
                attendance_rank INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(store_id, week_number, year)
            )
        ''')

        # Mark migration complete
        now_str = datetime.now().isoformat()
        c.execute("INSERT OR IGNORE INTO migrations (migration_id, ran_at) VALUES ('phase5_warehouse', ?)", (now_str,))
        
        conn.commit()
        print("Phase 5 migration completed successfully.")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_phase5_migration()
