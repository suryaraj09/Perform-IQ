import firebase_admin
from firebase_admin import credentials
import os
from pathlib import Path

def init_firebase():
    """Initialize Firebase Admin SDK using serviceAccountKey.json."""
    if not firebase_admin._apps:
        key_path = Path(__file__).parent / "serviceAccountKey.json"
        
        if not key_path.exists():
            print(f"WARNING: Firebase service account key not found at {key_path}")
            # Do not throw error here, so startup doesn't entirely crash without it,
            # but Admin APIs won't work until it's provided.
            return
            
        try:
            cred = credentials.Certificate(str(key_path))
            firebase_admin.initialize_app(cred)
            print("Firebase Admin initialized successfully.")
        except Exception as e:
            print(f"Error initializing Firebase Admin: {e}")
