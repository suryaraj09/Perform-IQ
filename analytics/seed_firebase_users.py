import sqlite3
import firebase_admin
from firebase_admin import credentials, auth
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "performiq.db"
KEY_PATH = Path(__file__).parent / "serviceAccountKey.json"

def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def seed_firebase_users():
    if not KEY_PATH.exists():
        print(f"Skipping seed: {KEY_PATH} not found.")
        return

    if not firebase_admin._apps:
        cred = credentials.Certificate(str(KEY_PATH))
        firebase_admin.initialize_app(cred)

    conn = get_connection()
    c = conn.cursor()
    
    print("Seeding SQLite Users to Firebase Auth...")

    # Head Office
    try:
        user = auth.create_user(
            email='headoffice@bluebuddha.com',
            password='HO@PerformIQ2024',
            display_name='Head Office'
        )
        auth.set_custom_user_claims(user.uid, {
            'role': 'HEAD_OFFICE',
            'storeId': None,
            'employeeId': None
        })
        print(f"Created HO: {user.uid}")
    except Exception as e:
        print(f"HO creation skipped/failed: {e}")

    # Store Managers
    managers = [
        ('manager.navrangpura@bluebuddha.com', 'Mgr@S001', 'S001', 'Navrangpura Manager'),
        ('manager.satellite@bluebuddha.com', 'Mgr@S002', 'S002', 'Satellite Manager'),
        ('manager.bopal@bluebuddha.com', 'Mgr@S003', 'S003', 'Bopal Manager')
    ]
    for email, pwd, s_id, name in managers:
        try:
            user = auth.create_user(
                email=email,
                password=pwd,
                display_name=name
            )
            auth.set_custom_user_claims(user.uid, {
                'role': 'STORE_MANAGER',
                'storeId': s_id,
                'employeeId': None
            })
            print(f"Created Mgr {s_id}: {user.uid}")
        except Exception as e:
            print(f"Mgr {s_id} creation skipped/failed: {e}")

    # Employees
    c.execute("SELECT id, name, email, store_id FROM employees WHERE role='employee'")
    employees = c.fetchall()
    
    for emp in employees:
        emp_id = str(emp['id'])
        name = emp['name']
        s_id = str(emp['store_id'])
        email = emp['email'] if emp['email'] else f"{emp_id.lower()}@bluebuddha.com"
        pwd = f"Emp@{emp_id}"
        
        try:
            user = auth.create_user(
                email=email,
                password=pwd,
                display_name=name
            )
            auth.set_custom_user_claims(user.uid, {
                'role': 'EMPLOYEE',
                'storeId': s_id,
                'employeeId': emp_id
            })
            # Save back to SQLite
            c.execute("UPDATE employees SET firebase_uid = ? WHERE id = ?", (user.uid, emp['id']))
            print(f"Created Emp {emp_id}: {user.uid}")
        except Exception as e:
            print(f"Emp {emp_id} skipped/failed: {e}")

    conn.commit()
    conn.close()
    print("Seeding complete.")

if __name__ == '__main__':
    seed_firebase_users()
