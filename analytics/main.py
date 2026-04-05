# no one touches this code without my permission, This is the only portion you need my permission
# don't do anything here without letting me know
import os
import sys
import uuid
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))

from database import init_db, query, execute
from metrics.productivity import compute_productivity_index
from metrics.growth import get_growth_trend_data
from metrics.clustering import cluster_employees
from gamification import get_employee_gamification, get_leaderboard, get_level_info, get_xp_for_score
from attendance import punch_in, punch_out, get_attendance_status
from migrate_weights import run_migration

app = FastAPI(title="PerformIQ API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "receipts").mkdir(exist_ok=True)
(UPLOAD_DIR / "screenshots").mkdir(exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


alert_queues: list = []


class SaleSubmission(BaseModel):
    employee_id: int
    revenue: float
    num_items: int = 1
    receipt_photo_path: Optional[str] = None


class ReviewAction(BaseModel):
    status: str  # "approved" or "rejected"
    reviewer_id: int
    rejection_reason: Optional[str] = None


class DailyRating(BaseModel):
    employee_id: int
    manager_id: int
    rating: int
    notes: Optional[str] = None


class PunchRequest(BaseModel):
    employee_id: int
    latitude: float
    longitude: float


class GeofenceAlert(BaseModel):
    employeeId: int
    employeeName: str
    punchInTime: str
    firstFailTime: str
    secondFailTime: str
    alertType: str = "GEOFENCE_ABSENCE"


class AuthRegister(BaseModel):
    firebase_uid: str
    name: str
    email: str
    role: str = "employee"
    store_id: int = 1
    department_id: int = 1


@app.post("/api/auth/register")
async def register_user(data: AuthRegister):
    existing = query("SELECT id FROM employees WHERE firebase_uid = ?", (data.firebase_uid,), one=True)
    if existing:
        return await get_profile(data.firebase_uid)
    status = 'pending' if data.role == 'employee' else 'approved'

    employee_id = execute(
        """INSERT INTO employees (name, email, role, department_id, store_id, firebase_uid, total_xp, level, level_title, status)
           VALUES (?, ?, ?, ?, ?, ?, 0, 1, 'Rookie', ?)""",
        (data.name, data.email, data.role, data.department_id, data.store_id, data.firebase_uid, status),
    )

    return query(
        """SELECT e.*, d.name as department_name, s.name as store_name
           FROM employees e
           JOIN departments d ON e.department_id = d.id
           JOIN stores s ON e.store_id = s.id
           WHERE e.id = ?""",
        (employee_id,), one=True
    )


@app.get("/api/auth/profile/{firebase_uid}")
async def get_profile(firebase_uid: str):
    emp = query(
        """SELECT e.*, d.name as department_name, s.name as store_name
           FROM employees e
           JOIN departments d ON e.department_id = d.id
           JOIN stores s ON e.store_id = s.id
           WHERE e.firebase_uid = ?""",
        (firebase_uid,), one=True
    )
    if not emp:
        raise HTTPException(status_code=404, detail="Profile not found")
    return emp



def get_date_range(range_type: str = "weekly", start: str = None, end: str = None):
    today = datetime.now()
    if range_type == "custom" and start and end:
        return start, end
    elif range_type == "daily":
        return today.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    elif range_type == "monthly":
        start_date = today.replace(day=1)
        return start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    else:  # weekly (default) don't touch this block please
        start_date = today - timedelta(days=today.weekday())
        return start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


def get_full_date_range():
    return "2026-01-12", datetime.now().strftime("%Y-%m-%d")


# ==================== FLAG DETECTION HELPERS ====================

def get_employee_avg_sale(employee_id: int) -> float:
    """Get avg sale amount from last 20 sales, or dept average if < 5 sales."""
    sales = query(
        "SELECT revenue FROM sales WHERE employee_id = ? ORDER BY submitted_at DESC LIMIT 20",
        (employee_id,)
    )
    if len(sales) >= 5:
        return sum(s["revenue"] for s in sales) / len(sales)
    # Fall back to department average
    dept = query(
        """SELECT COALESCE(AVG(s.revenue), 0) as avg_rev FROM sales s
           JOIN employees e ON s.employee_id = e.id
           WHERE e.department_id = (SELECT department_id FROM employees WHERE id = ?)""",
        (employee_id,), one=True
    )
    return dept["avg_rev"] if dept and dept["avg_rev"] > 0 else 5000.0


def get_last_sale_timestamp(employee_id: int):
    """Get Unix ms timestamp of most recent sale, or None."""
    row = query(
        "SELECT submitted_at FROM sales WHERE employee_id = ? ORDER BY submitted_at DESC LIMIT 1",
        (employee_id,), one=True
    )
    if not row or not row["submitted_at"]:
        return None
    dt = datetime.strptime(row["submitted_at"], "%Y-%m-%d %H:%M:%S")
    return dt.timestamp() * 1000


def has_active_punch_in(employee_id: int) -> bool:
    """Check if employee currently has an active punch-in session."""
    row = query(
        """SELECT id FROM attendance WHERE employee_id = ? 
           AND punch_in_time IS NOT NULL AND punch_out_time IS NULL
           ORDER BY attendance_date DESC LIMIT 1""",
        (employee_id,), one=True
    )
    return row is not None


def check_for_flags(sale_revenue: float, num_items: int, employee_id: int) -> list:
    """Run all 4 flag rules and return triggered flags."""
    flags = []

    # RULE 1 — HIGH_SALE_AMOUNT
    avg_sale = get_employee_avg_sale(employee_id)
    if sale_revenue > avg_sale * 3:
        flags.append({
            "rule": "HIGH_SALE_AMOUNT",
            "detail": f"Sale \u20b9{sale_revenue:.0f} is 3x above average \u20b9{avg_sale:.0f}"
        })

    # RULE 2 — HIGH_ITEM_COUNT
    if num_items > 15:
        flags.append({
            "rule": "HIGH_ITEM_COUNT",
            "detail": f"{num_items} items in a single bill is unusually high"
        })

    # RULE 3 — RAPID_SUBMISSION
    last_ts = get_last_sale_timestamp(employee_id)
    if last_ts is not None:
        now_ms = datetime.now().timestamp() * 1000
        diff_seconds = (now_ms - last_ts) / 1000
        if diff_seconds < 120:
            flags.append({
                "rule": "RAPID_SUBMISSION",
                "detail": f"Submitted {int(diff_seconds)}s after previous sale"
            })

    # RULE 4 — NO_ACTIVE_SESSION
    if not has_active_punch_in(employee_id):
        flags.append({
            "rule": "NO_ACTIVE_SESSION",
            "detail": "Sale submitted without an active punch in session"
        })

    return flags


# ==================== AUTO-CONFIRM TASK ====================

async def auto_confirm_flagged_sales():
    """Auto-confirm flagged sales older than 48 hours, runs every hour."""
    while True:
        await asyncio.sleep(3600)  # every hour
        try:
            cutoff = (datetime.now() - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")
            now_iso = datetime.now().isoformat()
            stale = query(
                """SELECT id FROM sales WHERE is_flagged = 1 AND resolved_by_admin = 0
                   AND submitted_at < ?""",
                (cutoff,)
            )
            for sale in stale:
                execute(
                    """UPDATE sales SET resolved_by_admin = 1, admin_action = 'AUTO_CONFIRMED',
                       auto_confirmed_at = ? WHERE id = ?""",
                    (now_iso, sale["id"]),
                )
            if stale:
                print(f"Auto-confirmed {len(stale)} flagged sales")
        except Exception as e:
            print(f"Auto-confirm error: {e}")


@app.on_event("startup")
async def startup():
    init_db()
    run_migration()
    asyncio.create_task(auto_confirm_flagged_sales())



@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), category: str = Form("receipts")):
    ext = Path(file.filename).suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    folder = UPLOAD_DIR / category
    folder.mkdir(exist_ok=True)
    filepath = folder / filename

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    return {"path": f"uploads/{category}/{filename}", "filename": filename}

@app.post("/api/sales")
async def submit_sale(sale: SaleSubmission):
    basket_size = round(sale.revenue / max(sale.num_items, 1), 2)

    # Run flag detection
    flags = check_for_flags(sale.revenue, sale.num_items, sale.employee_id)
    is_flagged = len(flags) > 0

    sale_id = execute(
        """INSERT INTO sales (employee_id, revenue, basket_size, num_items,
           receipt_photo_path, status, is_flagged, flags, resolved_by_admin, sale_date)
           VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, 0, date('now'))""",
        (sale.employee_id, sale.revenue, basket_size, sale.num_items,
         sale.receipt_photo_path,
         1 if is_flagged else 0, json.dumps(flags)),
    )

    alert_type = "flagged_sale" if is_flagged else "new_sale"
    await broadcast_alert({
        "type": alert_type,
        "message": f"{'🚩 Flagged sale' if is_flagged else 'New sale'} submission (₹{sale.revenue:.0f}) pending review",
        "employee_id": sale.employee_id,
        "sale_id": sale_id,
    })

    ws, we = get_date_range("weekly")
    weekly_revenue = query(
        "SELECT COALESCE(SUM(revenue), 0) as v FROM sales WHERE employee_id = ? AND sale_date BETWEEN ? AND ? AND admin_action IS NOT 'REJECTED'",
        (sale.employee_id, ws, we), one=True
    )
    total_bills = query(
        "SELECT COUNT(*) as v FROM sales WHERE employee_id = ? AND sale_date BETWEEN ? AND ? AND admin_action IS NOT 'REJECTED'",
        (sale.employee_id, ws, we), one=True
    )
    avg_basket = query(
        "SELECT COALESCE(AVG(basket_size), 0) as v FROM sales WHERE employee_id = ? AND sale_date BETWEEN ? AND ? AND admin_action IS NOT 'REJECTED'",
        (sale.employee_id, ws, we), one=True
    )

    return {
        "success": True,
        "saleId": str(sale_id),
        "isFlagged": is_flagged,
        "flags": flags,
        "basketSize": basket_size,
        "weeklyTotals": {
            "weeklyRevenue": round(weekly_revenue["v"], 2),
            "totalBills": total_bills["v"],
            "avgBasketSize": round(avg_basket["v"], 2),
        },
    }


@app.get("/api/sales")
async def list_sales(
    employee_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
):
    where, params = "WHERE 1=1", []
    if employee_id:
        where += " AND s.employee_id = ?"
        params.append(employee_id)
    if status:
        where += " AND s.status = ?"
        params.append(status)

    return query(
        f"""SELECT s.*, e.name as employee_name FROM sales s
            JOIN employees e ON s.employee_id = e.id {where}
            ORDER BY s.submitted_at DESC LIMIT ?""",
        (*params, limit),
    )


@app.put("/api/sales/{sale_id}/review")
async def review_sale(sale_id: int, review: ReviewAction):
    execute(
        "UPDATE sales SET status = ?, reviewed_by = ?, reviewed_at = datetime('now'), rejection_reason = ? WHERE id = ?",
        (review.status, review.reviewer_id, review.rejection_reason, sale_id),
    )
    return {"id": sale_id, "status": review.status, "message": f"Sale {review.status}"}




@app.get("/api/employees")
async def list_employees(department_id: Optional[int] = None, store_id: Optional[int] = None, role: Optional[str] = None):
    """List all employees."""
    where, params = "WHERE 1=1", []
    if department_id:
        where += " AND e.department_id = ?"
        params.append(department_id)
    if store_id:
        where += " AND e.store_id = ?"
        params.append(store_id)
    if role:
        where += " AND e.role = ?"
        params.append(role)

    return query(
        f"""SELECT e.*, d.name as department_name, s.name as store_name
            FROM employees e 
            JOIN departments d ON e.department_id = d.id
            JOIN stores s ON e.store_id = s.id
            {where} ORDER BY e.name""",
        tuple(params),
    )


@app.get("/api/employees/{employee_id}")
async def get_employee(employee_id: int):
    emp = query(
        """SELECT e.*, d.name as department_name, s.name as store_name
           FROM employees e
           JOIN departments d ON e.department_id = d.id
           JOIN stores s ON e.store_id = s.id
           WHERE e.id = ?""",
        (employee_id,), one=True
    )
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


@app.get("/api/employees/{employee_id}/score")
async def get_employee_score(
    employee_id: int,
    range: str = "weekly",
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    start_date, end_date = get_date_range(range, start, end)
    return compute_productivity_index(employee_id, start_date, end_date)


@app.get("/api/employees/{employee_id}/gamification")
async def get_gamification(employee_id: int):
    result = get_employee_gamification(employee_id)
    if not result:
        raise HTTPException(status_code=404, detail="Employee not found")
    return result


@app.get("/api/employees/{employee_id}/trends")
async def get_trends(
    employee_id: int,
    range: str = "weekly",
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    if range == "weekly":
        s, e = get_full_date_range()
    else:
        s, e = get_date_range(range, start, end)
    return get_growth_trend_data(employee_id, s, e)

@app.get("/api/leaderboard")
async def leaderboard(
    department_id: Optional[int] = None,
    store_id: Optional[int] = None,
    limit: int = 20,
):
    return get_leaderboard(department_id, store_id, limit)

@app.get("/api/clustering")
async def get_clustering(
    department_id: Optional[int] = None,
    n_clusters: int = 3,
    range: str = "monthly",
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    s, e = get_full_date_range() if range == "weekly" else get_date_range(range, start, end)
    return cluster_employees(department_id, s, e, n_clusters)


@app.get("/api/correlations")
async def get_correlations(department_id: Optional[int] = None):
    import numpy as np

    s, e = get_full_date_range()

    where, params = "WHERE e.role = 'employee' AND e.is_active = 1", []
    if department_id:
        where += " AND e.department_id = ?"
        params.append(department_id)

    employees = query(f"SELECT e.id FROM employees e {where}", tuple(params))

    if not employees:
        return {"matrix": [], "labels": []}

    metric_labels = ["Revenue", "Basket Size", "Manager Rating", "Attendance"]
    data_matrix = []

    for emp in employees:
        eid = emp["id"]
        rev = query("SELECT COALESCE(SUM(revenue), 0) as v FROM sales WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?", (eid, s, e), one=True)
        basket = query("SELECT COALESCE(AVG(basket_size), 0) as v FROM sales WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?", (eid, s, e), one=True)
        rating = query("SELECT COALESCE(AVG(rating), 0) as v FROM manager_ratings WHERE employee_id = ? AND rating_date BETWEEN ? AND ?", (eid, s, e), one=True)
        att = query("SELECT COUNT(*) as v FROM attendance WHERE employee_id = ? AND punch_in_status = 'approved' AND attendance_date BETWEEN ? AND ?", (eid, s, e), one=True)

        data_matrix.append([rev["v"], basket["v"], rating["v"], att["v"]])

    if len(data_matrix) < 2:
        return {"matrix": [], "labels": metric_labels}

    arr = np.array(data_matrix)
    corr = np.corrcoef(arr.T)
    corr = np.nan_to_num(corr)

    return {
        "matrix": [[round(float(v), 3) for v in row] for row in corr],
        "labels": metric_labels,
    }


@app.get("/api/departments/{department_id}/analytics")
async def department_analytics(
    department_id: int,
    range: str = "weekly",
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    s, e = get_date_range(range, start, end)

    dept = query("SELECT * FROM departments WHERE id = ?", (department_id,), one=True)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    total_rev = query(
        """SELECT COALESCE(SUM(s.revenue), 0) as total FROM sales s
           JOIN employees emp ON s.employee_id = emp.id
           WHERE emp.department_id = ? AND s.status = 'approved' AND s.sale_date BETWEEN ? AND ?""",
        (department_id, s, e), one=True
    )

    emp_count = query(
        "SELECT COUNT(*) as count FROM employees WHERE department_id = ? AND role = 'employee' AND is_active = 1",
        (department_id,), one=True
    )

    avg_rating = query(
        """SELECT COALESCE(AVG(mr.rating), 0) as avg FROM manager_ratings mr
           JOIN employees emp ON mr.employee_id = emp.id
           WHERE emp.department_id = ? AND mr.rating_date BETWEEN ? AND ?""",
        (department_id, s, e), one=True
    )

    return {
        "department": dept,
        "total_revenue": round(total_rev["total"], 2),
        "employee_count": emp_count["count"],
        "avg_rating": round(avg_rating["avg"], 2),
        "date_range": {"start": s, "end": e},
    }

@app.post("/api/attendance/punch-in")
async def api_punch_in(req: PunchRequest):
    result = punch_in(req.employee_id, req.latitude, req.longitude)
    if result["success"]:
        await broadcast_alert({
            "type": "punch_in",
            "employee_id": req.employee_id,
            "message": f"Employee punched in",
        })
    return result


@app.post("/api/attendance/punch-out")
async def api_punch_out(req: PunchRequest):
    return punch_out(req.employee_id, req.latitude, req.longitude)


@app.get("/api/attendance")
async def get_attendance(employee_id: Optional[int] = None, limit: int = 30):
    where, params = "", []
    if employee_id:
        where = "WHERE a.employee_id = ?"
        params.append(employee_id)

    return query(
        f"""SELECT a.*, e.name as employee_name FROM attendance a
            JOIN employees e ON a.employee_id = e.id
            {where} ORDER BY a.attendance_date DESC LIMIT ?""",
        (*params, limit),
    )


@app.get("/api/attendance/status/{employee_id}")
async def api_attendance_status(employee_id: int):
    return get_attendance_status(employee_id)

@app.get("/api/manager/review-queue")
async def review_queue():
    pending_sales = query(
        """SELECT s.*, e.name as employee_name, 'sale' as type FROM sales s
           JOIN employees e ON s.employee_id = e.id
           WHERE s.status = 'pending' ORDER BY s.submitted_at DESC"""
    )
    return {"sales": pending_sales, "downloads": [], "total": len(pending_sales)}


@app.post("/api/manager/daily-rating")
async def submit_rating(rating: DailyRating):
    try:
        execute(
            "INSERT OR REPLACE INTO manager_ratings (employee_id, manager_id, rating, notes, rating_date) VALUES (?, ?, ?, ?, date('now'))",
            (rating.employee_id, rating.manager_id, rating.rating, rating.notes),
        )
        return {"success": True, "message": "Rating submitted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/manager/attendance-overview")
async def attendance_overview():
    today = datetime.now().strftime("%Y-%m-%d")
    return query(
        """SELECT e.id, e.name, e.department_id, d.name as department_name,
                  a.punch_in_time, a.punch_out_time, a.punch_in_status, a.hours_worked
           FROM employees e
           JOIN departments d ON e.department_id = d.id
           LEFT JOIN attendance a ON e.id = a.employee_id AND a.attendance_date = ?
           WHERE e.role = 'employee' AND e.is_active = 1
           ORDER BY e.name""",
        (today,),
    )


@app.get("/api/manager/pending-employees")
async def pending_employees(store_id: Optional[int] = None):
    where, params = "WHERE e.status = 'pending'", []
    if store_id:
        where += " AND e.store_id = ?"
        params.append(store_id)
        
    return query(
        f"""SELECT e.*, d.name as department_name, s.name as store_name
            FROM employees e
            JOIN departments d ON e.department_id = d.id
            JOIN stores s ON e.store_id = s.id
            {where} ORDER BY e.created_at DESC""",
        tuple(params),
    )


@app.put("/api/manager/employees/{employee_id}/review")
async def review_employee(employee_id: int, review: ReviewAction):
    if review.status not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    execute(
        "UPDATE employees SET status = ? WHERE id = ?",
        (review.status, employee_id),
    )
    return {"id": employee_id, "status": review.status, "message": f"Employee {review.status}"}


# ==================== GEOFENCE ALERTS ====================

@app.post("/api/alerts/geofence")
async def create_geofence_alert(alert: GeofenceAlert):
    alert_id = execute(
        """INSERT INTO geofence_alerts (employee_id, employee_name, punch_in_time, first_fail_time, second_fail_time, alert_type)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (alert.employeeId, alert.employeeName, alert.punchInTime, alert.firstFailTime, alert.secondFailTime, alert.alertType),
    )
    return {"success": True, "alertId": str(alert_id)}


@app.get("/api/alerts/geofence")
async def list_geofence_alerts():
    return query(
        """SELECT id as alertId, employee_id as employeeId, employee_name as employeeName,
                  punch_in_time as punchInTime, first_fail_time as firstFailTime,
                  second_fail_time as secondFailTime, alert_type as alertType,
                  resolved, created_at as createdAt
           FROM geofence_alerts WHERE resolved = 0 ORDER BY created_at DESC"""
    )


# ==================== ADMIN FLAGGED SALES ====================

class AdminAction(BaseModel):
    action: str  # "CONFIRMED" or "REJECTED"


@app.get("/api/admin/flagged-sales")
async def get_flagged_sales():
    rows = query(
        """SELECT s.id as saleId, s.employee_id as employeeId, e.name as employeeName,
                  d.name as department, s.revenue as saleAmount, s.num_items as numberOfItems,
                  s.basket_size as basketSize,
                  s.receipt_photo_path as receiptPhoto, s.submitted_at as submittedAt,
                  s.flags, s.is_flagged as isFlagged, s.resolved_by_admin as resolvedByAdmin
           FROM sales s
           JOIN employees e ON s.employee_id = e.id
           JOIN departments d ON e.department_id = d.id
           WHERE s.is_flagged = 1 AND s.resolved_by_admin = 0
           ORDER BY s.submitted_at DESC"""
    )

    ws, we = get_date_range("weekly")
    result = []
    for row in rows:
        r = dict(row)
        try:
            r["flags"] = json.loads(r["flags"]) if r["flags"] else []
        except (json.JSONDecodeError, TypeError):
            r["flags"] = []
        r["isFlagged"] = bool(r["isFlagged"])
        r["resolvedByAdmin"] = bool(r["resolvedByAdmin"])

        # Compute score impact delta (Change 4)
        emp_id = r["employeeId"]
        try:
            current_score = compute_productivity_index(emp_id, ws, we)
            current_p = current_score["productivity_index"]

            # Get current weekly totals for this employee
            wr = query(
                "SELECT COALESCE(SUM(revenue), 0) as v FROM sales WHERE employee_id = ? AND sale_date BETWEEN ? AND ? AND admin_action IS NOT 'REJECTED'",
                (emp_id, ws, we), one=True
            )
            tb = query(
                "SELECT COUNT(*) as v FROM sales WHERE employee_id = ? AND sale_date BETWEEN ? AND ? AND admin_action IS NOT 'REJECTED'",
                (emp_id, ws, we), one=True
            )

            weekly_rev = wr["v"] if wr else 0
            total_bills = tb["v"] if tb else 0

            # Adjusted totals without this sale
            adj_revenue = weekly_rev - r["saleAmount"]
            adj_bills = total_bills - 1

            # Recompute M1 (Revenue vs Target)
            dept = query(
                """SELECT d.weekly_revenue_target FROM employees e
                   JOIN departments d ON e.department_id = d.id WHERE e.id = ?""",
                (emp_id,), one=True
            )
            target = dept["weekly_revenue_target"] if dept and dept["weekly_revenue_target"] > 0 else 1
            from datetime import datetime as dt_cls
            d1 = dt_cls.strptime(ws, "%Y-%m-%d")
            d2 = dt_cls.strptime(we, "%Y-%m-%d")
            weeks = max(1, (d2 - d1).days / 7)
            adj_m1 = min(100, (adj_revenue / weeks / target) * 100) if adj_revenue > 0 else 0

            # Recompute M2 (Basket Performance) without this sale's basket
            all_baskets = query(
                """SELECT basket_size FROM sales WHERE employee_id = ? AND sale_date BETWEEN ? AND ?
                   AND admin_action IS NOT 'REJECTED' AND id != ?""",
                (emp_id, ws, we, r["saleId"])
            )
            dept_basket = query(
                """SELECT d.avg_basket_size FROM employees e
                   JOIN departments d ON e.department_id = d.id WHERE e.id = ?""",
                (emp_id,), one=True
            )
            dept_bsz = dept_basket["avg_basket_size"] if dept_basket and dept_basket["avg_basket_size"] > 0 else 1
            if all_baskets:
                adj_avg_basket = sum(b["basket_size"] for b in all_baskets) / len(all_baskets)
                adj_m2 = min(100, (adj_avg_basket / dept_bsz) * 100)
            else:
                adj_m2 = 0

            # Keep M3-M8 unchanged from current score
            m = current_score["metrics"]
            projected_p = round(
                0.30 * adj_m1 +
                0.25 * adj_m2 +
                0.15 * m["manager_rating"] +
                0.10 * m["growth_trend"] +
                0.10 * m["stability_index"] +
                0.05 * m["attendance_rate"] +
                0.05 * m["punctuality"],
                1
            )
            projected_p = min(100, max(0, projected_p))

            r["currentPScore"] = current_p
            r["projectedPScore"] = projected_p
        except Exception:
            r["currentPScore"] = 0
            r["projectedPScore"] = 0

        result.append(r)
    return result


@app.patch("/api/admin/flagged-sales/{sale_id}")
async def resolve_flagged_sale(sale_id: int, action_data: AdminAction):
    if action_data.action not in ("CONFIRMED", "REJECTED"):
        raise HTTPException(status_code=400, detail="Action must be CONFIRMED or REJECTED")

    now_iso = datetime.now().isoformat()
    execute(
        "UPDATE sales SET resolved_by_admin = 1, admin_action = ?, resolved_at = ? WHERE id = ?",
        (action_data.action, now_iso, sale_id),
    )

    # Get employee id for this sale
    sale = query("SELECT employee_id FROM sales WHERE id = ?", (sale_id,), one=True)
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    emp_id = sale["employee_id"]
    ws, we = get_date_range("weekly")

    if action_data.action == "REJECTED":
        # Recalculate weekly totals excluding rejected sales
        weekly_revenue = query(
            "SELECT COALESCE(SUM(revenue), 0) as v FROM sales WHERE employee_id = ? AND sale_date BETWEEN ? AND ? AND admin_action IS NOT 'REJECTED'",
            (emp_id, ws, we), one=True
        )
        total_bills = query(
            "SELECT COUNT(*) as v FROM sales WHERE employee_id = ? AND sale_date BETWEEN ? AND ? AND admin_action IS NOT 'REJECTED'",
            (emp_id, ws, we), one=True
        )
        avg_basket = query(
            "SELECT COALESCE(AVG(basket_size), 0) as v FROM sales WHERE employee_id = ? AND sale_date BETWEEN ? AND ? AND admin_action IS NOT 'REJECTED'",
            (emp_id, ws, we), one=True
        )
        weekly_totals = {
            "weeklyRevenue": round(weekly_revenue["v"], 2),
            "totalBills": total_bills["v"],
            "avgBasketSize": round(avg_basket["v"], 2),
        }
    else:
        # Confirmed — just return current totals
        weekly_revenue = query(
            "SELECT COALESCE(SUM(revenue), 0) as v FROM sales WHERE employee_id = ? AND sale_date BETWEEN ? AND ?",
            (emp_id, ws, we), one=True
        )
        total_bills = query(
            "SELECT COUNT(*) as v FROM sales WHERE employee_id = ? AND sale_date BETWEEN ? AND ?",
            (emp_id, ws, we), one=True
        )
        avg_basket = query(
            "SELECT COALESCE(AVG(basket_size), 0) as v FROM sales WHERE employee_id = ? AND sale_date BETWEEN ? AND ?",
            (emp_id, ws, we), one=True
        )
        weekly_totals = {
            "weeklyRevenue": round(weekly_revenue["v"], 2),
            "totalBills": total_bills["v"],
            "avgBasketSize": round(avg_basket["v"], 2),
        }

    return {
        "success": True,
        "saleId": str(sale_id),
        "action": action_data.action,
        "weeklyTotals": weekly_totals,
    }


@app.post("/api/admin/flagged-sales/auto-confirm")
async def manual_auto_confirm():
    """Manual trigger for auto-confirming flagged sales older than 48h."""
    cutoff = (datetime.now() - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")
    now_iso = datetime.now().isoformat()
    stale = query(
        "SELECT id FROM sales WHERE is_flagged = 1 AND resolved_by_admin = 0 AND submitted_at < ?",
        (cutoff,)
    )
    for sale in stale:
        execute(
            "UPDATE sales SET resolved_by_admin = 1, admin_action = 'AUTO_CONFIRMED', auto_confirmed_at = ? WHERE id = ?",
            (now_iso, sale["id"]),
        )
    return {"success": True, "autoConfirmed": len(stale)}


# ==================== SSE ENDPOINT ====================

async def broadcast_alert(alert: dict):
    alert["timestamp"] = datetime.now().isoformat()
    for q in alert_queues:
        await q.put(alert)


@app.get("/api/stream/alerts")
async def stream_alerts():
    q = asyncio.Queue()
    alert_queues.append(q)

    async def event_generator():
        try:
            while True:
                alert = await asyncio.wait_for(q.get(), timeout=30)
                import json
                yield f"data: {json.dumps(alert)}\n\n"
        except asyncio.TimeoutError:
            yield f"data: {{}}\n\n"  # keepalive
        except Exception:
            pass
        finally:
            alert_queues.remove(q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ==================== DASHBOARD SUMMARY ====================

@app.get("/api/dashboard/employee/{employee_id}")
async def employee_dashboard(employee_id: int):
    s, e = get_full_date_range()
    ws, we = get_date_range("weekly")

    emp = query(
        """SELECT e.*, d.name as department_name, s.name as store_name
           FROM employees e JOIN departments d ON e.department_id = d.id
           JOIN stores s ON e.store_id = s.id WHERE e.id = ?""",
        (employee_id,), one=True
    )
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    score = compute_productivity_index(employee_id, ws, we)
    gamification = get_employee_gamification(employee_id)
    trends = get_growth_trend_data(employee_id, s, e)
    att_status = get_attendance_status(employee_id)

    weekly_revenue = query(
        "SELECT COALESCE(SUM(revenue), 0) as v FROM sales WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?",
        (employee_id, ws, we), one=True
    )
    weekly_bills = query(
        "SELECT COUNT(*) as v FROM sales WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?",
        (employee_id, ws, we), one=True
    )
    weekly_basket = query(
        "SELECT COALESCE(AVG(basket_size), 0) as v FROM sales WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?",
        (employee_id, ws, we), one=True
    )

    return {
        "employee": emp,
        "score": score,
        "gamification": gamification,
        "trends": trends,
        "attendance_status": att_status,
        "weekly_stats": {
            "revenue": round(weekly_revenue["v"], 2),
            "bills": weekly_bills["v"],
            "avg_basket": round(weekly_basket["v"], 2),
        },
    }


@app.get("/api/dashboard/manager")
async def manager_dashboard(store_id: int = 1):
    ws, we = get_date_range("weekly")

    departments = query("SELECT * FROM departments WHERE store_id = ?", (store_id,))

    dept_stats = []
    for dept in departments:
        rev = query(
            """SELECT COALESCE(SUM(s.revenue), 0) as total FROM sales s
               JOIN employees e ON s.employee_id = e.id
               WHERE e.department_id = ? AND s.status = 'approved' AND s.sale_date BETWEEN ? AND ?""",
            (dept["id"], ws, we), one=True
        )
        emp_count = query("SELECT COUNT(*) as c FROM employees WHERE department_id = ? AND role='employee' AND is_active=1", (dept["id"],), one=True)
        dept_stats.append({
            **dept,
            "weekly_revenue": round(rev["total"], 2),
            "employee_count": emp_count["c"],
            "target_achievement": round((rev["total"] / dept["weekly_revenue_target"]) * 100, 1) if dept["weekly_revenue_target"] > 0 else 0,
        })

    review = await review_queue()
    today_attendance = await attendance_overview()

    total_rev = sum(d["weekly_revenue"] for d in dept_stats)
    total_emp = sum(d["employee_count"] for d in dept_stats)
    avg_achievement = sum(d["target_achievement"] for d in dept_stats) / max(1, len(dept_stats))

    return {
        "summary": {
            "total_revenue": round(total_rev, 2),
            "active_employees": total_emp,
            "avg_target_achievement": round(avg_achievement, 1),
            "pending_reviews": review["total"],
        },
        "departments": dept_stats,
        "review_queue": review,
        "attendance": today_attendance,
    }


# ==================== PHASE 2 — VISUALISATION ENDPOINTS ====================

@app.get("/api/employee/{employee_id}/dashboard")
async def employee_dashboard_v2(employee_id: int):
    """Full employee dashboard payload for Phase 2 visualisations."""
    try:
        ws, we = get_date_range("weekly")

        emp = query(
            """SELECT e.id, e.name, e.total_xp, e.level, e.level_title,
                      d.name as department, d.weekly_revenue_target,
                      s.name as store_name, s.shift_start_time, e.store_id
               FROM employees e
               JOIN departments d ON e.department_id = d.id
               JOIN stores s ON e.store_id = s.id
               WHERE e.id = ?""",
            (employee_id,), one=True
        )
        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found")

        # Compute current week P score with metric breakdown
        score_data = compute_productivity_index(employee_id, ws, we)
        metrics = score_data.get("metrics", {})

        # Weekly stats
        weekly_revenue_row = query(
            "SELECT COALESCE(SUM(revenue), 0) as v FROM sales WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?",
            (employee_id, ws, we), one=True
        )
        total_bills_row = query(
            "SELECT COUNT(*) as v FROM sales WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?",
            (employee_id, ws, we), one=True
        )
        avg_basket_row = query(
            "SELECT COALESCE(AVG(basket_size), 0) as v FROM sales WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?",
            (employee_id, ws, we), one=True
        )

        weekly_revenue = round(weekly_revenue_row["v"], 2)
        weekly_target = emp["weekly_revenue_target"] or 0
        revenue_remaining = max(0, round(weekly_target - weekly_revenue, 2))

        # Week number
        today = datetime.now()
        week_number = today.isocalendar()[1]
        year = today.year

        # XP and level info
        level_info = get_level_info(emp["total_xp"])

        # Leaderboard rank
        lb = get_leaderboard(store_id=emp["store_id"], limit=100)
        rank = next((e["rank"] for e in lb if e["id"] == employee_id), len(lb))
        total_employees = len(lb)

        # Weekly trend — last 8 weeks
        weekly_trend = []
        for i in range(7, -1, -1):
            wk_start = (today - timedelta(days=today.weekday()) - timedelta(weeks=i)).strftime("%Y-%m-%d")
            wk_end = (datetime.strptime(wk_start, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")
            wk_rev = query(
                "SELECT COALESCE(SUM(revenue), 0) as v FROM sales WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?",
                (employee_id, wk_start, wk_end), one=True
            )
            wk_num = datetime.strptime(wk_start, "%Y-%m-%d").isocalendar()[1]
            wk_score = compute_productivity_index(employee_id, wk_start, wk_end)
            weekly_trend.append({
                "week": f"W{wk_num}",
                "revenue": round(wk_rev["v"], 2),
                "target": weekly_target,
                "pScore": wk_score.get("productivity_index", 0),
            })

        # Streak data — last 28 days
        streak_data = []
        daily_target = weekly_target / 6 if weekly_target > 0 else 0
        store_info = query("SELECT shift_start_time FROM stores WHERE id = ?", (emp["store_id"],), one=True)
        shift_start = store_info["shift_start_time"] if store_info else "09:00"

        for i in range(27, -1, -1):
            day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            day_rev = query(
                "SELECT COALESCE(SUM(revenue), 0) as v FROM sales WHERE employee_id = ? AND status = 'approved' AND sale_date = ?",
                (employee_id, day), one=True
            )
            att = query(
                "SELECT punch_in_time, punch_in_status FROM attendance WHERE employee_id = ? AND attendance_date = ?",
                (employee_id, day), one=True
            )
            present = att is not None and att.get("punch_in_status") == "approved"
            on_time = False
            if present and att.get("punch_in_time"):
                try:
                    pit = datetime.strptime(att["punch_in_time"], "%Y-%m-%d %H:%M:%S")
                    shift_dt = datetime.strptime(f"{day} {shift_start}", "%Y-%m-%d %H:%M")
                    on_time = pit <= shift_dt
                except Exception:
                    on_time = False

            streak_data.append({
                "date": day,
                "hitTarget": day_rev["v"] >= daily_target if daily_target > 0 else False,
                "present": present,
                "onTime": on_time,
            })

        # Gamification
        gam = get_employee_gamification(employee_id)
        streak_count = gam.get("streak", 0) if gam else 0

        # Calculate longest streak from streak_data
        longest = 0
        current = 0
        for d in streak_data:
            if d["hitTarget"] and d["present"]:
                current += 1
                longest = max(longest, current)
            else:
                current = 0

        # Current streak (counting from today backwards)
        current_streak = 0
        for d in reversed(streak_data):
            if d["hitTarget"] and d["present"]:
                current_streak += 1
            else:
                break

        # Weekly XP
        weekly_xp = get_xp_for_score(score_data.get("productivity_index", 0))

        # Bonus XP
        streak_bonus = 200 if current_streak >= 7 else 0
        leaderboard_bonus = 300 if rank <= 3 else 0
        avg_rating = query(
            "SELECT COALESCE(AVG(rating), 0) as v FROM manager_ratings WHERE employee_id = ? AND rating_date BETWEEN ? AND ?",
            (employee_id, ws, we), one=True
        )
        rating_bonus = 150 if avg_rating and avg_rating["v"] >= 5.0 else 0

        return {
            "employee": {
                "employeeId": str(employee_id),
                "name": emp["name"],
                "department": emp["department"],
                "level": level_info.get("level", 1),
                "levelLabel": level_info.get("title", "Rookie"),
                "xp": emp["total_xp"],
                "xpToNextLevel": level_info.get("xp_to_next", 0),
                "weeklyTarget": weekly_target,
                "shiftStartTime": emp.get("shift_start_time", "09:00"),
            },
            "currentWeek": {
                "weekNumber": week_number,
                "year": year,
                "pScore": score_data.get("productivity_index", 0),
                "M1": round(metrics.get("revenue_vs_target", 0), 1),
                "M2": round(metrics.get("basket_performance", 0), 1),
                "M3": round(metrics.get("manager_rating", 0), 1),
                "M4": round(metrics.get("growth_trend", 0), 1),
                "M5": round(metrics.get("stability_index", 0), 1),
                "M7": round(metrics.get("attendance_rate", 0), 1),
                "M8": round(metrics.get("punctuality", 0), 1),
                "weeklyRevenue": weekly_revenue,
                "totalBills": total_bills_row["v"],
                "avgBasketSize": round(avg_basket_row["v"], 2),
                "revenueRemaining": revenue_remaining,
            },
            "weeklyTrend": weekly_trend,
            "streakData": streak_data,
            "gamification": {
                "currentStreak": current_streak,
                "longestStreak": longest,
                "rank": rank,
                "totalEmployees": total_employees,
                "weeklyXP": weekly_xp,
                "bonusXP": {
                    "streakBonus": streak_bonus,
                    "leaderboardBonus": leaderboard_bonus,
                    "ratingBonus": rating_bonus,
                },
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/manager/store-overview")
async def store_overview(store_id: int = 1):
    """Returns all data needed for manager dashboard charts."""
    try:
        ws, we = get_date_range("weekly")
        today = datetime.now()
        week_number = today.isocalendar()[1]

        store = query("SELECT id, name FROM stores WHERE id = ?", (store_id,), one=True)
        if not store:
            raise HTTPException(status_code=404, detail="Store not found")

        employees = query(
            """SELECT e.id, e.name, d.name as department, d.weekly_revenue_target,
                      e.store_id
               FROM employees e
               JOIN departments d ON e.department_id = d.id
               WHERE e.store_id = ? AND e.role = 'employee' AND e.is_active = 1""",
            (store_id,)
        )

        # Per-employee current week data
        emp_data = []
        for emp in employees:
            score = compute_productivity_index(emp["id"], ws, we)
            m = score.get("metrics", {})
            rev_row = query(
                "SELECT COALESCE(SUM(revenue), 0) as v FROM sales WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?",
                (emp["id"], ws, we), one=True
            )
            bills_row = query(
                "SELECT COUNT(*) as v FROM sales WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?",
                (emp["id"], ws, we), one=True
            )
            basket_row = query(
                "SELECT COALESCE(AVG(basket_size), 0) as v FROM sales WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?",
                (emp["id"], ws, we), one=True
            )

            emp_data.append({
                "employeeId": str(emp["id"]),
                "name": emp["name"],
                "department": emp["department"],
                "pScore": score.get("productivity_index", 0),
                "M1": round(m.get("revenue_vs_target", 0), 1),
                "M2": round(m.get("basket_performance", 0), 1),
                "M3": round(m.get("manager_rating", 0), 1),
                "M4": round(m.get("growth_trend", 0), 1),
                "M5": round(m.get("stability_index", 0), 1),
                "M7": round(m.get("attendance_rate", 0), 1),
                "M8": round(m.get("punctuality", 0), 1),
                "weeklyRevenue": round(rev_row["v"], 2),
                "weeklyTarget": emp["weekly_revenue_target"] or 0,
                "totalBills": bills_row["v"],
                "avgBasketSize": round(basket_row["v"], 2),
                "attendanceRate": round(m.get("attendance_rate", 0), 1),
                "punctualityScore": round(m.get("punctuality", 0), 1),
            })

        # Store summary
        total_rev = sum(e["weeklyRevenue"] for e in emp_data)
        avg_p = round(sum(e["pScore"] for e in emp_data) / max(1, len(emp_data)), 1)
        avg_att = round(sum(e["attendanceRate"] for e in emp_data) / max(1, len(emp_data)), 1)
        above_target = sum(1 for e in emp_data if e["weeklyRevenue"] >= e["weeklyTarget"])
        below_target = len(emp_data) - above_target

        flagged_count = query(
            "SELECT COUNT(*) as v FROM sales WHERE is_flagged = 1 AND resolved_by_admin = 0", one=True
        )
        geofence_count = query(
            "SELECT COUNT(*) as v FROM geofence_alerts WHERE resolved = 0", one=True
        )

        # Weekly trend — last 8 weeks store-level
        weekly_trend = []
        for i in range(7, -1, -1):
            wk_start = (today - timedelta(days=today.weekday()) - timedelta(weeks=i)).strftime("%Y-%m-%d")
            wk_end = (datetime.strptime(wk_start, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")
            wk_num = datetime.strptime(wk_start, "%Y-%m-%d").isocalendar()[1]

            store_rev = query(
                """SELECT COALESCE(SUM(s.revenue), 0) as v FROM sales s
                   JOIN employees e ON s.employee_id = e.id
                   WHERE e.store_id = ? AND s.status = 'approved' AND s.sale_date BETWEEN ? AND ?""",
                (store_id, wk_start, wk_end), one=True
            )

            # Avg pScore and attendance for the week
            wk_scores = []
            wk_att = []
            for emp in employees:
                sc = compute_productivity_index(emp["id"], wk_start, wk_end)
                wk_scores.append(sc.get("productivity_index", 0))
                att_days = query(
                    "SELECT COUNT(*) as v FROM attendance WHERE employee_id = ? AND punch_in_status = 'approved' AND attendance_date BETWEEN ? AND ?",
                    (emp["id"], wk_start, wk_end), one=True
                )
                # 6 working days per week
                wk_att.append(round((att_days["v"] / 6) * 100, 1) if att_days else 0)

            weekly_trend.append({
                "week": f"W{wk_num}",
                "avgPScore": round(sum(wk_scores) / max(1, len(wk_scores)), 1),
                "totalRevenue": round(store_rev["v"], 2),
                "avgAttendance": round(sum(wk_att) / max(1, len(wk_att)), 1),
            })

        # Basket trend — last 8 weeks per employee
        basket_trend = []
        for i in range(7, -1, -1):
            wk_start = (today - timedelta(days=today.weekday()) - timedelta(weeks=i)).strftime("%Y-%m-%d")
            wk_end = (datetime.strptime(wk_start, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")
            wk_num = datetime.strptime(wk_start, "%Y-%m-%d").isocalendar()[1]

            emp_baskets = []
            for emp in employees:
                bsk = query(
                    "SELECT COALESCE(AVG(basket_size), 0) as v FROM sales WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?",
                    (emp["id"], wk_start, wk_end), one=True
                )
                emp_baskets.append({
                    "employeeId": str(emp["id"]),
                    "name": emp["name"],
                    "avgBasketSize": round(bsk["v"], 2),
                })

            basket_trend.append({
                "week": f"W{wk_num}",
                "employees": emp_baskets,
            })

        # Attendance matrix — last 28 days × all employees
        store_shift = query("SELECT shift_start_time FROM stores WHERE id = ?", (store_id,), one=True)
        shift_time = store_shift["shift_start_time"] if store_shift else "09:00"

        attendance_matrix = []
        for emp in employees:
            days = []
            for i in range(27, -1, -1):
                day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
                day_dt = datetime.strptime(day, "%Y-%m-%d")

                # Skip Sundays
                if day_dt.weekday() == 6:
                    days.append({"date": day, "status": "DAY_OFF"})
                    continue

                att = query(
                    "SELECT punch_in_time, punch_in_status FROM attendance WHERE employee_id = ? AND attendance_date = ?",
                    (emp["id"], day), one=True
                )

                if not att or att.get("punch_in_status") != "approved":
                    days.append({"date": day, "status": "ABSENT"})
                else:
                    try:
                        pit = datetime.strptime(att["punch_in_time"], "%Y-%m-%d %H:%M:%S")
                        shift_dt = datetime.strptime(f"{day} {shift_time}", "%Y-%m-%d %H:%M")
                        diff_min = (pit - shift_dt).total_seconds() / 60
                        if diff_min <= 0:
                            status = "ON_TIME"
                        elif diff_min <= 30:
                            status = "LATE"
                        else:
                            status = "VERY_LATE"
                    except Exception:
                        status = "ON_TIME"
                    days.append({"date": day, "status": status})

            attendance_matrix.append({
                "employeeId": str(emp["id"]),
                "name": emp["name"],
                "days": days,
            })

        return {
            "storeId": str(store_id),
            "storeName": store["name"],
            "currentWeek": {
                "weekNumber": week_number,
                "employees": emp_data,
                "storeSummary": {
                    "avgPScore": avg_p,
                    "totalRevenue": round(total_rev, 2),
                    "avgAttendance": avg_att,
                    "flaggedSalesPending": flagged_count["v"] if flagged_count else 0,
                    "geofenceAlertsPending": geofence_count["v"] if geofence_count else 0,
                    "employeesAboveTarget": above_target,
                    "employeesBelowTarget": below_target,
                },
            },
            "weeklyTrend": weekly_trend,
            "basketTrend": basket_trend,
            "attendanceMatrix": attendance_matrix,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/manager/department-summary")
async def department_summary(store_id: int = 1):
    """Returns department-level aggregates for comparison charts."""
    try:
        ws, we = get_date_range("weekly")

        departments = query("SELECT id, name FROM departments WHERE store_id = ?", (store_id,))

        dept_data = []
        for dept in departments:
            emps = query(
                "SELECT id FROM employees WHERE department_id = ? AND role = 'employee' AND is_active = 1",
                (dept["id"],)
            )
            headcount = len(emps)
            if headcount == 0:
                dept_data.append({
                    "department": dept["name"],
                    "avgPScore": 0, "avgRevenue": 0, "avgBasketSize": 0,
                    "avgAttendance": 0, "headcount": 0, "employeesAboveTarget": 0,
                })
                continue

            scores = []
            revs = []
            baskets = []
            att_rates = []
            above_target = 0

            dept_target = query(
                "SELECT weekly_revenue_target FROM departments WHERE id = ?",
                (dept["id"],), one=True
            )
            target = dept_target["weekly_revenue_target"] if dept_target else 0

            for emp in emps:
                sc = compute_productivity_index(emp["id"], ws, we)
                scores.append(sc.get("productivity_index", 0))
                m = sc.get("metrics", {})
                att_rates.append(m.get("attendance_rate", 0))

                rev = query(
                    "SELECT COALESCE(SUM(revenue), 0) as v FROM sales WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?",
                    (emp["id"], ws, we), one=True
                )
                bsk = query(
                    "SELECT COALESCE(AVG(basket_size), 0) as v FROM sales WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?",
                    (emp["id"], ws, we), one=True
                )
                revs.append(rev["v"])
                baskets.append(bsk["v"])
                if rev["v"] >= target:
                    above_target += 1

            dept_data.append({
                "department": dept["name"],
                "avgPScore": round(sum(scores) / headcount, 1),
                "avgRevenue": round(sum(revs) / headcount, 2),
                "avgBasketSize": round(sum(baskets) / headcount, 2),
                "avgAttendance": round(sum(att_rates) / headcount, 1),
                "headcount": headcount,
                "employeesAboveTarget": above_target,
            })

        return {"departments": dept_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
