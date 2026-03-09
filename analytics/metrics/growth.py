"""Growth Trend — linear regression slope over revenue data."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from database import query
import numpy as np
from scipy import stats


def get_growth_trend(employee_id: int, start_date: str, end_date: str) -> float:
    """
    Growth Trend — linear regression slope over weekly revenues.
    Normalized to 0-100 scale.
    Positive slope = high score, negative slope = low score.
    """
    weekly_revenues = query(
        """SELECT strftime('%Y-%W', sale_date) as week, SUM(revenue) as weekly_revenue
           FROM sales 
           WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?
           GROUP BY week
           ORDER BY week""",
        (employee_id, start_date, end_date)
    )

    if len(weekly_revenues) < 3:
        return 50  # Not enough data for trend

    revenues = np.array([w["weekly_revenue"] for w in weekly_revenues])
    x = np.arange(len(revenues))

    slope, _, r_value, _, _ = stats.linregress(x, revenues)

    # Normalize: positive slope = growing, negative = declining
    mean_revenue = np.mean(revenues)
    if mean_revenue == 0:
        return 50

    # Percentage growth per week
    pct_growth = (slope / mean_revenue) * 100

    # Map to 0-100: -10% weekly decline = 0, +10% weekly growth = 100
    score = 50 + (pct_growth * 5)
    return max(0, min(100, score))


def get_growth_trend_data(employee_id: int, start_date: str, end_date: str) -> dict:
    """Return detailed trend data for charting."""
    weekly_revenues = query(
        """SELECT strftime('%Y-%W', sale_date) as week, 
                  MIN(sale_date) as week_start,
                  SUM(revenue) as weekly_revenue,
                  COUNT(*) as num_sales,
                  AVG(basket_size) as avg_basket
           FROM sales 
           WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?
           GROUP BY week
           ORDER BY week""",
        (employee_id, start_date, end_date)
    )

    if len(weekly_revenues) < 2:
        return {"weeks": [], "trend_line": [], "slope": 0, "r_squared": 0}

    revenues = np.array([w["weekly_revenue"] for w in weekly_revenues])
    x = np.arange(len(revenues))

    slope, intercept, r_value, _, _ = stats.linregress(x, revenues)
    trend_line = (slope * x + intercept).tolist()

    return {
        "weeks": [
            {
                "week": w["week"],
                "week_start": w["week_start"],
                "revenue": round(w["weekly_revenue"], 2),
                "num_sales": w["num_sales"],
                "avg_basket": round(w["avg_basket"], 2),
            }
            for w in weekly_revenues
        ],
        "trend_line": [round(v, 2) for v in trend_line],
        "slope": round(slope, 2),
        "r_squared": round(r_value ** 2, 4),
        "direction": "growing" if slope > 0 else "declining" if slope < 0 else "flat",
    }
