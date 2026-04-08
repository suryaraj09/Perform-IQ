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

from fastapi import Request
from fastapi.responses import JSONResponse
from firebase_admin import auth
import firebase_admin_setup
firebase_admin_setup.init_firebase()

from database import init_db, query, execute
from metrics.productivity import compute_productivity_index
from metrics.growth import get_growth_trend_data
from metrics.clustering import cluster_employees
from gamification import get_employee_gamification, get_leaderboard, get_level_info, get_xp_for_score
from attendance import punch_in, punch_out, get_attendance_status
from migrate_weights import run_migration
<<<<<<< HEAD
=======
from migrate_phase4 import run_phase4_migration
from backfill_scores import backfill_all_scores
from metrics.clustering import run_performance_clustering
from migrate_warehouse import run_warehouse_migration
from migrate_phase6 import migrate as run_phase6_migration
from etl_pipeline import run_etl
>>>>>>> 55b7e13 (Removed JSON files containing secrets)

app = FastAPI(title="PerformIQ API", version="1.0.0")

from aggregation_job import run_weekly_aggregation, get_current_week
import asyncio

@app.middleware("http")
async def require_firebase_auth(request: Request, call_next):
    # Skip auth for these routes
    open_paths = ["/docs", "/openapi.json", "/api/upload", "/api/admin/set-user-claims"]
    if any(request.url.path.startswith(p) for p in open_paths) or request.method == "OPTIONS":
        return await call_next(request)
        
    if not request.url.path.startswith("/api/"):
        return await call_next(request)
        
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        
    token = auth_header.split("Bearer ")[1]
    
    # Demo / quick-test bypass
    if token == "demo-token":
        request.state.user = {"uid": "demo", "role": "STORE_MANAGER", "storeId": "S001", "employeeId": "1"}
        request.state.scoped_store_id = "S001"
        return await call_next(request)
    
    try:
        decoded = auth.verify_id_token(token)
        request.state.user = decoded
        role = decoded.get("role")
        store_id = decoded.get("storeId")
        
        if role == 'STORE_MANAGER':
            request.state.scoped_store_id = store_id
        elif role == 'EMPLOYEE':
            request.state.scoped_store_id = store_id
        elif role == 'HEAD_OFFICE':
            request.state.scoped_store_id = request.query_params.get("store_id")
            
        if request.url.path.startswith("/api/manager") and role not in ["STORE_MANAGER", "HEAD_OFFICE"]:
            return JSONResponse(status_code=403, content={"error": "Forbidden - manager access required"})
            
        if request.url.path.startswith("/api/admin") and request.url.path != "/api/admin/set-user-claims" and role != "HEAD_OFFICE":
            return JSONResponse(status_code=403, content={"error": "Forbidden - head office required"})

        response = await call_next(request)
        return response
    except Exception as e:
        print(f"Auth error: {e}")
        return JSONResponse(status_code=401, content={"error": "Invalid token"})


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
    store_id: str = "S001"
    department_id: int = 1

# --- Admin Models ---
class StoreCreate(BaseModel):
    storeName: str
    storeLocation: str
    storeLat: float
    storeLng: float
    geofenceRadius: float = 100

class StoreUpdate(BaseModel):
    storeName: Optional[str] = None
    storeLocation: Optional[str] = None
    storeLat: Optional[float] = None
    storeLng: Optional[float] = None
    geofenceRadius: Optional[float] = None
    isActive: Optional[bool] = None

class EmployeeCreate(BaseModel):
    name: str
    department: str # Name or ID
    storeId: str
    shiftStartTime: str
    email: str
    temporaryPassword: str

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    storeId: Optional[str] = None
    shiftStartTime: Optional[str] = None
    isActive: Optional[bool] = None

class PasswordReset(BaseModel):
    newPassword: str

class TargetBulkEntry(BaseModel):
    employeeId: int
    targetAmount: float

class TargetBulkSet(BaseModel):
    weekNumber: int
    year: int
    targets: List[TargetBulkEntry]
    setBy: str

class ConfigUpdate(BaseModel):
    value: str # JSON or Number
    reason: str
    effectiveFromWeek: Optional[int] = None
    effectiveFromYear: Optional[int] = None

class EmployeeRatingEntry(BaseModel):
    employeeId: int
    rating: int

class RatingBulkSet(BaseModel):
    date: str
    storeId: str
    ratings: List[EmployeeRatingEntry]
    ratedBy: str


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
        """SELECT e.*, d.name as department_name, s.store_name as store_name
           FROM employees e
           JOIN departments d ON e.department_id = d.id
           JOIN stores s ON e.store_id = s.store_id
           WHERE e.id = ?""",
        (employee_id,), one=True
    )


@app.get("/api/auth/profile/{firebase_uid}")
async def get_profile(firebase_uid: str):
    emp = query(
        """SELECT e.*, d.name as department_name, s.store_name as store_name
           FROM employees e
           JOIN departments d ON e.department_id = d.id
           JOIN stores s ON e.store_id = s.store_id
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
<<<<<<< HEAD
    """Run all 4 flag rules and return triggered flags."""
=======
    """Run flag rules and return triggered flags using DB thresholds."""
    from config_service import get_config
>>>>>>> 55b7e13 (Removed JSON files containing secrets)
    flags = []

    # RULE 1 — HIGH_SALE_AMOUNT
    hsa_multiplier = get_config('FLAG_HIGH_SALE_MULTIPLIER')
    avg_sale = get_employee_avg_sale(employee_id)
    if sale_revenue > avg_sale * hsa_multiplier:
        flags.append({
            "rule": "HIGH_SALE_AMOUNT",
            "detail": f"Sale \u20b9{sale_revenue:.0f} is {hsa_multiplier}x above average \u20b9{avg_sale:.0f}"
        })

    # RULE 2 — HIGH_ITEM_COUNT
    hic_limit = get_config('FLAG_HIGH_ITEM_COUNT')
    if num_items > hic_limit:
        flags.append({
            "rule": "HIGH_ITEM_COUNT",
            "detail": f"{num_items} items in a single bill is above limit of {hic_limit}"
        })

    # RULE 3 — RAPID_SUBMISSION
    rss_seconds = get_config('FLAG_RAPID_SUBMISSION_SECONDS')
    last_ts = get_last_sale_timestamp(employee_id)
    if last_ts is not None:
        now_ms = datetime.now().timestamp() * 1000
        diff_seconds = (now_ms - last_ts) / 1000
        if diff_seconds < rss_seconds:
            flags.append({
                "rule": "RAPID_SUBMISSION",
                "detail": f"Submitted {int(diff_seconds)}s after previous sale (Limit: {rss_seconds}s)"
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
    """Auto-confirm flagged sales based on dynamic hours limit, runs every hour."""
    from config_service import get_config
    while True:
        await asyncio.sleep(3600)  # every hour
        try:
            hours_limit = get_config('FLAG_AUTO_CONFIRM_HOURS')
            cutoff = (datetime.now() - timedelta(hours=hours_limit)).strftime("%Y-%m-%d %H:%M:%S")
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
                print(f"Auto-confirmed {len(stale)} flagged sales after {hours_limit}h")
        except Exception as e:
            print(f"Auto-confirm error: {e}")


@app.on_event("startup")
async def startup():
    init_db()
    run_migration()
<<<<<<< HEAD
=======
    run_phase4_migration()
    run_warehouse_migration()
    run_phase6_migration()
    backfill_all_scores()
>>>>>>> 55b7e13 (Removed JSON files containing secrets)
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
async def list_employees(department_id: Optional[int] = None, store_id: Optional[str] = None, role: Optional[str] = None):
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
        f"""SELECT e.*, d.name as department_name, s.store_name as store_name
            FROM employees e 
            JOIN departments d ON e.department_id = d.id
            JOIN stores s ON e.store_id = s.store_id
            {where} ORDER BY e.name""",
        tuple(params),
    )


@app.get("/api/employees/{employee_id}")
async def get_employee(employee_id: int):
    emp = query(
        """SELECT e.*, d.name as department_name, s.store_name as store_name
           FROM employees e
           JOIN departments d ON e.department_id = d.id
           JOIN stores s ON e.store_id = s.store_id
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
    request: Request,
    department_id: Optional[int] = None,
    limit: int = 20,
):
    store_id = getattr(request.state, "scoped_store_id", None)
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
async def attendance_overview(request: Request):
    store_id = getattr(request.state, "scoped_store_id", "S001") or "S001"
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
async def pending_employees(request: Request, store_id: Optional[str] = None):
    store_id = getattr(request.state, "scoped_store_id", "S001") or "S001"
    where, params = "WHERE e.status = 'pending'", []
    if store_id:
        where += " AND e.store_id = ?"
        params.append(store_id)
        
    return query(
        f"""SELECT e.*, d.name as department_name, s.store_name as store_name
            FROM employees e
            JOIN departments d ON e.department_id = d.id
            JOIN stores s ON e.store_id = s.store_id
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
        """SELECT e.*, d.name as department_name, s.store_name as store_name
           FROM employees e JOIN departments d ON e.department_id = d.id
           JOIN stores s ON e.store_id = s.store_id WHERE e.id = ?""",
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
async def manager_dashboard(store_id: str = "S001"):
    ws, we = get_date_range("weekly")

    departments = query("SELECT * FROM departments WHERE store_id_text = ? OR store_id = ?", (store_id, store_id))

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
    today = datetime.now().strftime("%Y-%m-%d")
    today_attendance = query(
        """SELECT e.id, e.name, e.department_id, d.name as department_name,
                  a.punch_in_time, a.punch_out_time, a.punch_in_status, a.hours_worked
           FROM employees e
           JOIN departments d ON e.department_id = d.id
           LEFT JOIN attendance a ON e.id = a.employee_id AND a.attendance_date = ?
           WHERE e.role = 'employee' AND e.is_active = 1 AND e.store_id = ?
           ORDER BY e.name""",
        (today, store_id),
    )

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
<<<<<<< HEAD
                      s.name as store_name, s.shift_start_time, e.store_id
               FROM employees e
               JOIN departments d ON e.department_id = d.id
               JOIN stores s ON e.store_id = s.id
=======
                      s.store_name as store_name, e.store_id
               FROM employees e
               JOIN departments d ON e.department_id = d.id
               JOIN stores s ON e.store_id = s.store_id
>>>>>>> 55b7e13 (Removed JSON files containing secrets)
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
<<<<<<< HEAD
        store_info = query("SELECT shift_start_time FROM stores WHERE id = ?", (emp["store_id"],), one=True)
=======
        store_info = query("SELECT shift_start_time FROM stores WHERE store_id = ?", (emp["store_id"],), one=True)
>>>>>>> 55b7e13 (Removed JSON files containing secrets)
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
<<<<<<< HEAD
async def store_overview(store_id: int = 1):
=======
async def store_overview(request: Request, store_id: Optional[str] = None):
    """Returns key metrics for a specific store."""
    if store_id is None:
        store_id = getattr(request.state, "scoped_store_id", "S001") or "S001"
>>>>>>> 55b7e13 (Removed JSON files containing secrets)
    """Returns all data needed for manager dashboard charts."""
    try:
        ws, we = get_date_range("weekly")
        today = datetime.now()
        week_number = today.isocalendar()[1]

<<<<<<< HEAD
        store = query("SELECT id, name FROM stores WHERE id = ?", (store_id,), one=True)
=======
        store = query("SELECT store_id as id, store_name as name FROM stores WHERE store_id = ?", (store_id,), one=True)
>>>>>>> 55b7e13 (Removed JSON files containing secrets)
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
<<<<<<< HEAD
        store_shift = query("SELECT shift_start_time FROM stores WHERE id = ?", (store_id,), one=True)
=======
        store_shift = query("SELECT shift_start_time FROM stores WHERE store_id = ?", (store_id,), one=True)
>>>>>>> 55b7e13 (Removed JSON files containing secrets)
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
<<<<<<< HEAD
async def department_summary(store_id: int = 1):
=======
async def department_summary(request: Request):
    store_id = getattr(request.state, "scoped_store_id", "S001") or "S001"
>>>>>>> 55b7e13 (Removed JSON files containing secrets)
    """Returns department-level aggregates for comparison charts."""
    try:
        ws, we = get_date_range("weekly")

<<<<<<< HEAD
        departments = query("SELECT id, name FROM departments WHERE store_id = ?", (store_id,))
=======
        departments = query("SELECT id, name FROM departments WHERE store_id_text = ? OR store_id = ?", (store_id, store_id))
>>>>>>> 55b7e13 (Removed JSON files containing secrets)

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
<<<<<<< HEAD
=======


@app.get("/api/manager/available-weeks")
async def get_available_weeks(request: Request):
    store_id = getattr(request.state, "scoped_store_id", "S001") or "S001"
    """Returns distinct week/year combos from weekly_scores."""
    try:
        weeks = query(
            "SELECT DISTINCT week_number, year FROM weekly_scores ORDER BY year DESC, week_number DESC"
        )
        return weeks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/manager/segmentation")
async def get_manager_segmentation(request: Request, week: int,
    year: int,
    xMetric: str = "P_score",
    yMetric: str = "M4",
    department: Optional[str] = None):
    store_id = getattr(request.state, "scoped_store_id", "S001") or "S001"
    """Returns employee performance segmentation data (9-box + clusters)."""
    try:
        where_clause = "WHERE week_number = ? AND year = ? AND store_id = ?"
        params = [week, year, store_id]
        
        if department and department != "All":
            where_clause += " AND department = ?"
            params.append(department)
            
        sql = f"SELECT * FROM weekly_scores {where_clause}"
        scores = query(sql, tuple(params))
        
        if not scores:
            return {"employees": [], "clusterCentroids": []}
            
        # Get employee names
        emp_ids = [s["employee_id"] for s in scores]
        placeholders = ",".join(["?"] * len(emp_ids))
        names_map = {e["id"]: e["name"] for e in query(f"SELECT id, name FROM employees WHERE id IN ({placeholders})", tuple(emp_ids))}
        
        employees = []
        for s in scores:
            employees.append({
                "id": str(s["employee_id"]),
                "name": names_map.get(s["employee_id"], "Unknown"),
                "department": s["department"],
                "M1": s["M1"], "M2": s["M2"], "M3": s["M3"], "M4": s["M4"],
                "M5": s["M5"], "M7": s["M7"], "M8": s["M8"], "P": s["P_score"],
                "xValue": s.get(xMetric) if s.get(xMetric) is not None else s.get("P_score"),
                "yValue": s.get(yMetric) if s.get(yMetric) is not None else s.get("M4"),
            })
            
        # Run clustering on [M1, M2]
        clustered_employees, centroids = run_performance_clustering(employees)
        
        return {
            "employees": clustered_employees,
            "clusterCentroids": centroids
        }
    except Exception as e:
        print(f"Segmentation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== HEAD OFFICE ENDPOINTS ====================

@app.get("/api/headoffice/global-leaderboard")
async def get_global_leaderboard():
    """Ranked table of top 10 performers across all stores."""
    try:
        sql = """
            SELECT 
                e.name, 
                s.store_name, 
                e.store_id,
                s.store_location,
                e.department_id,
                'Sales' as department,
                ws.P_score, 
                ws.M1 as revenue, 
                e.level
            FROM weekly_scores ws
            JOIN employees e ON ws.employee_id = e.id
            JOIN stores s ON e.store_id = s.store_id
            ORDER BY ws.P_score DESC, ws.M1 DESC
            LIMIT 10
        """
        results = query(sql)
        for i, row in enumerate(results):
            row["rank"] = i + 1
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/headoffice/department-crossstore")
async def get_dept_crossstore():
    """Department performance comparison across all stores."""
    try:
        sql = """
            SELECT 
                s.store_id,
                s.store_name,
                ws.department,
                AVG(ws.P_score) as avg_p_score,
                AVG(ws.M2) as avg_basket,
                COUNT(ws.employee_id) as headcount
            FROM weekly_scores ws
            JOIN employees e ON ws.employee_id = e.id
            JOIN stores s ON e.store_id = s.store_id
            GROUP BY s.store_id, ws.department
        """
        return query(sql)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/headoffice/alerts")
async def get_global_alerts():
    """Aggregated geofence and flagged sale alerts across all stores."""
    try:
        geofence = query("""
            SELECT ga.*, s.store_name, e.name as employee_name
            FROM geofence_alerts ga
            JOIN employees e ON ga.employee_id = e.id
            JOIN stores s ON e.store_id = s.store_id
            WHERE ga.resolved_by_admin = 0
            ORDER BY ga.created_at DESC
        """)
        
        flagged = query("""
            SELECT s.*, st.store_name, e.name as employee_name
            FROM sales s
            JOIN employees e ON s.employee_id = e.id
            JOIN stores st ON e.store_id = st.store_id
            WHERE s.is_flagged = 1 AND s.resolved_by_admin = 0
            ORDER BY s.submitted_at DESC
        """)
        
        return {
            "geofence_alerts": geofence,
            "flagged_sales": flagged,
            "total_unresolved": len(geofence) + len(flagged)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/headoffice/store/{store_id}/overview")
async def get_ho_store_overview(request: Request, store_id: str):
    """Reuse manager store-overview logic for a specific store ID."""
    try:
        # Import store_overview locally if needed or just use it if available
        return await store_overview(request, store_id=store_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ADMIN: STORE MANAGEMENT ====================

@app.get("/api/admin/stores")
async def admin_list_stores():
    stores = query("""
        SELECT s.*, 
               (SELECT COUNT(*) FROM employees WHERE store_id = s.store_id AND is_active = 1) as employeeCount,
               (SELECT email FROM employees WHERE store_id = s.store_id AND role = 'STORE_MANAGER' LIMIT 1) as managerEmail
        FROM stores s
    """)
    
    # Add setup checklist logic
    res = []
    for s in stores:
        sid = s["store_id"]
        has_employees = s["employeeCount"] > 0
        has_manager = s["managerEmail"] is not None
        
        # Check targets for current week
        cur_week = get_current_week()
        has_targets = query("SELECT 1 FROM weekly_targets WHERE store_id = ? AND week_number = ? AND year = ?", 
                           (sid, cur_week["week"], cur_week["year"]), one=True) is not None
        
        has_geofence = s["latitude"] != 0 and s["longitude"] != 0
        
        res.append({
            **s,
            "setupChecklist": {
                "hasEmployees": has_employees,
                "hasManager": has_manager,
                "hasTargetsThisWeek": has_targets,
                "geofenceConfigured": has_geofence
            }
        })
    return {"stores": res}

@app.post("/api/admin/stores")
async def admin_create_store(data: StoreCreate):
    # Auto-generate S00{n}
    count = query("SELECT COUNT(*) as c FROM stores", one=True)["c"]
    new_id = f"S{str(count + 1).zfill(3)}"
    
    execute("""
        INSERT INTO stores (store_id, name, location, latitude, longitude, geofence_radius, is_active)
        VALUES (?, ?, ?, ?, ?, ?, 1)
    """, (new_id, data.storeName, data.storeLocation, data.storeLat, data.storeLng, data.geofenceRadius))
    
    return query("SELECT * FROM stores WHERE store_id = ?", (new_id,), one=True)

@app.patch("/api/admin/stores/{store_id}")
async def admin_update_store(store_id: str, data: StoreUpdate):
    for field, value in data.dict(exclude_unset=True).items():
        db_field = {
            "storeName": "name",
            "storeLocation": "location",
            "storeLat": "latitude",
            "storeLng": "longitude",
            "geofenceRadius": "geofence_radius",
            "isActive": "is_active"
        }.get(field, field)
        
        execute(f"UPDATE stores SET {db_field} = ? WHERE store_id = ?", (value, store_id))
    
    return query("SELECT * FROM stores WHERE store_id = ?", (store_id,), one=True)


# ==================== ADMIN: EMPLOYEE MANAGEMENT ====================

@app.get("/api/admin/employees")
async def admin_list_employees(store: Optional[str] = None, dept: Optional[str] = None, status: str = "active"):
    where = "WHERE 1=1"
    params = []
    if store:
        where += " AND e.store_id = ?"
        params.append(store)
    if dept:
        where += " AND d.name = ?"
        params.append(dept)
    if status == "active":
        where += " AND e.is_active = 1"
        
    employees = query(f"""
        SELECT e.*, d.name as department, s.name as storeName,
               (SELECT p_score FROM weekly_scores 
                WHERE employee_id = e.id 
                ORDER BY year DESC, week_number DESC LIMIT 1) as currentWeekPScore
        FROM employees e
        JOIN departments d ON e.department_id = d.id
        JOIN stores s ON e.store_id = s.store_id
        {where}
    """, tuple(params))
    
    return {"employees": employees, "total": len(employees)}

@app.post("/api/admin/employees")
async def admin_create_employee(data: EmployeeCreate):
    # 1. Generate employeeId (E{storeId}{next_n})
    count = query("SELECT COUNT(*) as c FROM employees WHERE store_id = ?", (data.storeId,), one=True)["c"]
    emp_id_str = f"E{data.storeId[1:]}{str(count + 1).zfill(3)}"
    
    # 2. Map department string to ID
    dept = query("SELECT id FROM departments WHERE name = ?", (data.department,), one=True)
    dept_id = dept["id"] if dept else 1
    
    try:
        # 3. Create Firebase user
        fb_user = auth.create_user(
            email=data.email,
            password=data.temporaryPassword,
            display_name=data.name
        )
        
        # 4. Set custom claims
        role = "EMPLOYEE" # Admin can change this later via set-user-claims
        auth.set_custom_user_claims(fb_user.uid, {
            "role": role,
            "storeId": data.storeId,
            "employeeId": emp_id_str
        })
        
        # 5. DB Insert
        new_id = execute("""
            INSERT INTO employees (name, email, firebase_uid, role, store_id, department_id, 
                                 shift_start_time, employee_id_str, is_active, total_xp, level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 0, 1)
        """, (data.name, data.email, fb_user.uid, role.lower(), data.storeId, dept_id, 
              data.shift_startTime, emp_id_str))
        
        return {
            "employeeId": emp_id_str,
            "firebaseUid": fb_user.uid,
            "id": new_id,
            "name": data.name
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.patch("/api/admin/employees/{id}")
async def admin_update_employee(id: int, data: EmployeeUpdate):
    emp = query("SELECT firebase_uid, store_id, role, employee_id_str FROM employees WHERE id = ?", (id,), one=True)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    claims_updated = False
    new_store_id = emp["store_id"]
    
    for field, value in data.dict(exclude_unset=True).items():
        if field == "department":
            dept = query("SELECT id FROM departments WHERE name = ?", (value,), one=True)
            execute("UPDATE employees SET department_id = ? WHERE id = ?", (dept["id"] if dept else 1, id))
        elif field == "storeId":
            execute("UPDATE employees SET store_id = ? WHERE id = ?", (value, id))
            new_store_id = value
            claims_updated = True
        elif field == "shiftStartTime":
            execute("UPDATE employees SET shift_start_time = ? WHERE id = ?", (value, id))
        elif field == "isActive":
            execute("UPDATE employees SET is_active = ? WHERE id = ?", (1 if value else 0, id))
        elif field == "name":
            execute("UPDATE employees SET name = ? WHERE id = ?", (value, id))
            
    if claims_updated:
        auth.set_custom_user_claims(emp["firebase_uid"], {
            "role": emp["role"].upper(),
            "storeId": new_store_id,
            "employeeId": emp["employee_id_str"]
        })
        
    return {"success": True}

@app.post("/api/admin/employees/{id}/reset-password")
async def admin_reset_password(id: int, data: PasswordReset):
    emp = query("SELECT firebase_uid FROM employees WHERE id = ?", (id,), one=True)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    auth.update_user(emp["firebase_uid"], password=data.newPassword)
    return {"success": True}


# ==================== ADMIN: WEEKLY TARGETS ====================

@app.get("/api/admin/targets")
async def admin_list_targets(store: Optional[str] = None, week: int = None, year: int = None):
    cw = week or get_current_week()["week"]
    cy = year or get_current_week()["year"]
    
    where = "WHERE 1=1"
    params = [cw, cy]
    if store:
        where += " AND e.store_id = ?"
        params.append(store)
        
    targets = query(f"""
        SELECT t.*, e.name as employeeName, d.name as department, s.name as storeName,
               (SELECT target_amount FROM weekly_targets 
                WHERE employee_id = e.id AND (year < ? OR (year = ? AND week_number < ?))
                ORDER BY year DESC, week_number DESC LIMIT 1) as lastWeekTarget,
               (SELECT revenue FROM weekly_scores 
                WHERE employee_id = e.id AND (year < ? OR (year = ? AND week_number < ?))
                ORDER BY year DESC, week_number DESC LIMIT 1) as lastWeekRevenue,
               (SELECT p_score FROM weekly_scores 
                WHERE employee_id = e.id AND (year < ? OR (year = ? AND week_number < ?))
                ORDER BY year DESC, week_number DESC LIMIT 1) as lastWeekPScore
        FROM employees e
        LEFT JOIN weekly_targets t ON e.id = t.employee_id AND t.week_number = ? AND t.year = ?
        JOIN departments d ON e.department_id = d.id
        JOIN stores s ON e.store_id = s.store_id
        {where} AND e.is_active = 1
    """, (cy, cy, cw, cy, cy, cw, cy, cy, cw, cw, cy, *params))
    
    # Filter unset
    unset = [t for t in targets if t["target_amount"] is None]
    
    return {
        "weekNumber": cw,
        "year": cy,
        "targets": [t for t in targets if t["target_amount"] is not None],
        "unsetEmployees": unset
    }

@app.post("/api/admin/targets/bulk")
async def admin_bulk_set_targets(data: TargetBulkSet):
    count = 0
    now = datetime.now().isoformat()
    for t in data.targets:
        # Get store_id for employee
        emp = query("SELECT store_id FROM employees WHERE id = ?", (t.employeeId,), one=True)
        if not emp: continue
        
        execute("""
            INSERT OR REPLACE INTO weekly_targets 
            (target_id, employee_id, store_id, week_number, year, target_amount, set_by, set_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), t.employeeId, emp["store_id"], data.weekNumber, data.year, t.targetAmount, data.setBy, now))
        count += 1
    return {"count": count}

@app.post("/api/admin/targets/copy-last-week")
async def admin_copy_targets(storeId: Optional[str] = None):
    cw = get_current_week()["week"]
    cy = get_current_week()["year"]
    
    # Simple logic: find previous week targets
    prev_w = cw - 1 if cw > 1 else 52
    prev_y = cy if cw > 1 else cy - 1
    
    where = "WHERE week_number = ? AND year = ?"
    params = [prev_w, prev_y]
    if storeId:
        where += " AND store_id = ?"
        params.append(storeId)
        
    prev_targets = query(f"SELECT employee_id, store_id, target_amount FROM weekly_targets {where}", tuple(params))
    
    count = 0
    now = datetime.now().isoformat()
    for t in prev_targets:
        # Skip if already exists
        exists = query("SELECT 1 FROM weekly_targets WHERE employee_id = ? AND week_number = ? AND year = ?", 
                      (t["employee_id"], cw, cy), one=True)
        if exists: continue
        
        execute("""
            INSERT INTO weekly_targets (target_id, employee_id, store_id, week_number, year, target_amount, set_by, set_at)
            VALUES (?, ?, ?, ?, ?, ?, 'SYSTEM_COPY', ?)
        """, (str(uuid.uuid4()), t["employee_id"], t["store_id"], cw, cy, t["target_amount"], now))
        count += 1
        
    return {"count": count}

@app.get("/api/admin/targets/fairness-check")
async def admin_targets_fairness(week: int, year: int):
    targets = query("""
        SELECT t.*, e.name, d.name as department, e.store_id
        FROM weekly_targets t
        JOIN employees e ON t.employee_id = e.id
        JOIN departments d ON e.department_id = d.id
        WHERE t.week_number = ? AND t.year = ?
    """, (week, year))
    
    # Calculate dept averages
    depts = {}
    for t in targets:
        key = (t["department"], t["store_id"])
        if key not in depts: depts[key] = []
        depts[key].append(t["target_amount"])
        
    dept_avgs = []
    for (d, s), vals in depts.items():
        dept_avgs.append({"department": d, "storeId": s, "avgTarget": sum(vals)/len(vals)})
        
    warnings = []
    for t in targets:
        avg = next(a["avgTarget"] for a in dept_avgs if a["department"] == t["department"] and a["storeId"] == t["store_id"])
        ratio = t["target_amount"] / avg if avg > 0 else 1
        if ratio > 2.0:
            warnings.append({**t, "deptAvgTarget": avg, "ratio": ratio, "warning": f"Target is {ratio:.1f}x dept average"})
        elif ratio < 0.5:
            warnings.append({**t, "deptAvgTarget": avg, "ratio": ratio, "warning": f"Target is only {ratio:.1f}x dept average"})
            
    return {"warnings": warnings, "deptAverages": dept_avgs}


# ==================== ADMIN: SYSTEM CONFIG ====================

@app.get("/api/admin/config")
async def admin_get_config():
    from config_service import get_config
    # Invalidate cache first to get fresh for admin
    from config_service import invalidate_cache
    invalidate_cache()
    
    configs = query("SELECT * FROM system_config")
    res = []
    for c in configs:
        val = c["config_value"]
        if c["config_type"] == "JSON": val = json.loads(val)
        elif c["config_type"] == "NUMBER": val = float(val)
        elif c["config_type"] == "BOOLEAN": val = val.lower() == "true"
        
        res.append({
            "key": c["config_key"],
            "value": val,
            "type": c["config_type"],
            "description": c["description"],
            "lastUpdatedBy": c["last_updated_by"],
            "lastUpdatedAt": c["last_updated_at"]
        })
    return {"config": res}

@app.patch("/api/admin/config/{key}")
async def admin_update_config(key: str, data: ConfigUpdate):
    # Validation for METRIC_WEIGHTS
    if key == "METRIC_WEIGHTS":
        weights = json.loads(data.value)
        total = sum(weights.values())
        if abs(total - 1.0) > 0.001:
            raise HTTPException(status_code=400, detail=f"Weights must sum to 1.00. Current sum: {total:.3f}")
            
    from config_service import update_config_db
    update_config_db(key, data.value, data.reason, data.reason, data.effectiveFromWeek, data.effectiveFromYear)
    
    return {"success": True}

@app.get("/api/admin/config/history/{key}")
async def admin_config_history(key: str):
    history = query("SELECT * FROM system_config_history WHERE config_key = ? ORDER BY changed_at DESC", (key,))
    return {"key": key, "history": history}


# ==================== ADMIN: RAW DATA & EXPORTS ====================

@app.get("/api/admin/data/sales")
async def admin_data_sales(
    store: Optional[str] = None,
    employee: Optional[int] = None,
    start_date: str = Query(None, alias="from"),
    end_date: str = Query(None, alias="to"),
    flagged: str = "all",
    page: int = 1,
    limit: int = 50
):
    where = "WHERE 1=1"
    params = []
    if store:
        where += " AND e.store_id = ?"
        params.append(store)
    if employee:
        where += " AND s.employee_id = ?"
        params.append(employee)
    if start_date and end_date:
        where += " AND s.sale_date BETWEEN ? AND ?"
        params.extend([start_date, end_date])
    if flagged == "true":
        where += " AND s.is_flagged = 1"
    elif flagged == "false":
        where += " AND s.is_flagged = 0"
        
    offset = (page - 1) * limit
    sales = query(f"""
        SELECT s.*, e.name as employeeName, st.name as storeName, d.name as department
        FROM sales s
        JOIN employees e ON s.employee_id = e.id
        JOIN stores st ON e.store_id = st.store_id
        JOIN departments d ON e.department_id = d.id
        {where} ORDER BY s.submitted_at DESC LIMIT ? OFFSET ?
    """, (*params, limit, offset))
    
    total = query(f"SELECT COUNT(*) as c FROM sales s JOIN employees e ON s.employee_id = e.id {where}", tuple(params))["c"]
    
    return {
        "sales": sales,
        "total": total,
        "page": page,
        "totalPages": (total + limit - 1) // limit
    }

@app.get("/api/admin/data/weekly-scores")
async def admin_data_scores(store: Optional[str] = None, week: int = None, year: int = None):
    where = "WHERE 1=1"
    params = []
    if store:
        where += " AND e.store_id = ?"
        params.append(store)
    if week and year:
        where += " AND ws.week_number = ? AND ws.year = ?"
        params.extend([week, year])
        
    scores = query(f"""
        SELECT ws.*, e.name as employeeName, st.name as storeName, d.name as department
        FROM weekly_scores ws
        JOIN employees e ON ws.employee_id = e.id
        JOIN stores st ON e.store_id = st.store_id
        JOIN departments d ON e.department_id = d.id
        {where} ORDER BY ws.year DESC, ws.week_number DESC, ws.p_score DESC
    """, tuple(params))
    return {"scores": scores}

@app.get("/api/admin/data/attendance")
async def admin_data_attendance(store: Optional[str] = None, start_date: str = Query(None, alias="from"), end_date: str = Query(None, alias="to")):
    where = "WHERE 1=1"
    params = []
    if store:
        where += " AND e.store_id = ?"
        params.append(store)
    if start_date and end_date:
        where += " AND a.attendance_date BETWEEN ? AND ?"
        params.extend([start_date, end_date])
        
    records = query(f"""
        SELECT a.*, e.name as employeeName, st.name as storeName
        FROM attendance a
        JOIN employees e ON a.employee_id = e.id
        JOIN stores st ON e.store_id = st.store_id
        {where} ORDER BY a.attendance_date DESC
    """, tuple(params))
    return {"records": records}


# --- CSV Stream Generation ---
def generate_csv(df):
    from io import StringIO
    output = StringIO()
    df.to_csv(output, index=False)
    return output.getvalue()

@app.get("/api/admin/export/sales")
async def admin_export_sales(store: Optional[str] = None, from_date: str = Query(None, alias="from"), to_date: str = Query(None, alias="to")):
    import pandas as pd
    data = (await admin_data_sales(store=store, start_date=from_date, end_date=to_date, limit=10000))["sales"]
    df = pd.DataFrame(data)
    if not df.empty:
        # Cleanup for CSV
        df = df[["id", "employee_id", "employeeName", "storeName", "department", "revenue", "num_items", "basketSize", "is_flagged", "flags", "admin_action", "sale_date"]]
    
    csv_content = generate_csv(df)
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=performiq_sales_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

@app.get("/api/admin/export/weekly-scores")
async def admin_export_scores(store: Optional[str] = None, week: int = None, year: int = None):
    import pandas as pd
    data = (await admin_data_scores(store=store, week=week, year=year))["scores"]
    df = pd.DataFrame(data)
    if not df.empty:
        df = df[["employee_id", "employeeName", "storeName", "department", "week_number", "year", "p_score", "revenue", "avg_basket_size", "total_bills", "xp_earned"]]
    
    csv_content = generate_csv(df)
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=performiq_scores_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

@app.get("/api/admin/data/health-check")
async def admin_health_check():
    warnings = []
    cw = get_current_week()
    stores = query("SELECT store_id, name FROM stores WHERE is_active = 1")
    
    for s in stores:
        sid = s["store_id"]
        
        # 1. Missing targets
        missing_targets = query("""
            SELECT COUNT(*) as c FROM employees e 
            WHERE e.store_id = ? AND e.role = 'employee' AND e.is_active = 1
            AND NOT EXISTS (SELECT 1 FROM weekly_targets t WHERE t.employee_id = e.id AND t.week_number = ? AND t.year = ?)
        """, (sid, cw["week"], cw["year"]), one=True)["c"]
        if missing_targets > 0:
            warnings.append({
                "type": "MISSING_TARGETS", "storeId": sid, "storeName": s["name"],
                "detail": f"{missing_targets} employees have no targets set", "affectedCount": missing_targets, "weekNumber": cw["week"]
            })
            
        # 2. Missing ratings today
        today = datetime.now().strftime("%Y-%m-%d")
        missing_ratings = query("""
            SELECT COUNT(*) as c FROM employees e 
            WHERE e.store_id = ? AND e.role = 'employee' AND e.is_active = 1
            AND NOT EXISTS (SELECT 1 FROM manager_ratings r WHERE r.employee_id = e.id AND r.rating_date = ?)
        """, (sid, today), one=True)["c"]
        if missing_ratings > 0:
            warnings.append({
                "type": "MISSING_RATINGS", "storeId": sid, "storeName": s["name"],
                "detail": f"{missing_ratings} employees not rated today", "affectedCount": missing_ratings, "weekNumber": cw["week"]
            })
            
    return {
        "warnings": warnings,
        "totalWarnings": len(warnings),
        "lastAggregationRan": query("SELECT MAX(aggregated_at) as m FROM store_weekly_summary", one=True)["m"]
    }


# ==================== ADMIN: RATING MANAGEMENT ====================

@app.get("/api/admin/ratings/status")
async def admin_ratings_status(date: str = None):
    check_date = date or datetime.now().strftime("%Y-%m-%d")
    stores = query("SELECT store_id, name FROM stores WHERE is_active = 1")
    
    store_statuses = []
    for s in stores:
        sid = s["store_id"]
        employees = query("SELECT id, name, department_id FROM employees WHERE store_id = ? AND role = 'employee' AND is_active = 1", (sid,))
        total = len(employees)
        
        rated = query("""
            SELECT r.employee_id, e.name, d.name as department, r.rating 
            FROM manager_ratings r 
            JOIN employees e ON r.employee_id = e.id
            JOIN departments d ON e.department_id = d.id
            WHERE e.store_id = ? AND r.rating_date = ?
        """, (sid, check_date))
        
        rated_ids = [r["employee_id"] for r in rated]
        unrated = [e for e in employees if e["id"] not in rated_ids]
        
        # Variance warning
        import numpy as np
        variant_warning = False
        if len(rated) > 2:
            std = np.std([r["rating"] for r in rated])
            if std < 0.3: variant_warning = True
            
        store_statuses.append({
            "storeId": sid, "storeName": s["name"],
            "totalEmployees": total, "ratedToday": len(rated),
            "unratedEmployees": unrated,
            "completionPercent": (len(rated)/total * 100) if total > 0 else 0,
            "varianceWarning": variant_warning
        })
        
    return {"date": check_date, "stores": store_statuses}

@app.post("/api/admin/ratings/bulk")
async def admin_bulk_rate(data: RatingBulkSet):
    count = 0
    for r in data.ratings:
        execute("""
            INSERT OR REPLACE INTO manager_ratings (employee_id, rating, rating_date, rated_by, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (r.employeeId, r.rating, data.date, data.ratedBy))
        count += 1
    return {"count": count}

# ==================== AUTHENTICATION & CLAIMS ====================

@app.post("/api/admin/set-user-claims")
async def set_user_claims(request: Request):
    """Administrative endpoint to assign roles and store scoping to Firebase users."""
    try:
        data = await request.json()
        uid = data.get("uid")
        role = data.get("role") # HEAD_OFFICE, STORE_MANAGER, EMPLOYEE
        store_id = data.get("storeId")
        employee_id = data.get("employeeId")
        
        if not uid or not role:
            raise HTTPException(status_code=400, detail="UID and Role are required")
            
        # Set custom claims in Firebase
        claims = {
            "role": role,
            "storeId": store_id,
            "employeeId": employee_id
        }
        auth.set_custom_user_claims(uid, claims)
        
        return {"success": True, "uid": uid, "claims": claims}
    except Exception as e:
        print(f"Error setting claims: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== EMPLOYEE TRAJECTORY ====================
@app.get("/api/manager/employee-trajectories")
async def get_employee_trajectories(request: Request, store_id: Optional[str] = None, weeks: int = 8):
    # If store_id not provided, use scoped_store_id from middleware
    sid = store_id or getattr(request.state, "scoped_store_id", "S001")
    
    # Calculate this from the sales table directly for precision
    cw, cy = get_current_week()
    
    # Fetch sales for the last N weeks
    start_date = (datetime.now() - timedelta(weeks=weeks)).strftime("%Y-%m-%d")
    
    sales_data = query("""
        SELECT 
            e.id, e.name, d.name as department, 
            s.revenue, s.sale_date
        FROM sales s
        JOIN employees e ON s.employee_id = e.id
        JOIN departments d ON e.department_id = d.id
        WHERE e.store_id = ? AND s.sale_date >= ? AND s.status = 'approved'
    """, (sid, start_date))
    
    trajectories = {}
    for row in sales_data:
        eid = row['id']
        if eid not in trajectories:
            trajectories[eid] = {
                "name": row['name'],
                "department": row['department'],
                "weeklyData": {}
            }
        
        # Get week number from date
        dt = datetime.strptime(row['sale_date'], "%Y-%m-%d")
        w_key = f"W{dt.isocalendar()[1]} {dt.year}"
        
        if w_key not in trajectories[eid]["weeklyData"]:
            trajectories[eid]["weeklyData"][w_key] = 0
        trajectories[eid]["weeklyData"][w_key] += row['revenue']
        
    # Format for frontend
    result = []
    all_weeks = []
    for i in range(weeks):
        d = datetime.now() - timedelta(weeks=i)
        all_weeks.append(f"W{d.isocalendar()[1]} {d.year}")
    all_weeks.reverse()
    
    for eid, data in trajectories.items():
        points = []
        for w in all_weeks:
            points.append({
                "week": w,
                "revenue": data["weeklyData"].get(w, 0)
            })
        result.append({
            "employeeId": eid,
            "name": data["name"],
            "department": data["department"],
            "data": points
        })
        
    return result

# ==================== DATA WAREHOUSE API ====================

@app.get("/api/warehouse/store-summary")
async def wh_store_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Store summary from wh_store_summary, filterable by date range."""
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    rows = query(
        """SELECT ws.*, s.store_name
           FROM wh_store_summary ws
           JOIN stores s ON ws.store_id = s.store_id
           WHERE ws.date BETWEEN ? AND ?
           ORDER BY ws.date DESC, ws.store_id""",
        (start_date, end_date),
    )
    return {"startDate": start_date, "endDate": end_date, "rows": rows}


@app.get("/api/warehouse/employee-facts")
async def wh_employee_facts(
    store_id: Optional[str] = None,
    department: Optional[str] = None,
    date: Optional[str] = None,
):
    """Employee fact table, searchable by store and department."""
    target = date or (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    where = "WHERE wf.date = ?"
    params: list = [target]

    if store_id:
        where += " AND wf.store_id = ?"
        params.append(store_id)
    if department:
        where += " AND wf.department = ?"
        params.append(department)

    rows = query(
        f"""SELECT wf.*, e.name as employee_name, s.store_name
            FROM wh_employee_fact wf
            JOIN employees e ON wf.employee_id = e.id
            JOIN stores s ON wf.store_id = s.store_id
            {where}
            ORDER BY wf.p_score DESC""",
        tuple(params),
    )
    return {"date": target, "rows": rows}


@app.get("/api/warehouse/dept-benchmarks")
async def wh_dept_benchmarks(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Department benchmarks with cross-store ranking."""
    if not start_date:
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    rows = query(
        """SELECT db.*, s.store_name
           FROM wh_dept_benchmark db
           JOIN stores s ON db.store_id = s.store_id
           WHERE db.date BETWEEN ? AND ?
           ORDER BY db.department, db.dept_rank""",
        (start_date, end_date),
    )
    return {"startDate": start_date, "endDate": end_date, "rows": rows}


@app.get("/api/warehouse/flag-summary")
async def wh_flag_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Flag type breakdown per store."""
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    rows = query(
        """SELECT fl.*, s.store_name
           FROM wh_flag_log fl
           JOIN stores s ON fl.store_id = s.store_id
           WHERE fl.date BETWEEN ? AND ?
           ORDER BY fl.date DESC, fl.store_id""",
        (start_date, end_date),
    )
    return {"startDate": start_date, "endDate": end_date, "rows": rows}


@app.get("/api/warehouse/etl-runs")
async def wh_etl_runs(limit: int = 20):
    """Last N ETL runs with status."""
    rows = query(
        "SELECT * FROM etl_runs ORDER BY run_at DESC LIMIT ?",
        (limit,),
    )
    return {"runs": rows}


@app.post("/api/warehouse/run-etl")
async def wh_trigger_etl(request: Request):
    """Manually trigger ETL pipeline."""
    try:
        data = await request.json()
    except Exception:
        data = {}

    target_date = data.get("date", None)
    try:
        run_etl(target_date)
        return {"success": True, "message": "ETL completed", "ranAt": datetime.now().isoformat()}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== WAREHOUSE & AGGREGATION ====================

@app.post("/api/admin/run-aggregation")
async def trigger_aggregation(request: Request):
    """Manual trigger for data warehouse aggregation."""
    try:
        data = await request.json()
    except:
        data = {}
    
    cw, cy = get_current_week()
    week = data.get("weekNumber", cw)
    year = data.get("year", cy)
    
    # Run in thread if it takes too long, but for now just await
    run_weekly_aggregation(week, year)
    
    return {
        "success": True,
        "weekNumber": week,
        "year": year,
        "ranAt": datetime.now().isoformat()
    }

@app.get("/api/headoffice/warehouse/overview")
async def get_warehouse_overview(week: int = None, year: int = None):
    cw, cy = get_current_week()
    w = week or cw
    y = year or cy
    
    sql = """
        SELECT 
            sws.*, 
            cwc.store_rank, cwc.revenue_rank, cwc.attendance_rank,
            s.store_name, s.store_location
        FROM store_weekly_summary sws
        JOIN cross_store_weekly_comparison cwc ON sws.store_id = cwc.store_id 
            AND sws.week_number = cwc.week_number AND sws.year = cwc.year
        JOIN stores s ON sws.store_id = s.store_id
        WHERE sws.week_number = ? AND sws.year = ?
    """
    results = query(sql, (w, y))
    return {
        "weekNumber": w,
        "year": y,
        "stores": results
    }

@app.get("/api/headoffice/warehouse/trends")
async def get_warehouse_trends(weeks: int = 8):
    weeks = min(max(weeks, 1), 12)
    cw, cy = get_current_week()
    
    # Get last N weeks
    trend_data = query("""
        SELECT 
            sws.store_id, s.store_name, sws.week_number, sws.year,
            sws.avg_p_score, sws.total_revenue, sws.avg_attendance_rate,
            cwc.store_rank
        FROM store_weekly_summary sws
        JOIN stores s ON sws.store_id = s.store_id
        JOIN cross_store_weekly_comparison cwc ON sws.store_id = cwc.store_id 
            AND sws.week_number = cwc.week_number AND sws.year = cwc.year
        ORDER BY sws.year DESC, sws.week_number DESC
        LIMIT ?
    """, (weeks * 3,)) # 3 stores
    
    stores_map = {}
    for row in trend_data:
        sid = row['store_id']
        if sid not in stores_map:
            stores_map[sid] = {"storeId": sid, "storeName": row['store_name'], "trend": []}
        
        stores_map[sid]["trend"].append({
            "week": f"W{row['week_number']} {row['year']}",
            "weekNumber": row['week_number'],
            "year": row['year'],
            "avgPScore": row['avg_p_score'],
            "totalRevenue": row['total_revenue'],
            "avgAttendance": row['avg_attendance_rate'],
            "storeRank": row['store_rank']
        })
        
    # Reverse trends for chronological display
    for sid in stores_map:
        stores_map[sid]["trend"].reverse()
        
    return {
        "weeks": sorted(list(set(f"W{r['week_number']} {r['year']}" for r in trend_data))),
        "stores": list(stores_map.values())
    }

@app.get("/api/headoffice/warehouse/departments")
async def get_warehouse_departments(week: int = None, year: int = None):
    cw, cy = get_current_week()
    w = week or cw
    y = year or cy
    
    stats = query("""
        SELECT dws.*, s.store_name
        FROM department_weekly_summary dws
        JOIN stores s ON dws.store_id = s.store_id
        WHERE dws.week_number = ? AND dws.year = ?
    """, (w, y))
    
    stores_data = {}
    for row in stats:
        sid = row['store_id']
        if sid not in stores_data:
            stores_data[sid] = {"storeId": sid, "storeName": row['store_name'], "departments": []}
        
        stores_data[sid]["departments"].append({
            "department": row['department'],
            "avgPScore": row['dept_avg_p_score'],
            "avgRevenue": row['dept_avg_revenue'],
            "avgBasketSize": row['dept_avg_basket_size'],
            "avgAttendance": row['dept_avg_attendance'],
            "headcount": row['headcount'],
            "employees_above_target": row['employees_above_target']
        })
        
    return {
        "weekNumber": w,
        "year": y,
        "departments": ["Women's Wear", "Men's Wear", "Accessories"],
        "stores": list(stores_data.values())
    }

@app.get("/api/headoffice/warehouse/store-ranking-history")
async def get_ranking_history(weeks: int = 8):
    cw, cy = get_current_week()
    history = query("""
        SELECT 
            cwc.week_number, cwc.year, cwc.store_id, s.store_name, 
            cwc.store_rank, cwc.avg_p_score, cwc.total_revenue
        FROM cross_store_weekly_comparison cwc
        JOIN stores s ON cwc.store_id = s.store_id
        ORDER BY cwc.year DESC, cwc.week_number DESC
        LIMIT ?
    """, (weeks * 3,))
    
    stores_map = {}
    for row in history:
        sid = row['store_id']
        if sid not in stores_map:
            stores_map[sid] = {"storeId": sid, "storeName": row['store_name'], "rankHistory": []}
        
        stores_map[sid]["rankHistory"].append({
            "week": f"W{row['week_number']}",
            "rank": row['store_rank'],
            "avgPScore": row['avg_p_score'],
            "totalRevenue": row['total_revenue']
        })
        
    for sid in stores_map:
        stores_map[sid]["rankHistory"].reverse()
        
    return {
        "weeks": sorted(list(set(f"W{r['week_number']}" for r in history))),
        "stores": list(stores_map.values())
    }

@app.get("/api/headoffice/warehouse/global-leaderboard")
async def get_warehouse_global_leaderboard(week: int = None, year: int = None, limit: int = 10):
    cw, cy = get_current_week()
    w = week or cw
    y = year or cy
    
    sql = """
        SELECT 
            e.id as employeeId, e.name, ws.department, 
            e.store_id as storeId, s.store_name as storeName,
            ws.P_score as pScore, ws.M1 as weeklyRevenue, -- M1 is the score but here requested as revenue placeholder if needed
            e.level, e.level_title as levelLabel, e.total_xp as xp
        FROM weekly_scores ws
        JOIN employees e ON ws.employee_id = e.id
        JOIN stores s ON e.store_id = s.store_id
        WHERE ws.week_number = ? AND ws.year = ?
        ORDER BY ws.P_score DESC
        LIMIT ?
    """
    results = query(sql, (w, y, limit))
    for i, res in enumerate(results):
        res["rank"] = i + 1
        
    return {
        "weekNumber": w,
        "leaderboard": results
    }

# ==================== SCHEDULER ====================

async def run_scheduler():
    """Runs at startup and periodically checks for Sunday 11:59 PM IST."""
    print("Initializing aggregation scheduler...")
    
    # Run once immediately for current week
    cw, cy = get_current_week()
    try:
        run_weekly_aggregation(cw, cy)
        # Backfill last 8 weeks if empty
        for i in range(1, 9):
            bw = cw - i
            by = cy
            if bw <= 0:
                bw += 52
                by -= 1
            
            exists = query("SELECT 1 FROM store_weekly_summary WHERE week_number = ? AND year = ? LIMIT 1", (bw, by))
            if not exists:
                print(f"Backfilling aggregation for W{bw} {by}...")
                run_weekly_aggregation(bw, by)
    except Exception as e:
        print(f"Startup aggregation error: {e}")

    while True:
        # Calculate time until next Sunday 23:59:00 IST (UTC+5:30)
        # simplistic check every hour
        await asyncio.sleep(3600)
        now = datetime.now() # assume server time matches desired TZ or convert
        if now.weekday() == 6 and now.hour == 23 and now.minute >= 50:
            print("Scheduled aggregation triggered...")
            cw, cy = get_current_week()
            run_weekly_aggregation(cw, cy)
            await asyncio.sleep(600) # prevent double trigger

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_scheduler())
>>>>>>> 55b7e13 (Removed JSON files containing secrets)
