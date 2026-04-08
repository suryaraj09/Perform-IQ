import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from database import query

def check():
    tables = [t['name'] for t in query("SELECT name FROM sqlite_master WHERE type='table'")]
    print("TABLES:", tables)
    for table in tables:
        cols = query(f"PRAGMA table_info({table})")
        col_names = [f"{c['name']}({c['type']})" for c in cols]
        print(f"  {table}: {col_names}")

if __name__ == "__main__":
    check()
