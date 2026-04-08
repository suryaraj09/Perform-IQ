
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics.database import query, execute, get_connection
from analytics.metrics.productivity import compute_productivity_index

def get_week_range(week, year):
    # Get Monday of that week
    first_day_of_year = datetime(year, 1, 1)
    # week 1 is the week with the first Thursday
    # For simplicity, we'll use a more robust calculation
    # ISO week starts on Monday
    monday = datetime.strptime(f'{year}-W{week}-1', "%G-W%V-%u")
    sunday = monday + timedelta(days=6)
    return monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")

def backfill_all_scores():
    print("🔄 Starting weekly_scores backfill...")
    
    # Get all employees
    employees = query("SELECT id, store_id, department_id, (SELECT name FROM departments WHERE id = department_id) as dept_name FROM employees WHERE role = 'employee' AND is_active = 1")
    
    # Get range of weeks to calculate
    # Start from 2026-01-12 (as seen in seed_data)
    start_date = datetime(2026, 1, 12)
    today = datetime.now()
    
    current_date = start_date
    weeks_to_process = []
    
    while current_date <= today:
        year, week, _ = current_date.isocalendar()
        if (week, year) not in weeks_to_process:
            weeks_to_process.append((week, year))
        current_date += timedelta(days=7)
        
    print(f"  → Processing {len(weeks_to_process)} weeks for {len(employees)} employees...")
    
    total_inserted = 0
    for week, year in weeks_to_process:
        ws, we = get_week_range(week, year)
        
        for emp in employees:
            scores = compute_productivity_index(emp["id"], ws, we)
            m = scores["metrics"]
            
            execute(
                """INSERT OR REPLACE INTO weekly_scores 
                   (employee_id, store_id, department, week_number, year, M1, M2, M3, M4, M5, M7, M8, P_score) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    emp["id"], emp["store_id"], emp["dept_name"], week, year,
                    m.get("revenue_vs_target"),
                    m.get("basket_performance"),
                    m.get("manager_rating"),
                    m.get("growth_trend"),
                    m.get("stability_index"),
                    m.get("attendance_rate"),
                    m.get("punctuality"),
                    scores["productivity_index"]
                )
            )
            total_inserted += 1
            
    print(f"✅ Backfill complete. Inserted/Updated {total_inserted} records.")

if __name__ == "__main__":
    backfill_all_scores()
