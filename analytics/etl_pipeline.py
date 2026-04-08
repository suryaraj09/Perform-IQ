"""ETL Pipeline for PerformIQ Data Warehouse.

Reads from store-level operational tables, computes daily aggregates,
and inserts into the wh_* warehouse tables.

Designed to be run daily via cron:
  0 0 * * * python etl_pipeline.py

Idempotent — uses INSERT OR REPLACE so re-running for the same date is safe.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from database import query, execute, get_connection


def run_etl(target_date: str = None):
    """Run the ETL pipeline for the given date (defaults to yesterday)."""
    if target_date is None:
        yesterday = datetime.now() - timedelta(days=1)
        target_date = yesterday.strftime("%Y-%m-%d")

    run_start = datetime.now().isoformat()
    total_rows = 0
    stores_processed = 0

    print(f"ETL Pipeline started for date: {target_date}")

    try:
        # Get all active stores
        stores = query("SELECT store_id, store_name FROM stores")
        if not stores:
            print("No stores found. ETL aborted.")
            _log_run(run_start, 0, 0, "error")
            return

        stores_processed = len(stores)

        # ------------------------------------------------------------------
        # 1. wh_store_summary — per-store daily aggregates
        # ------------------------------------------------------------------
        for store in stores:
            sid = store["store_id"]

            # Total sales revenue and transaction count
            sales_agg = query(
                """SELECT COALESCE(SUM(revenue), 0) as total_sales,
                          COUNT(*) as total_transactions
                   FROM sales
                   WHERE store_id = ? AND sale_date = ? AND status = 'approved'""",
                (sid, target_date),
                one=True,
            )

            # Average P-score from weekly_scores (closest match for this date)
            # weekly_scores are keyed by week_number/year, so we find the week
            # for target_date and use that.
            from datetime import datetime as dt_cls
            td = dt_cls.strptime(target_date, "%Y-%m-%d")
            iso = td.isocalendar()
            week_num = iso[1]
            year_num = iso[0]

            p_score_agg = query(
                """SELECT COALESCE(AVG(P_score), 0) as avg_p
                   FROM weekly_scores
                   WHERE store_id = ? AND week_number = ? AND year = ?""",
                (sid, week_num, year_num),
                one=True,
            )

            # Flag count for this day
            flag_agg = query(
                """SELECT COUNT(*) as flag_count
                   FROM sales
                   WHERE store_id = ? AND sale_date = ? AND is_flagged = 1""",
                (sid, target_date),
                one=True,
            )

            execute(
                """INSERT OR REPLACE INTO wh_store_summary
                   (store_id, date, avg_p_score, total_sales, total_transactions, flag_count)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    sid,
                    target_date,
                    round(p_score_agg["avg_p"] or 0, 2),
                    round(sales_agg["total_sales"] or 0, 2),
                    sales_agg["total_transactions"] or 0,
                    flag_agg["flag_count"] or 0,
                ),
            )
            total_rows += 1

        # ------------------------------------------------------------------
        # 2. wh_employee_fact — per-employee daily scores
        # ------------------------------------------------------------------
        # Join weekly_scores with employees to get department
        emp_facts = query(
            """SELECT ws.employee_id, ws.store_id, ws.department,
                      ws.P_score, e.total_xp as xp
               FROM weekly_scores ws
               JOIN employees e ON ws.employee_id = e.id
               WHERE ws.week_number = ? AND ws.year = ?""",
            (week_num, year_num),
        )

        for ef in emp_facts:
            # Note: cluster_label is not stored in weekly_scores.
            # Clustering is computed on-the-fly by metrics/clustering.py.
            # Set to None until clustering results are persisted to a table.
            cluster_label = None

            execute(
                """INSERT OR REPLACE INTO wh_employee_fact
                   (employee_id, store_id, department, date, p_score, cluster_label, xp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    ef["employee_id"],
                    ef["store_id"],
                    ef["department"] or "",
                    target_date,
                    round(ef["P_score"] or 0, 2),
                    cluster_label,
                    ef["xp"] or 0,
                ),
            )
            total_rows += 1

        # ------------------------------------------------------------------
        # 3. wh_dept_benchmark — per-department avg P-score with ranking
        # ------------------------------------------------------------------
        dept_scores = query(
            """SELECT store_id, department, AVG(P_score) as avg_p
               FROM weekly_scores
               WHERE week_number = ? AND year = ?
               GROUP BY store_id, department
               ORDER BY department, avg_p DESC""",
            (week_num, year_num),
        )

        # Group by department for ranking
        dept_groups = {}
        for ds in dept_scores:
            dept = ds["department"]
            if dept not in dept_groups:
                dept_groups[dept] = []
            dept_groups[dept].append(ds)

        for dept, entries in dept_groups.items():
            # Entries are already sorted by avg_p DESC
            for rank, entry in enumerate(entries, start=1):
                execute(
                    """INSERT OR REPLACE INTO wh_dept_benchmark
                       (store_id, department, date, avg_p_score, dept_rank)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        entry["store_id"],
                        dept,
                        target_date,
                        round(entry["avg_p"] or 0, 2),
                        rank,
                    ),
                )
                total_rows += 1

        # ------------------------------------------------------------------
        # 4. wh_flag_log — flag type counts per store per day
        # ------------------------------------------------------------------
        flagged_sales = query(
            """SELECT store_id, flags
               FROM sales
               WHERE sale_date = ? AND is_flagged = 1 AND flags IS NOT NULL""",
            (target_date,),
        )

        # Count flag types per store
        flag_counts = {}  # {(store_id, flag_type): count}
        for fs in flagged_sales:
            sid = fs["store_id"]
            try:
                flags_list = json.loads(fs["flags"]) if fs["flags"] else []
            except (json.JSONDecodeError, TypeError):
                flags_list = []

            for flag in flags_list:
                flag_type = flag.get("rule", "UNKNOWN") if isinstance(flag, dict) else str(flag)
                key = (sid, flag_type)
                flag_counts[key] = flag_counts.get(key, 0) + 1

        for (sid, flag_type), count in flag_counts.items():
            execute(
                """INSERT OR REPLACE INTO wh_flag_log
                   (store_id, flag_type, date, count)
                   VALUES (?, ?, ?, ?)""",
                (sid, flag_type, target_date, count),
            )
            total_rows += 1

        # Log successful run
        _log_run(run_start, stores_processed, total_rows, "success")
        print(f"ETL Pipeline completed: {stores_processed} stores, {total_rows} rows inserted.")

    except Exception as e:
        print(f"ETL Pipeline error: {e}")
        _log_run(run_start, stores_processed, total_rows, "error")
        raise


def _log_run(run_at: str, stores_processed: int, rows_inserted: int, status: str):
    """Log an ETL run into etl_runs table."""
    try:
        execute(
            """INSERT INTO etl_runs (run_at, stores_processed, rows_inserted, status)
               VALUES (?, ?, ?, ?)""",
            (run_at, stores_processed, rows_inserted, status),
        )
    except Exception as e:
        print(f"Failed to log ETL run: {e}")


if __name__ == "__main__":
    # Allow optional date argument: python etl_pipeline.py 2026-04-05
    import sys as _sys

    date_arg = _sys.argv[1] if len(_sys.argv) > 1 else None
    run_etl(date_arg)
