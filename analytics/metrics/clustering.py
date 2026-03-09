"""K-Means Employee Clustering."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from database import query
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


def cluster_employees(department_id: int = None, start_date: str = None, end_date: str = None, n_clusters: int = 3) -> dict:
    """
    Cluster employees using K-Means on [revenue, basket_size, app_conversion].
    Returns cluster assignments with centroids.
    """
    # Build employee filter
    where_clause = "WHERE e.role = 'employee' AND e.is_active = 1"
    params = []
    if department_id:
        where_clause += " AND e.department_id = ?"
        params.append(department_id)

    employees = query(f"SELECT e.id, e.name, e.department_id FROM employees e {where_clause}", tuple(params))

    if len(employees) < n_clusters:
        return {"error": "Not enough employees for clustering", "clusters": []}

    # Build feature matrix
    features = []
    emp_data = []

    for emp in employees:
        date_filter = ""
        date_params = []
        if start_date and end_date:
            date_filter = " AND sale_date BETWEEN ? AND ?"
            date_params = [start_date, end_date]

        # Total revenue
        rev = query(
            f"SELECT COALESCE(SUM(revenue), 0) as val FROM sales WHERE employee_id = ? AND status = 'approved'{date_filter}",
            (emp["id"], *date_params), one=True
        )

        # Avg basket size
        basket = query(
            f"SELECT COALESCE(AVG(basket_size), 0) as val FROM sales WHERE employee_id = ? AND status = 'approved'{date_filter}",
            (emp["id"], *date_params), one=True
        )

        # App downloads count
        downloads = query(
            f"SELECT COUNT(*) as val FROM app_downloads WHERE employee_id = ? AND status = 'approved'" +
            (f" AND download_date BETWEEN ? AND ?" if start_date and end_date else ""),
            (emp["id"], *date_params) if date_params else (emp["id"],), one=True
        )

        # Num sales (for conversion rate)
        num_sales = query(
            f"SELECT COUNT(*) as val FROM sales WHERE employee_id = ? AND status = 'approved'{date_filter}",
            (emp["id"], *date_params), one=True
        )

        conversion = downloads["val"] / num_sales["val"] if num_sales["val"] > 0 else 0

        features.append([rev["val"], basket["val"], conversion])
        emp_data.append({
            "id": emp["id"],
            "name": emp["name"],
            "total_revenue": round(rev["val"], 2),
            "avg_basket": round(basket["val"], 2),
            "app_conversion": round(conversion, 4),
        })

    if not features:
        return {"clusters": [], "centroids": []}

    X = np.array(features)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=min(n_clusters, len(X)), random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)

    # Name clusters based on centroids
    cluster_names = _name_clusters(kmeans.cluster_centers_, scaler)

    # Build result
    clusters = {}
    for i, emp in enumerate(emp_data):
        cluster_id = int(labels[i])
        if cluster_id not in clusters:
            clusters[cluster_id] = {
                "cluster_id": cluster_id,
                "name": cluster_names[cluster_id],
                "employees": [],
            }
        clusters[cluster_id]["employees"].append(emp)

    return {
        "clusters": list(clusters.values()),
        "centroids": [
            {
                "cluster_id": i,
                "name": cluster_names[i],
                "revenue": round(c[0], 2),
                "basket_size": round(c[1], 2),
                "app_conversion": round(c[2], 4),
            }
            for i, c in enumerate(scaler.inverse_transform(kmeans.cluster_centers_))
        ],
        "n_employees": len(emp_data),
    }


def _name_clusters(centers_scaled, scaler):
    """Auto-name clusters based on their characteristics."""
    centers = scaler.inverse_transform(centers_scaled)
    names = {}

    # Sort by total revenue (first feature)
    ranked = sorted(range(len(centers)), key=lambda i: centers[i][0], reverse=True)

    name_options = ["High Performers", "Steady Performers", "Growth Potential", "Needs Attention"]
    for idx, cluster_id in enumerate(ranked):
        names[cluster_id] = name_options[min(idx, len(name_options) - 1)]

    return names
