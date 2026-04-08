from fastapi import Depends, HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth
from typing import Optional, List, Dict, Any

security = HTTPBearer()

async def verify_firebase_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """Verify Firebase ID token and return decoded user info."""
    token = credentials.credentials
    try:
        decoded = auth.verify_id_token(token)
        return {
            "uid": decoded.get("uid"),
            "role": decoded.get("role"),
            "storeId": decoded.get("storeId"),
            "employeeId": decoded.get("employeeId"),
            "email": decoded.get("email"),
            "name": decoded.get("name") or decoded.get("email")
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_role(allowed_roles: List[str]):
    """Returns a dependency that asserts the user role is authorized."""
    async def role_checker(user: dict = Depends(verify_firebase_token)):
        if not user.get("role"):
            raise HTTPException(status_code=403, detail="No role assigned. Contact admin.")
        
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden — insufficient role")
        
        return user
    return role_checker


async def require_store_scope(request: Request, user: dict = Depends(verify_firebase_token)):
    """Computes the scopedStoreId based on the user's role."""
    role = user.get("role")
    
    if role == 'STORE_MANAGER':
        request.state.scoped_store_id = user.get("storeId")
    elif role == 'HEAD_OFFICE':
        request.state.scoped_store_id = request.query_params.get("storeId")
    elif role == 'EMPLOYEE':
        request.state.scoped_store_id = user.get("storeId")
    else:
        request.state.scoped_store_id = None
        
    return user

# Helper dependency to easily get the scoped_store_id in route handlers
async def get_scoped_store_id(request: Request, _: dict = Depends(require_store_scope)) -> Optional[str]:
    return getattr(request.state, "scoped_store_id", None)
