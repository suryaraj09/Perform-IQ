import re
from pathlib import Path

def patch_file(filename, replacements):
    with open(filename, 'r') as f:
        content = f.read()
    
    for old, new in replacements:
        content = content.replace(old, new)
        
    with open(filename, 'w') as f:
        f.write(content)
    print(f"Patched {filename}")

def patch_main_regex():
    with open('main.py', 'r') as f:
        content = f.read()

    # Generic search and replace for joins
    content = content.replace("JOIN stores s ON e.store_id = s.id", "JOIN stores s ON e.store_id = s.store_id")
    content = content.replace("FROM stores WHERE id = ?", "FROM stores WHERE store_id = ?")
    content = content.replace("s.latitude, s.longitude, s.geofence_radius_meters", "s.store_lat, s.store_lng, s.geofence_radius")
    
    # Update manager routes to use scopedStoreId
    # Example: async def store_overview(store_id: str = "S001"):
    # Target: async def store_overview(request: Request): ... store_id = request.state.scoped_store_id or "S001"
    
    routes_to_fix = [
        "store_overview", "department_summary", "attendance_overview", 
        "pending_employees", "get_manager_segmentation", "get_available_weeks"
    ]
    
    for route in routes_to_fix:
        # Search for: async def route(..., store_id: str = "S001", ...)
        # Replace signature to include request: Request
        # Inject store_id assignment
        pattern = rf'async def {route}\(([^)]*)\):'
        
        def replacer(match):
            args = match.group(1).strip()
            # If request: Request not in args, insert it
            new_args = args
            if 'request: Request' not in args:
                new_args = 'request: Request, ' + args if args else 'request: Request'
            
            # Remove the default store_id from signature if present
            new_args = re.sub(r'store_id:\s*str\s*=\s*"[^"]*"', '', new_args)
            new_args = re.sub(r',\s*,', ',', new_args).strip(', ')
            
            replacement = f'async def {route}({new_args}):\n    store_id = getattr(request.state, "scoped_store_id", "S001") or "S001"'
            return replacement
            
        content = re.sub(pattern, replacer, content)

    with open('main.py', 'w') as f:
        f.write(content)
    print("Patched main.py with scoping and schema alignment.")

def main():
    attendance_reps = [
        ("JOIN stores s ON e.store_id = s.id", "JOIN stores s ON e.store_id = s.store_id"),
        ("s.latitude, s.longitude, s.geofence_radius_meters, s.shift_start_time", "s.store_lat, s.store_lng, s.geofence_radius, s.shift_start_time"),
        ("SELECT s.latitude, s.longitude, s.geofence_radius_meters", "SELECT s.store_lat, s.store_lng, s.geofence_radius"),
    ]
    patch_file('attendance.py', attendance_reps)
    patch_main_regex()

if __name__ == "__main__":
    main()
