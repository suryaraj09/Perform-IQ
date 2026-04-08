import re
import sys

def modify_main():
    with open('main.py', 'r') as f:
        content = f.read()

    # 1. Add imports to main.py
    imports = """from fastapi import Request
from fastapi.responses import JSONResponse
from firebase_admin import auth
import firebase_admin_setup
firebase_admin_setup.init_firebase()
"""
    if "import firebase_admin_setup" not in content:
        content = content.replace("from database import init_db", imports + "\nfrom database import init_db")

    # 2. Add middleware
    middleware = """
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
"""
    if "require_firebase_auth" not in content:
        content = content.replace('app = FastAPI(title="PerformIQ API", version="1.0.0")', 
                                  'app = FastAPI(title="PerformIQ API", version="1.0.0")\n' + middleware)

    # 3. Add POST /api/admin/set-user-claims
    set_claims_route = """
class ClaimData(BaseModel):
    uid: str
    role: str
    storeId: str | None = None
    employeeId: str | None = None

@app.post("/api/admin/set-user-claims")
async def set_user_claims(data: ClaimData):
    auth.set_custom_user_claims(data.uid, {
        "role": data.role,
        "storeId": data.storeId,
        "employeeId": data.employeeId
    })
    return {"success": True}
    
@app.get("/api/store/config")
async def get_store_config(request: Request):
    user = request.state.user
    s_id = user.get("storeId") or 'S001'
    store = query("SELECT id, store_id, store_name, store_lat, store_lng, geofence_radius FROM stores WHERE store_id = ?", (s_id,), one=True)
    if not store:
        return {"storeId": "S001", "storeName": "Default", "storeLat": 0.0, "storeLng": 0.0, "geofenceRadius": 100}
    return {
        "storeId": store["store_id"],
        "storeName": store["store_name"],
        "storeLat": store["store_lat"],
        "storeLng": store["store_lng"],
        "geofenceRadius": store["geofence_radius"]
    }
"""
    if "/api/admin/set-user-claims" not in content:
        # insert before upload
        content = content.replace('@app.post("/api/upload")', set_claims_route + '\n@app.post("/api/upload")')

    # Replace hardcoded store_id: int = 1 with request.state.scoped_store_id or "S001"
    # We will just change `store_id: int = 1` to `store_id: str = 'S001'` globally for schema compatibility,
    # and if we need the scoped store, we use it natively.
    # Actually wait, `store_id: int = 1` -> `store_id: str = "S001"`
    content = re.sub(r'store_id:\s*int\s*=\s*1', 'store_id: str = "S001"', content)

    with open('main.py', 'w') as f:
        f.write(content)
        
    print("Updated main.py")

if __name__ == '__main__':
    modify_main()
