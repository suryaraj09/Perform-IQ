import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from database import query

def cluster_employees(department_id, start_date, end_date, n_clusters=4):
    """
    Higher-level wrapper to fetch data and run clustering.
    Returns format expected by legacy Clustering.tsx component.
    """
    where = "WHERE e.role = 'employee' AND e.is_active = 1"
    params = []
    if department_id:
        where += " AND e.department_id = ?"
        params.append(department_id)

    employees = query(
        f"SELECT e.id, e.name, d.name as department FROM employees e JOIN departments d ON e.department_id = d.id {where}",
        tuple(params)
    )

    if not employees:
        return {"clusters": [], "centroids": [], "n_employees": 0}

    employees_data = []
    for emp in employees:
        stats = query(
            """SELECT COALESCE(SUM(revenue), 0) as total_revenue,
                      COALESCE(AVG(basket_size), 0) as avg_basket
               FROM sales
               WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?""",
            (emp["id"], start_date, end_date),
            one=True
        )

        employees_data.append({
            "id": str(emp["id"]),
            "name": emp["name"],
            "department": emp["department"],
            "M1": stats["total_revenue"],
            "M2": stats["avg_basket"],
            "P": 0
        })

    if len(employees_data) < 4:
        # Not enough data for k=4 clustering
        return {"clusters": [], "centroids": [], "n_employees": len(employees_data)}

    clustered, centroids_raw = run_performance_clustering(employees_data)
    
    # Reformat for legacy Clustering.tsx component
    cluster_labels = [
        "High Vol High Basket",
        "High Vol Low Basket",
        "Low Vol High Basket",
        "Low Vol Low Basket"
    ]
    
    clusters = []
    for i in range(4):
        c_emps = []
        for emp in clustered:
            if emp["cluster"] == i:
                c_emps.append({
                    "id": int(emp["id"]),
                    "name": emp["name"],
                    "total_revenue": emp["M1"],
                    "avg_basket": emp["M2"]
                })
        clusters.append({
            "cluster_id": i,
            "name": cluster_labels[i],
            "employees": c_emps
        })
        
    centroids = []
    for c in centroids_raw:
        centroids.append({
            "cluster_id": c["cluster"],
            "name": c["label"],
            "revenue": c["M1"],
            "basket_size": c["M2"]
        })
        
    return {
        "clusters": clusters,
        "centroids": centroids,
        "n_employees": len(clustered)
    }

def run_performance_clustering(employees_data):
    """
    Run K-Means clustering on [M1, M2] (Revenue vs Target, Basket Performance).
    k=4 clusters.
    """
    if len(employees_data) < 4:
        # Not enough data for 4 clusters, return default
        return employees_data, []

    # Prepare features
    features = []
    for emp in employees_data:
        features.append([emp["M1"] or 0, emp["M2"] or 0])
    
    X = np.array(features)
    
    # Sklearn KMeans
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)
    centroids = kmeans.cluster_centers_

    # Map clusters to labels based on their centroids [M1, M2]
    # We'll identify the clusters by their relative coordinates
    # Cluster 0: High Vol High Basket
    # Cluster 1: High Vol Low Basket
    # Cluster 2: Low Vol High Basket
    # Cluster 3: Low Vol Low Basket
    
    # Sort centroids by M1 (descending)
    sorted_by_m1 = sorted(enumerate(centroids), key=lambda x: x[1][0], reverse=True)
    # Top 2 on M1
    top_2_m1 = sorted_by_m1[:2]
    # Bottom 2 on M1
    bottom_2_m1 = sorted_by_m1[2:]
    
    # Sort top 2 by M2
    hv_hb = sorted(top_2_m1, key=lambda x: x[1][1], reverse=True)[0]
    hv_lb = sorted(top_2_m1, key=lambda x: x[1][1], reverse=True)[1]
    
    # Sort bottom 2 by M2
    lv_hb = sorted(bottom_2_m1, key=lambda x: x[1][1], reverse=True)[0]
    lv_lb = sorted(bottom_2_m1, key=lambda x: x[1][1], reverse=True)[1]
    
    mapping = {
        hv_hb[0]: 0, # High Vol High Basket
        hv_lb[0]: 1, # High Vol Low Basket
        lv_hb[0]: 2, # Low Vol High Basket
        lv_lb[0]: 3  # Low Vol Low Basket
    }
    
    cluster_labels = [
        "High Vol High Basket",
        "High Vol Low Basket",
        "Low Vol High Basket",
        "Low Vol Low Basket"
    ]

    # Update employees with their mapped cluster ID
    for i, emp in enumerate(employees_data):
        emp["cluster"] = mapping[labels[i]]
        
    # Format centroids for response
    formatted_centroids = []
    for raw_idx, label_idx in mapping.items():
        formatted_centroids.append({
            "cluster": label_idx,
            "label": cluster_labels[label_idx],
            "M1": round(float(centroids[raw_idx][0]), 1),
            "M2": round(float(centroids[raw_idx][1]), 1)
        })
        
    # Sort centroids by internal cluster ID (0, 1, 2, 3)
    formatted_centroids.sort(key=lambda x: x["cluster"])

    return employees_data, formatted_centroids
