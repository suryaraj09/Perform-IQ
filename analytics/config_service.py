import sqlite3
import json
import time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "performiq.db"

# Cache structure: { key: { "value": parsed_value, "expiry": timestamp } }
_config_cache = {}
CACHE_TTL = 60 # seconds

def get_config(key: str):
    """Retrieve and parse setting from system_config with 60s caching."""
    global _config_cache
    
    now = time.time()
    if key in _config_cache and _config_cache[key]["expiry"] > now:
        return _config_cache[key]["value"]
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT config_value, config_type FROM system_config WHERE config_key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print(f"ERROR: Config storage missing key: {key}")
        # Default fallbacks to prevent crash if migration failed partially
        if key == 'METRIC_WEIGHTS':
            return {"M1":0.30,"M2":0.25,"M3":0.15,"M4":0.10,"M5":0.10,"M7":0.05,"M8":0.05}
        return None
        
    val_str, val_type = row
    parsed_val = val_str
    
    try:
        if val_type == 'JSON':
            parsed_val = json.loads(val_str)
        elif val_type == 'NUMBER':
            parsed_val = float(val_str)
        elif val_type == 'BOOLEAN':
            parsed_val = val_str.lower() == 'true'
    except Exception as e:
        print(f"Error parsing config {key}: {e}")
        
    _config_cache[key] = {
        "value": parsed_val,
        "expiry": now + CACHE_TTL
    }
    
    return parsed_val

def invalidate_cache(key: str = None):
    """Clear specific key or entire cache."""
    global _config_cache
    if key:
        _config_cache.pop(key, None)
    else:
        _config_cache.clear()

def update_config_db(key: str, value, updated_by: str, reason: str = None, week: int = None, year: int = None):
    """Update config in DB and log to history."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Get current value for history
    cursor.execute("SELECT config_value FROM system_config WHERE config_key = ?", (key,))
    current = cursor.fetchone()
    old_val = current[0] if current else ""
    
    new_val_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
    
    # 2. Log to history
    import uuid
    cursor.execute("""
        INSERT INTO system_config_history 
        (history_id, config_key, old_value, new_value, changed_by, changed_at, effective_from_week, effective_from_year, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(uuid.uuid4()), key, old_val, new_val_str, updated_by, 
        time.strftime('%Y-%m-%dT%H:%M:%S'), week, year, reason
    ))
    
    # 3. Update main table
    cursor.execute("""
        UPDATE system_config 
        SET config_value = ?, last_updated_by = ?, last_updated_at = ?, effective_from_week = ?, effective_from_year = ?
        WHERE config_key = ?
    """, (new_val_str, updated_by, time.strftime('%Y-%m-%dT%H:%M:%S'), week, year, key))
    
    conn.commit()
    conn.close()
    
    # 4. Invalidate cache
    invalidate_cache(key)
