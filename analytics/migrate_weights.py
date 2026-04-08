"""One-time migration to recalculate P scores with new 7-metric weights.

New weights (M6 removed, others adjusted):
  M1 Revenue vs Target:     0.30 (unchanged)
  M2 Basket Performance:    0.25 (was 0.20)
  M3 Manager Rating:        0.15 (unchanged)
  M4 Growth Trend:          0.10 (unchanged)
  M5 Stability Index:       0.10 (unchanged)
  M7 Attendance Rate:       0.05 (was 0.03)
  M8 Punctuality Score:     0.05 (was 0.02)
  Total:                    1.00
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database import query, execute, get_connection
from metrics.productivity import compute_productivity_index


MIGRATION_NAME = "recalculate_weights_v2"


def _ensure_migrations_table():
    """Create migrations table if it doesn't exist."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                migration_id TEXT PRIMARY KEY,
                ran_at TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def _is_migration_applied() -> bool:
    """Check if this migration has already been applied."""
    row = query("SELECT migration_id FROM migrations WHERE migration_id = ?", (MIGRATION_NAME,), one=True)
    return row is not None


def _mark_migration_applied():
    """Record that this migration was applied."""
    from datetime import datetime
    execute("INSERT INTO migrations (migration_id, ran_at) VALUES (?, ?)", (MIGRATION_NAME, datetime.now().isoformat()))


def run_migration():
    """Recalculate P scores for all employees using new weights.
    
    This is a run-once migration. It checks a flag in the database
    and skips if already applied.
    """
    _ensure_migrations_table()

    if _is_migration_applied():
        print(f"[migrate] '{MIGRATION_NAME}' already applied — skipping.")
        return

    print(f"[migrate] Running '{MIGRATION_NAME}'...")

    # Get all active employees
    employees = query(
        "SELECT id FROM employees WHERE role = 'employee' AND is_active = 1"
    )

    if not employees:
        print("[migrate] No employees found — marking as applied.")
        _mark_migration_applied()
        return

    from datetime import datetime, timedelta

    # Use full date range for recalculation
    start_date = "2026-01-12"
    end_date = datetime.now().strftime("%Y-%m-%d")

    updated = 0
    for emp in employees:
        try:
            score_data = compute_productivity_index(emp["id"], start_date, end_date)
            # The new weights are already applied inside compute_productivity_index
            # We just log the recalculation
            updated += 1
            print(f"  [migrate] Employee {emp['id']}: P = {score_data['productivity_index']}")
        except Exception as e:
            print(f"  [migrate] Employee {emp['id']}: error — {e}")

    _mark_migration_applied()
    print(f"[migrate] '{MIGRATION_NAME}' complete. Recalculated {updated} employee scores.")


if __name__ == "__main__":
    run_migration()
