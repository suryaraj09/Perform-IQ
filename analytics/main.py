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
    app_download: bool = False
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


def get_app_download_rate(employee_id: int) -> float:
    """Get app download rate from sales in last 7 days."""
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")
    total = query(
        "SELECT COUNT(*) as v FROM sales WHERE employee_id = ? AND sale_date BETWEEN ? AND ?",
        (employee_id, seven_days_ago, today), one=True
    )
    downloads = query(
        "SELECT COUNT(*) as v FROM sales WHERE employee_id = ? AND app_download = 1 AND sale_date BETWEEN ? AND ?",
        (employee_id, seven_days_ago, today), one=True
    )
    total_bills = total["v"] if total else 0
    if total_bills == 0:
        return 0.0
    return (downloads["v"] if downloads else 0) / total_bills


def check_for_flags(sale_revenue: float, num_items: int, app_download: bool, employee_id: int) -> list:
    """Run all 5 flag rules and return triggered flags."""
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

    # RULE 5 — HIGH_APP_DOWNLOAD_RATE
    if app_download:
        dl_rate = get_app_download_rate(employee_id)
        if dl_rate > 0.80:
            flags.append({
                "rule": "HIGH_APP_DOWNLOAD_RATE",
                "detail": f"App download rate of {dl_rate*100:.0f}% over last 7 days is suspiciously high"
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
    flags = check_for_flags(sale.revenue, sale.num_items, sale.app_download, sale.employee_id)
    is_flagged = len(flags) > 0

    sale_id = execute(
        """INSERT INTO sales (employee_id, revenue, basket_size, num_items, app_download,
           receipt_photo_path, status, is_flagged, flags, resolved_by_admin, sale_date)
           VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, 0, date('now'))""",
        (sale.employee_id, sale.revenue, basket_size, sale.num_items,
         1 if sale.app_download else 0, sale.receipt_photo_path,
         1 if is_flagged else 0, json.dumps(flags)),
    )

    if sale.app_download:
        execute(
            """INSERT INTO app_downloads (employee_id, status, download_date)
               VALUES (?, 'approved', date('now'))""",
            (sale.employee_id,),
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
    total_app_downloads = query(
        "SELECT COUNT(*) as v FROM app_downloads WHERE employee_id = ? AND download_date BETWEEN ? AND ?",
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
            "totalAppDownloads": total_app_downloads["v"],
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

@app.post("/api/app-downloads")
async def submit_download(employee_id: int = Form(...), screenshot_photo_path: Optional[str] = Form(None), customer_name: Optional[str] = Form(None)):
    dl_id = execute(
        """INSERT INTO app_downloads (employee_id, screenshot_photo_path, customer_name, status, download_date)
           VALUES (?, ?, ?, 'pending', date('now'))""",
        (employee_id, screenshot_photo_path, customer_name),
    )
    return {"id": dl_id, "status": "pending"}


@app.put("/api/app-downloads/{download_id}/review")
async def review_download(download_id: int, review: ReviewAction):
    execute(
        "UPDATE app_downloads SET status = ?, reviewed_by = ?, reviewed_at = datetime('now'), rejection_reason = ? WHERE id = ?",
        (review.status, review.reviewer_id, review.rejection_reason, download_id),
    )
    return {"id": download_id, "status": review.status}


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

    metric_labels = ["Revenue", "Basket Size", "Manager Rating", "Attendance", "App Downloads"]
    data_matrix = []

    for emp in employees:
        eid = emp["id"]
        rev = query("SELECT COALESCE(SUM(revenue), 0) as v FROM sales WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?", (eid, s, e), one=True)
        basket = query("SELECT COALESCE(AVG(basket_size), 0) as v FROM sales WHERE employee_id = ? AND status = 'approved' AND sale_date BETWEEN ? AND ?", (eid, s, e), one=True)
        rating = query("SELECT COALESCE(AVG(rating), 0) as v FROM manager_ratings WHERE employee_id = ? AND rating_date BETWEEN ? AND ?", (eid, s, e), one=True)
        att = query("SELECT COUNT(*) as v FROM attendance WHERE employee_id = ? AND punch_in_status = 'approved' AND attendance_date BETWEEN ? AND ?", (eid, s, e), one=True)
        dl = query("SELECT COUNT(*) as v FROM app_downloads WHERE employee_id = ? AND status = 'approved' AND download_date BETWEEN ? AND ?", (eid, s, e), one=True)

        data_matrix.append([rev["v"], basket["v"], rating["v"], att["v"], dl["v"]])

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
    pending_downloads = query(
        """SELECT a.*, e.name as employee_name, 'download' as type FROM app_downloads a
           JOIN employees e ON a.employee_id = e.id
           WHERE a.status = 'pending' ORDER BY a.submitted_at DESC"""
    )
    return {"sales": pending_sales, "downloads": pending_downloads, "total": len(pending_sales) + len(pending_downloads)}


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
                  s.basket_size as basketSize, s.app_download as appDownload,
                  s.receipt_photo_path as receiptPhoto, s.submitted_at as submittedAt,
                  s.flags, s.is_flagged as isFlagged, s.resolved_by_admin as resolvedByAdmin
           FROM sales s
           JOIN employees e ON s.employee_id = e.id
           JOIN departments d ON e.department_id = d.id
           WHERE s.is_flagged = 1 AND s.resolved_by_admin = 0
           ORDER BY s.submitted_at DESC"""
    )
    result = []
    for row in rows:
        r = dict(row)
        try:
            r["flags"] = json.loads(r["flags"]) if r["flags"] else []
        except (json.JSONDecodeError, TypeError):
            r["flags"] = []
        r["appDownload"] = bool(r["appDownload"])
        r["isFlagged"] = bool(r["isFlagged"])
        r["resolvedByAdmin"] = bool(r["resolvedByAdmin"])
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
        total_app_downloads = query(
            "SELECT COUNT(*) as v FROM app_downloads WHERE employee_id = ? AND download_date BETWEEN ? AND ?",
            (emp_id, ws, we), one=True
        )
        avg_basket = query(
            "SELECT COALESCE(AVG(basket_size), 0) as v FROM sales WHERE employee_id = ? AND sale_date BETWEEN ? AND ? AND admin_action IS NOT 'REJECTED'",
            (emp_id, ws, we), one=True
        )
        weekly_totals = {
            "weeklyRevenue": round(weekly_revenue["v"], 2),
            "totalBills": total_bills["v"],
            "totalAppDownloads": total_app_downloads["v"],
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
        total_app_downloads = query(
            "SELECT COUNT(*) as v FROM app_downloads WHERE employee_id = ? AND download_date BETWEEN ? AND ?",
            (emp_id, ws, we), one=True
        )
        avg_basket = query(
            "SELECT COALESCE(AVG(basket_size), 0) as v FROM sales WHERE employee_id = ? AND sale_date BETWEEN ? AND ?",
            (emp_id, ws, we), one=True
        )
        weekly_totals = {
            "weeklyRevenue": round(weekly_revenue["v"], 2),
            "totalBills": total_bills["v"],
            "totalAppDownloads": total_app_downloads["v"],
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
    weekly_downloads = query(
        "SELECT COUNT(*) as v FROM app_downloads WHERE employee_id = ? AND status = 'approved' AND download_date BETWEEN ? AND ?",
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
            "app_downloads": weekly_downloads["v"],
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
