import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "performiq.db"

def refine():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS users")
    
    # Check current stores columns
    c.execute("PRAGMA table_info(stores)")
    cols = [col[1] for col in c.fetchall()]
    
    if 'shift_start_time' not in cols:
        c.execute("ALTER TABLE stores ADD COLUMN shift_start_time TEXT DEFAULT '09:00'")
    if 'shift_end_time' not in cols:
        c.execute("ALTER TABLE stores ADD COLUMN shift_end_time TEXT DEFAULT '21:00'")
        
    conn.commit()
    conn.close()
    print("Database refined.")

if __name__ == "__main__":
    refine()
