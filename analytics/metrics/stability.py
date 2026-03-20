"""Stability Index — coefficient of variation based consistency scoring."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from database import query
import numpy as np


def get_stability_index(employee_id: int, start_date: str, end_date: str) -> float:
    """
    Stability Index = (1 - CoeffientOfVariation) × 100
    Rewards consistency over volatility.
    Computed from weekly revenue totals.
    """
    # Get weekly revenue totals
    weekly_revenues = query(
        """SELECT strftime('%Y-%W', sale_date) as week, SUM(revenue) as weekly_revenue
           FROM sales 
           WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?
           GROUP BY week
           ORDER BY week""",
        (employee_id, start_date, end_date)
    )

    if len(weekly_revenues) < 2:
        return 0  # Not enough data

    revenues = np.array([w["weekly_revenue"] for w in weekly_revenues])
    mean = np.mean(revenues)

    if mean == 0:
        return 0

    cv = np.std(revenues) / mean  # Coefficient of variation
    stability = (1 - cv) * 100
    return max(0, min(100, stability))
