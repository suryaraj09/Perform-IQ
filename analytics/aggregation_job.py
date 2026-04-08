"""Aggregation job for PerformIQ — populates warehouse tables from operational data."""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3

# Ensure we can import from parent and current dir
sys.path.insert(0, str(Path(__file__).parent))

from database import query, execute, execute_many

def get_week_range(week_number, year):
    """Get the Monday to Sunday date range for a given ISO week and year."""
    # First day of the year
    jan1 = datetime(year, 1, 1)
    # ISO week 1 is the week with the first Thursday.
    # We find the first Monday of the week containing Jan 4th.
    jan4 = datetime(year, 1, 4)
    start_of_year_week = jan4 - timedelta(days=jan4.isocalendar()[2] - 1)
    
    start_date = start_of_year_week + timedelta(weeks=week_number - 1)
    end_date = start_date + timedelta(days=6)
    
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

def run_weekly_aggregation(week_number: int, year: int):
    """Aggregate data for a specific week and year into the warehouse tables."""
    print(f"Running aggregation for W{week_number} {year}...")
    start_date, end_date = get_week_range(week_number, year)
    now_str = datetime.now().isoformat()
    
    # Get all active stores
    stores = query("SELECT store_id, store_name FROM stores")
    
    # 1. STORE WEEKLY SUMMARY
    for store in stores:
        sid = store['store_id']
        
        # Aggregates from weekly_scores (Operational analytics table)
        # Note: In our Phase 4 system, P_score and M1..M8 are computed in weekly_scores.
        # We also need RAW revenue and headcount.
        
        # Raw revenue and sales count from sales table
        # We filter sales by date range and store_id
        sales_stats = query('''
            SELECT 
                COALESCE(SUM(revenue), 0) as total_rev,
                COUNT(*) as sales_count
            FROM sales 
            WHERE store_id = ? 
            AND sale_date BETWEEN ? AND ?
            AND status = 'approved'
        ''', (sid, start_date, end_date), one=True)
        
        # Productivity scores from weekly_scores
        scores_stats = query('''
            SELECT 
                AVG(P_score) as avg_p,
                AVG(M7) as avg_att,
                AVG(M8) as avg_punct,
                COUNT(employee_id) as headcount,
                SUM(CASE WHEN M1 >= 100 THEN 1 ELSE 0 END) as above_target
            FROM weekly_scores
            WHERE store_id = ? AND week_number = ? AND year = ?
        ''', (sid, week_number, year), one=True)
        
        # Top performer for this store this week
        top_perf = query('''
            SELECT e.id, e.name, ws.P_score
            FROM weekly_scores ws
            JOIN employees e ON ws.employee_id = e.id
            WHERE ws.store_id = ? AND ws.week_number = ? AND ws.year = ?
            ORDER BY ws.P_score DESC LIMIT 1
        ''', (sid, week_number, year), one=True)
        
        # Alerts
        geofence_count = query('''
            SELECT COUNT(*) as c FROM geofence_alerts 
            WHERE store_id = ? AND created_at BETWEEN ? AND ?
        ''', (sid, start_date + "T00:00:00", end_date + "T23:59:59"), one=True)
        
        flagged_count = query('''
            SELECT COUNT(*) as c FROM sales 
            WHERE store_id = ? AND is_flagged = 1
            AND sale_date BETWEEN ? AND ?
        ''', (sid, start_date, end_date), one=True)

        summary_id = f"{sid}_W{week_number}_{year}"
        
        execute('''
            INSERT OR REPLACE INTO store_weekly_summary (
                summary_id, store_id, week_number, year, total_revenue, avg_p_score,
                top_performer_id, top_performer_name, top_performer_score,
                total_employees_active, total_sales_logged, avg_attendance_rate,
                avg_punctuality_score, total_flagged_sales, total_geofence_alerts,
                employees_above_target, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            summary_id, sid, week_number, year, 
            sales_stats['total_rev'], scores_stats['avg_p'] or 0,
            str(top_perf['id']) if top_perf else None, 
            top_perf['name'] if top_perf else None,
            top_perf['P_score'] if top_perf else 0,
            scores_stats['headcount'] or 0,
            sales_stats['sales_count'],
            scores_stats['avg_att'] or 0,
            scores_stats['avg_punct'] or 0,
            flagged_count['c'],
            geofence_count['c'],
            scores_stats['above_target'] or 0,
            now_str, now_str
        ))

    # 2. DEPARTMENT WEEKLY SUMMARY
    departments = ["Women's Wear", "Men's Wear", "Accessories"]
    for store in stores:
        sid = store['store_id']
        for dept in departments:
            dept_stats = query('''
                SELECT 
                    AVG(P_score) as avg_p,
                    AVG(M1) as avg_m1, -- revenue vs target placeholder if needed
                    AVG(M2) as avg_basket, -- normalized basket
                    AVG(M7) as avg_att,
                    COUNT(employee_id) as headcount,
                    SUM(CASE WHEN M1 >= 100 THEN 1 ELSE 0 END) as above_target
                FROM weekly_scores
                WHERE store_id = ? AND department = ? AND week_number = ? AND year = ?
            ''', (sid, dept, week_number, year), one=True)
            
            # Raw avg revenue for dept
            raw_rev = query('''
                SELECT AVG(revenue) as avg_rev, AVG(basket_size) as avg_basket_size
                FROM sales s
                JOIN employees e ON s.employee_id = e.id
                WHERE e.store_id = ? AND e.department_id = (SELECT id FROM departments WHERE name = ? LIMIT 1)
                AND s.sale_date BETWEEN ? AND ?
                AND s.status = 'approved'
            ''', (sid, dept, start_date, end_date), one=True)

            summary_id = f"{sid}_{dept.replace(' ', '_')}_W{week_number}_{year}"
            
            execute('''
                INSERT OR REPLACE INTO department_weekly_summary (
                    summary_id, store_id, department, week_number, year,
                    dept_avg_revenue, dept_avg_basket_size, dept_avg_p_score,
                    dept_avg_attendance, headcount, employees_above_target,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                summary_id, sid, dept, week_number, year,
                raw_rev['avg_rev'] or 0,
                raw_rev['avg_basket_size'] or 0,
                dept_stats['avg_p'] or 0,
                dept_stats['avg_att'] or 0,
                dept_stats['headcount'] or 0,
                dept_stats['above_target'] or 0,
                now_str, now_str
            ))

    # 3. CROSS-STORE WEEKLY COMPARISON (Ranking)
    summaries = query('''
        SELECT * FROM store_weekly_summary 
        WHERE week_number = ? AND year = ?
    ''', (week_number, year))
    
    if summaries:
        # Sort for ranking
        by_p = sorted(summaries, key=lambda x: x['avg_p_score'], reverse=True)
        by_rev = sorted(summaries, key=lambda x: x['total_revenue'], reverse=True)
        by_att = sorted(summaries, key=lambda x: x['avg_attendance_rate'], reverse=True)
        
        ranks_map = {s['store_id']: {
            'p_rank': i + 1,
            'rev_rank': 0,
            'att_rank': 0
        } for i, s in enumerate(by_p)}
        
        for i, s in enumerate(by_rev):
            ranks_map[s['store_id']]['rev_rank'] = i + 1
        for i, s in enumerate(by_att):
            ranks_map[s['store_id']]['att_rank'] = i + 1
            
        for s in summaries:
            sid = s['store_id']
            comparison_id = f"{sid}_W{week_number}_{year}"
            
            execute('''
                INSERT OR REPLACE INTO cross_store_weekly_comparison (
                    comparison_id, week_number, year, store_id, store_rank,
                    avg_p_score, total_revenue, avg_attendance_rate,
                    top_performer_name, top_performer_score,
                    revenue_rank, attendance_rank, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                comparison_id, week_number, year, sid, ranks_map[sid]['p_rank'],
                s['avg_p_score'], s['total_revenue'], s['avg_attendance_rate'],
                s['top_performer_name'], s['top_performer_score'],
                ranks_map[sid]['rev_rank'], ranks_map[sid]['att_rank'],
                now_str, now_str
            ))

    print(f"Aggregation complete for W{week_number} {year} — {datetime.now().isoformat()}")

def get_current_week():
    cal = datetime.now().isocalendar()
    return cal[1], cal[0]

if __name__ == "__main__":
    w, y = get_current_week()
    run_weekly_aggregation(w, y)
