"""Phase 7 — Data Warehouse tables migration.

Creates the wh_* tables and etl_runs table for the Data Warehouse portal.
These are SEPARATE from the existing Phase 5 weekly warehouse tables
(store_weekly_summary, department_weekly_summary, cross_store_weekly_comparison)
which continue to power the HeadOffice analytics views.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "performiq.db"


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def run_warehouse_migration():
    print("Checking Phase 7 data warehouse migration...")
    conn = get_connection()
    c = conn.cursor()

    try:
        # Check if migration already ran
        try:
            c.execute("SELECT * FROM migrations WHERE migration_id = 'phase7_warehouse'")
            if c.fetchone():
                print("Phase 7 warehouse migration already completed. Skipping.")
                conn.close()
                return
        except sqlite3.OperationalError:
            pass

        print("Running Phase 7 warehouse migration...")

        # TABLE 1 — wh_store_summary
        # Daily store-level aggregates for the Data Warehouse dashboard
        c.execute('''
            CREATE TABLE IF NOT EXISTS wh_store_summary (
                id INTEGER PRIMARY KEY,
                store_id TEXT NOT NULL,
                date TEXT NOT NULL,
                avg_p_score REAL NOT NULL DEFAULT 0,
                total_sales REAL NOT NULL DEFAULT 0,
                total_transactions INTEGER NOT NULL DEFAULT 0,
                flag_count INTEGER NOT NULL DEFAULT 0,
                UNIQUE(store_id, date)
            )
        ''')

        # TABLE 2 — wh_employee_fact
        # Daily per-employee scores for drill-down analysis
        c.execute('''
            CREATE TABLE IF NOT EXISTS wh_employee_fact (
                id INTEGER PRIMARY KEY,
                employee_id INTEGER NOT NULL,
                store_id TEXT NOT NULL,
                department TEXT NOT NULL DEFAULT '',
                date TEXT NOT NULL,
                p_score REAL NOT NULL DEFAULT 0,
                cluster_label TEXT,
                xp INTEGER NOT NULL DEFAULT 0,
                UNIQUE(employee_id, date)
            )
        ''')

        # TABLE 3 — wh_dept_benchmark
        # Daily per-department benchmarks with cross-store ranking
        c.execute('''
            CREATE TABLE IF NOT EXISTS wh_dept_benchmark (
                id INTEGER PRIMARY KEY,
                store_id TEXT NOT NULL,
                department TEXT NOT NULL,
                date TEXT NOT NULL,
                avg_p_score REAL NOT NULL DEFAULT 0,
                dept_rank INTEGER NOT NULL DEFAULT 0,
                UNIQUE(store_id, department, date)
            )
        ''')

        # TABLE 4 — wh_flag_log
        # Daily flag type counts per store
        c.execute('''
            CREATE TABLE IF NOT EXISTS wh_flag_log (
                id INTEGER PRIMARY KEY,
                store_id TEXT NOT NULL,
                flag_type TEXT NOT NULL,
                date TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                UNIQUE(store_id, flag_type, date)
            )
        ''')

        # TABLE 5 — etl_runs
        # ETL execution log
        c.execute('''
            CREATE TABLE IF NOT EXISTS etl_runs (
                id INTEGER PRIMARY KEY,
                run_at TEXT NOT NULL,
                stores_processed INTEGER NOT NULL DEFAULT 0,
                rows_inserted INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending'
            )
        ''')

        # Create indexes for query performance
        c.execute('CREATE INDEX IF NOT EXISTS idx_wh_store_summary_date ON wh_store_summary(date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_wh_store_summary_store ON wh_store_summary(store_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_wh_employee_fact_date ON wh_employee_fact(date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_wh_employee_fact_store ON wh_employee_fact(store_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_wh_dept_benchmark_date ON wh_dept_benchmark(date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_wh_flag_log_date ON wh_flag_log(date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_etl_runs_status ON etl_runs(status)')

        # Mark migration complete
        now_str = datetime.now().isoformat()
        c.execute(
            "INSERT OR IGNORE INTO migrations (migration_id, ran_at) VALUES ('phase7_warehouse', ?)",
            (now_str,),
        )

        conn.commit()
        print("Phase 7 warehouse migration completed successfully.")

    except Exception as e:
        conn.rollback()
        print(f"Phase 7 migration failed: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    run_warehouse_migration()
