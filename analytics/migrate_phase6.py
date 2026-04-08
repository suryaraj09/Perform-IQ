import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "performiq.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"Starting Phase 6 Migration on {DB_PATH}...")

    # 1. system_config table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_config (
      config_key TEXT PRIMARY KEY,
      config_value TEXT NOT NULL,
      config_type TEXT NOT NULL,
      description TEXT NOT NULL,
      last_updated_by TEXT,
      last_updated_at TEXT,
      effective_from_week INTEGER,
      effective_from_year INTEGER
    )
    """)

    # 2. system_config_history table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_config_history (
      history_id TEXT PRIMARY KEY,
      config_key TEXT NOT NULL,
      old_value TEXT NOT NULL,
      new_value TEXT NOT NULL,
      changed_by TEXT NOT NULL,
      changed_at TEXT NOT NULL,
      effective_from_week INTEGER,
      effective_from_year INTEGER,
      reason TEXT
    )
    """)

    # 3. weekly_targets table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weekly_targets (
      target_id TEXT PRIMARY KEY,
      employee_id TEXT NOT NULL,
      store_id TEXT NOT NULL,
      week_number INTEGER NOT NULL,
      year INTEGER NOT NULL,
      target_amount REAL NOT NULL,
      set_by TEXT NOT NULL,
      set_at TEXT NOT NULL,
      notes TEXT,
      UNIQUE(employee_id, week_number, year)
    )
    """)

    # 4. Insertion of Default Values
    defaults = [
        (
            'METRIC_WEIGHTS',
            json.dumps({"M1":0.30,"M2":0.25,"M3":0.15,"M4":0.10,"M5":0.10,"M7":0.05,"M8":0.05}),
            'JSON',
            'Weighted coefficients for P score formula. Must sum to exactly 1.00.',
            'SYSTEM', datetime.now().isoformat(), None, None
        ),
        (
            'FLAG_HIGH_SALE_MULTIPLIER',
            '3',
            'NUMBER',
            'Sale flagged if amount exceeds personal average multiplied by this value.',
            'SYSTEM', datetime.now().isoformat(), None, None
        ),
        (
            'FLAG_HIGH_ITEM_COUNT',
            '15',
            'NUMBER',
            'Sale flagged if number of items exceeds this.',
            'SYSTEM', datetime.now().isoformat(), None, None
        ),
        (
            'FLAG_RAPID_SUBMISSION_SECONDS',
            '120',
            'NUMBER',
            'Sale flagged if submitted within this many seconds of the previous sale.',
            'SYSTEM', datetime.now().isoformat(), None, None
        ),
        (
            'PUNCTUALITY_FULL_SCORE_MINUTES',
            '15',
            'NUMBER',
            'Minutes late still earns full punctuality score.',
            'SYSTEM', datetime.now().isoformat(), None, None
        ),
        (
            'PUNCTUALITY_HALF_SCORE_MINUTES',
            '30',
            'NUMBER',
            'Minutes late earns half punctuality score. Beyond this earns zero.',
            'SYSTEM', datetime.now().isoformat(), None, None
        ),
        (
            'GEOFENCE_CHECK_INTERVAL_MINUTES',
            '15',
            'NUMBER',
            'How often silent geofence checks run in minutes.',
            'SYSTEM', datetime.now().isoformat(), None, None
        ),
        (
            'GEOFENCE_CONSECUTIVE_FAILS_ALERT',
            '2',
            'NUMBER',
            'Number of consecutive failed geofence checks before admin alert is triggered.',
            'SYSTEM', datetime.now().isoformat(), None, None
        ),
        (
            'XP_BASE_TIERS',
            json.dumps({
                "tier1":{"minScore":90,"xp":1000},
                "tier2":{"minScore":75,"xp":750},
                "tier3":{"minScore":60,"xp":500},
                "tier4":{"minScore":0,"xp":250}
            }),
            'JSON',
            'Base XP awarded per P score band each week.',
            'SYSTEM', datetime.now().isoformat(), None, None
        ),
        (
            'XP_BONUS_VALUES',
            json.dumps({"streakBonus":200,"leaderboardBonus":300,"perfectRatingBonus":150}),
            'JSON',
            'Bonus XP for streak, leaderboard, perfect rating.',
            'SYSTEM', datetime.now().isoformat(), None, None
        ),
        (
            'LEVEL_THRESHOLDS',
            json.dumps({"Rookie":0,"Associate":1000,"Performer":3000,"Expert":6000,"Champion":10000}),
            'JSON',
            'Cumulative XP required to reach each level.',
            'SYSTEM', datetime.now().isoformat(), None, None
        ),
        (
            'FLAG_AUTO_CONFIRM_HOURS',
            '48',
            'NUMBER',
            'Hours after which unreviewed flagged sales are automatically confirmed.',
            'SYSTEM', datetime.now().isoformat(), None, None
        )
    ]

    cursor.executemany("""
    INSERT OR IGNORE INTO system_config 
    (config_key, config_value, config_type, description, last_updated_by, last_updated_at, effective_from_week, effective_from_year)
    VALUES (?,?,?,?,?,?,?,?)
    """, defaults)

    conn.commit()
    conn.close()
    print("Migration Phase 6 completed successfully.")

if __name__ == "__main__":
    migrate()
