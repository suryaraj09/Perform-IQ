"""PerformIQ — FastAPI Analytics Backend."""

import os
import sys
import uuid
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Ensure imports work
sys.path.insert(0, str(Path(__file__).parent))

from database import init_db, query, execute
from metrics.productivity import compute_productivity_index
from metrics.growth import get_growth_trend_data
from metrics.clustering import cluster_employees
from gamification import get_employee_gamification, get_leaderboard, get_level_info, get_xp_for_score
from attendance import punch_in, punch_out, get_attendance_status

# --- App Setup ---
app = FastAPI(title="PerformIQ API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for uploads
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "receipts").mkdir(exist_ok=True)
(UPLOAD_DIR / "screenshots").mkdir(exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# SSE event queue for manager alerts
alert_queues: list = []


# --- Pydantic Models ---
class SaleSubmission(BaseModel):
    employee_id: int
    revenue: float
    basket_size: float
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


class AuthRegister(BaseModel):
    firebase_uid: str
    name: str
    email: str
    role: str = "employee"
    store_id: int = 1
    department_id: int = 1


# ==================== AUTH ENDPOINTS ====================

@app.post("/api/auth/register")
async def register_user(data: AuthRegister):
    """Register a new user after Firebase sign-up."""
    # Check if firebase_uid already registered
    existing = query("SELECT id FROM employees WHERE firebase_uid = ?", (data.firebase_uid,), one=True)
    if existing:
        return await get_profile(data.firebase_uid)

    employee_id = execute(
        """INSERT INTO employees (name, email, role, department_id, store_id, firebase_uid, total_xp, level, level_title)
           VALUES (?, ?, ?, ?, ?, ?, 0, 1, 'Rookie')""",
        (data.name, data.email, data.role, data.department_id, data.store_id, data.firebase_uid),
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
    """Get employee profile by Firebase UID."""
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


# --- Date Range Helper ---
def get_date_range(range_type: str = "weekly", start: str = None, end: str = None):
    """Compute start/end dates from range type."""
    today = datetime.now()
    if range_type == "custom" and start and end:
        return start, end
    elif range_type == "daily":
        return today.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    elif range_type == "monthly":
        start_date = today.replace(day=1)
        return start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    else:  # weekly (default)
        start_date = today - timedelta(days=today.weekday())
        return start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


def get_full_date_range():
    """Get the full 8-week date range for overall stats."""
    return "2026-01-12", datetime.now().strftime("%Y-%m-%d")


# --- Startup ---
@app.on_event("startup")
async def startup():
    init_db()


# --- Upload Endpoint ---
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), category: str = Form("receipts")):
    """Upload an image file (receipt or screenshot)."""
    ext = Path(file.filename).suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    folder = UPLOAD_DIR / category
    folder.mkdir(exist_ok=True)
    filepath = folder / filename

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    return {"path": f"uploads/{category}/{filename}", "filename": filename}


# ==================== SALES ENDPOINTS ====================

@app.post("/api/sales")
async def submit_sale(sale: SaleSubmission):
    """Employee submits a sale record."""
    sale_id = execute(
        """INSERT INTO sales (employee_id, revenue, basket_size, num_items, receipt_photo_path, status, sale_date)
           VALUES (?, ?, ?, ?, ?, 'pending', date('now'))""",
        (sale.employee_id, sale.revenue, sale.basket_size, sale.num_items, sale.receipt_photo_path),
    )
    # Notify managers via SSE
    await broadcast_alert({
        "type": "new_sale",
        "message": f"New sale submission (₹{sale.revenue:.0f}) pending review",
        "employee_id": sale.employee_id,
        "sale_id": sale_id,
    })
    return {"id": sale_id, "status": "pending", "message": "Sale submitted for review"}


@app.get("/api/sales")
async def list_sales(
    employee_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
):
    """List sales, optionally filtered."""
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
    """Manager approves/rejects a sale."""
    execute(
        "UPDATE sales SET status = ?, reviewed_by = ?, reviewed_at = datetime('now'), rejection_reason = ? WHERE id = ?",
        (review.status, review.reviewer_id, review.rejection_reason, sale_id),
    )
    return {"id": sale_id, "status": review.status, "message": f"Sale {review.status}"}


# ==================== APP DOWNLOADS ENDPOINTS ====================

@app.post("/api/app-downloads")
async def submit_download(employee_id: int = Form(...), screenshot_photo_path: Optional[str] = Form(None), customer_name: Optional[str] = Form(None)):
    """Employee submits an app download record."""
    dl_id = execute(
        """INSERT INTO app_downloads (employee_id, screenshot_photo_path, customer_name, status, download_date)
           VALUES (?, ?, ?, 'pending', date('now'))""",
        (employee_id, screenshot_photo_path, customer_name),
    )
    return {"id": dl_id, "status": "pending"}


@app.put("/api/app-downloads/{download_id}/review")
async def review_download(download_id: int, review: ReviewAction):
    """Manager approves/rejects a download."""
    execute(
        "UPDATE app_downloads SET status = ?, reviewed_by = ?, reviewed_at = datetime('now'), rejection_reason = ? WHERE id = ?",
        (review.status, review.reviewer_id, review.rejection_reason, download_id),
    )
    return {"id": download_id, "status": review.status}


# ==================== EMPLOYEE ENDPOINTS ====================

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
    """Get single employee details."""
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
    """Get real-time productivity score with metric breakdown."""
    start_date, end_date = get_date_range(range, start, end)
    return compute_productivity_index(employee_id, start_date, end_date)


@app.get("/api/employees/{employee_id}/gamification")
async def get_gamification(employee_id: int):
    """Get XP, level, badges, streaks."""
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
    """Get growth trend data for charting."""
    if range == "weekly":
        s, e = get_full_date_range()
    else:
        s, e = get_date_range(range, start, end)
    return get_growth_trend_data(employee_id, s, e)


# ==================== LEADERBOARD ====================

@app.get("/api/leaderboard")
async def leaderboard(
    department_id: Optional[int] = None,
    store_id: Optional[int] = None,
    limit: int = 20,
):
    """Get ranked leaderboard."""
    return get_leaderboard(department_id, store_id, limit)


# ==================== ANALYTICS ENDPOINTS ====================

@app.get("/api/clustering")
async def get_clustering(
    department_id: Optional[int] = None,
    n_clusters: int = 3,
    range: str = "monthly",
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    """K-Means employee clustering."""
    s, e = get_full_date_range() if range == "weekly" else get_date_range(range, start, end)
    return cluster_employees(department_id, s, e, n_clusters)


@app.get("/api/correlations")
async def get_correlations(department_id: Optional[int] = None):
    """Get correlation matrix between performance metrics."""
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
    """Department-level analytics."""
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


# ==================== ATTENDANCE ENDPOINTS ====================

@app.post("/api/attendance/punch-in")
async def api_punch_in(req: PunchRequest):
    """Punch in with GPS verification."""
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
    """Punch out with GPS."""
    return punch_out(req.employee_id, req.latitude, req.longitude)


@app.get("/api/attendance")
async def get_attendance(employee_id: Optional[int] = None, limit: int = 30):
    """Get attendance history."""
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
    """Get current shift status."""
    return get_attendance_status(employee_id)


# ==================== MANAGER ENDPOINTS ====================

@app.get("/api/manager/review-queue")
async def review_queue():
    """Get all pending submissions."""
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
    """Manager gives daily rating."""
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
    """Get today's attendance for all employees."""
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


# ==================== SSE ENDPOINT ====================

async def broadcast_alert(alert: dict):
    """Send alert to all connected manager clients."""
    alert["timestamp"] = datetime.now().isoformat()
    for q in alert_queues:
        await q.put(alert)


@app.get("/api/stream/alerts")
async def stream_alerts():
    """SSE endpoint for live manager alerts."""
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
    """All-in-one employee dashboard data."""
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

    # Weekly stats
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
    """All-in-one manager dashboard data."""
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
