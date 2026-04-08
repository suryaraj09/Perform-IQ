"""Productivity Index computation — weighted 0-100 score computed on-demand."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from database import query


def get_revenue_vs_target(employee_id: int, start_date: str, end_date: str) -> float:
    """Revenue vs Target % (weight: 30%)."""
    # Get employee's department target
    dept = query(
        """SELECT d.weekly_revenue_target FROM employees e 
           JOIN departments d ON e.department_id = d.id WHERE e.id = ?""",
        (employee_id,), one=True
    )
    if not dept or dept["weekly_revenue_target"] == 0:
        return 0

    # Get total approved revenue in date range
    result = query(
        """SELECT COALESCE(SUM(revenue), 0) as total_revenue FROM sales 
           WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?""",
        (employee_id, start_date, end_date), one=True
    )

    # Calculate weeks in range
    from datetime import datetime
    d1 = datetime.strptime(start_date, "%Y-%m-%d")
    d2 = datetime.strptime(end_date, "%Y-%m-%d")
    weeks = max(1, (d2 - d1).days / 7)

    weekly_revenue = result["total_revenue"] / weeks
    ratio = weekly_revenue / dept["weekly_revenue_target"]
    return min(100, ratio * 100)


def get_basket_performance_index(employee_id: int, start_date: str, end_date: str) -> float:
    """Basket Performance Index — employee avg vs department avg (weight: 25%)."""
    # Employee average basket
    emp_avg = query(
        """SELECT COALESCE(AVG(basket_size), 0) as avg_basket FROM sales 
           WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?""",
        (employee_id, start_date, end_date), one=True
    )

    # Department average
    dept_avg = query(
        """SELECT d.avg_basket_size FROM employees e 
           JOIN departments d ON e.department_id = d.id WHERE e.id = ?""",
        (employee_id,), one=True
    )

    if not dept_avg or dept_avg["avg_basket_size"] == 0:
        return 0

    ratio = emp_avg["avg_basket"] / dept_avg["avg_basket_size"]
    return min(100, ratio * 100)


def get_manager_rating_score(employee_id: int, start_date: str, end_date: str) -> float:
    """Manager Rating Score — avg of daily ratings (weight: 15%)."""
    result = query(
        """SELECT COALESCE(AVG(rating), 0) as avg_rating FROM manager_ratings 
           WHERE employee_id = ? AND rating_date BETWEEN ? AND ?""",
        (employee_id, start_date, end_date), one=True
    )
    if not result or result["avg_rating"] == 0:
        return 0
    return (result["avg_rating"] / 5) * 100




def get_attendance_rate(employee_id: int, start_date: str, end_date: str) -> float:
    """Attendance Rate (weight: 5%)."""
    from datetime import datetime
    d1 = datetime.strptime(start_date, "%Y-%m-%d")
    d2 = datetime.strptime(end_date, "%Y-%m-%d")
    total_days = max(1, sum(1 for i in range((d2 - d1).days + 1)
                           if (d1 + __import__("datetime").timedelta(days=i)).weekday() < 6))

    present = query(
        """SELECT COUNT(*) as count FROM attendance 
           WHERE employee_id = ? AND punch_in_status = 'approved' AND attendance_date BETWEEN ? AND ?""",
        (employee_id, start_date, end_date), one=True
    )

    rate = present["count"] / total_days
    return min(100, rate * 100)


def get_punctuality_score(employee_id: int, start_date: str, end_date: str) -> float:
    """Punctuality Score — on-time check-ins (weight: 5%)."""
    records = query(
        """SELECT punch_in_time FROM attendance 
           WHERE employee_id = ? AND punch_in_status = 'approved' AND attendance_date BETWEEN ? AND ?""",
        (employee_id, start_date, end_date)
    )

    if not records:
        return 0

    from datetime import datetime
    on_time = 0
    for r in records:
        punch_time = datetime.strptime(r["punch_in_time"], "%Y-%m-%d %H:%M:%S")
        if punch_time.hour < 9 or (punch_time.hour == 9 and punch_time.minute == 0):
            on_time += 1

    return (on_time / len(records)) * 100


def compute_productivity_index(employee_id: int, start_date: str, end_date: str) -> dict:
    """Compute the full Productivity Index with all metric breakdowns."""
    from metrics.stability import get_stability_index
    from metrics.growth import get_growth_trend
    from config_service import get_config

    metrics = {
        "revenue_vs_target": get_revenue_vs_target(employee_id, start_date, end_date),
        "basket_performance": get_basket_performance_index(employee_id, start_date, end_date),
        "manager_rating": get_manager_rating_score(employee_id, start_date, end_date),
        "growth_trend": get_growth_trend(employee_id, start_date, end_date),
        "stability_index": get_stability_index(employee_id, start_date, end_date),
        "attendance_rate": get_attendance_rate(employee_id, start_date, end_date),
        "punctuality": get_punctuality_score(employee_id, start_date, end_date),
    }

    # Fetch dynamic weights from DB
    db_weights = get_config('METRIC_WEIGHTS')
    
    # Map DB shorthand keys to metric names
    weights_map = {
        "M1": "revenue_vs_target",
        "M2": "basket_performance",
        "M3": "manager_rating",
        "M4": "growth_trend",
        "M5": "stability_index",
        "M7": "attendance_rate",
        "M8": "punctuality",
    }
    
    # Construct final weights dict for the response and calculation
    active_weights = {weights_map[k]: v for k, v in db_weights.items() if k in weights_map}

    score = sum(metrics[k] * active_weights[k] for k in active_weights)
    score = min(100, max(0, round(score, 1)))

    return {
        "productivity_index": score,
        "metrics": {k: round(v, 1) for k, v in metrics.items()},
        "weights": active_weights,
    }
