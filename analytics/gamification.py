"""Gamification engine — XP, levels, badges computed dynamically."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from database import query, execute
from config_service import get_config

LEVEL_THRESHOLDS = [
    (10000, 5, "Champion"),
    (6000, 4, "Expert"),
    (3000, 3, "Performer"),
    (1000, 2, "Associate"),
    (0, 1, "Rookie"),
]

XP_TIERS = [
    (90, 1000),
    (75, 750),
    (60, 500),
    (0, 250),
]

BADGE_DEFINITIONS = {
    "target_crusher": {
        "name": "Target Crusher",
        "emoji": "🎯",
        "description": "3 consecutive weeks above 90% target",
    },
    "rock_solid": {
        "name": "Rock Solid",
        "emoji": "🪨",
        "description": "Stability index above 85 for a month",
    },
    "on_the_rise": {
        "name": "On The Rise",
        "emoji": "📈",
        "description": "Positive growth trend for 4 weeks straight",
    },
    "never_miss": {
        "name": "Never Miss",
        "emoji": "✅",
        "description": "100% attendance for 30 days",
    },
    "early_bird": {
        "name": "Early Bird",
        "emoji": "🌅",
        "description": "On-time every day for 2 weeks",
    },
    "app_champion": {
        "name": "App Champion",
        "emoji": "📱",
        "description": "Top app converter in department",
    },
    "fan_favourite": {
        "name": "Fan Favourite",
        "emoji": "⭐",
        "description": "Avg manager rating above 4.5 for a month",
    },
}

def get_level_info(total_xp: int) -> dict:
    """Get level, title and progress based on dynamic thresholds."""
    # Fetch from DB: {"Rookie":0, "Associate":1000, ...}
    db_thresholds = get_config('LEVEL_THRESHOLDS')
    
    # Convert to sorted list of (threshold, title) ascending
    sorted_thresholds = sorted(db_thresholds.items(), key=lambda x: x[1])
    
    # We need to find current and next
    current_level = 1
    current_title = "Rookie"
    current_threshold = 0
    next_threshold = 0
    
    for i, (title, threshold) in enumerate(sorted_thresholds):
        if total_xp >= threshold:
            current_level = i + 1
            current_title = title
            current_threshold = threshold
            # Peek at next
            if i + 1 < len(sorted_thresholds):
                next_threshold = sorted_thresholds[i+1][1]
            else:
                next_threshold = threshold
        else:
            break
            
    if next_threshold > current_threshold:
        progress = (total_xp - current_threshold) / (next_threshold - current_threshold)
    else:
        progress = 1.0
        
    return {
        "level": current_level,
        "title": current_title,
        "total_xp": total_xp,
        "current_threshold": current_threshold,
        "next_threshold": next_threshold,
        "progress": round(min(1.0, progress), 2),
        "xp_to_next": max(0, next_threshold - total_xp),
    }


def get_xp_for_score(productivity_index: float) -> int:
    """Calculate base XP earned using dynamic tiers."""
    # Fetch from DB: {"tier1":{"minScore":90,"xp":1000}, ...}
    db_tiers = get_config('XP_BASE_TIERS')
    
    # Sort by minScore descending
    tiers = sorted(db_tiers.values(), key=lambda x: x['minScore'], reverse=True)
    
    for tier in tiers:
        if productivity_index >= tier['minScore']:
            return tier['xp']
            
    return 250 # Ultimate fallback


def get_employee_gamification(employee_id: int) -> dict:
    emp = query("SELECT total_xp, level, level_title FROM employees WHERE id = ?", (employee_id,), one=True)
    if not emp:
        return None

    level_info = get_level_info(emp["total_xp"])

    badges = query(
        "SELECT badge_type, badge_name, badge_emoji, earned_at FROM badges WHERE employee_id = ? ORDER BY earned_at DESC",
        (employee_id,),
    )

    streak = _calculate_streak(employee_id)

    return {
        "employee_id": employee_id,
        **level_info,
        "badges": [
            {**b, "description": BADGE_DEFINITIONS.get(b["badge_type"], {}).get("description", "")}
            for b in badges
        ],
        "streak": streak,
        "available_badges": [
            {"type": k, **v, "earned": any(b["badge_type"] == k for b in badges)}
            for k, v in BADGE_DEFINITIONS.items()
        ],
    }


def _calculate_streak(employee_id: int) -> int:
    records = query(
        """SELECT attendance_date FROM attendance 
           WHERE employee_id = ? AND punch_in_status = 'approved'
           ORDER BY attendance_date DESC""",
        (employee_id,),
    )

    if not records:
        return 0

    from datetime import datetime, timedelta

    streak = 1
    for i in range(1, len(records)):
        curr = datetime.strptime(records[i - 1]["attendance_date"], "%Y-%m-%d")
        prev = datetime.strptime(records[i]["attendance_date"], "%Y-%m-%d")
        diff = (curr - prev).days

        if diff <= 2:
            streak += 1
        else:
            break

    return streak


def get_leaderboard(department_id: int = None, store_id: str = None, limit: int = 20) -> list:
    where = "WHERE e.role = 'employee' AND e.is_active = 1"
    params = []

    if department_id:
        where += " AND e.department_id = ?"
        params.append(department_id)
    if store_id:
        where += " AND e.store_id = ?"
        params.append(store_id)

    employees = query(
        f"""SELECT e.id, e.name, e.total_xp, e.level, e.level_title, 
                   d.name as department_name
            FROM employees e 
            JOIN departments d ON e.department_id = d.id
            {where}
            ORDER BY e.total_xp DESC
            LIMIT ?""",
        (*params, limit),
    )

    return [
        {**emp, "rank": idx + 1}
        for idx, emp in enumerate(employees)
    ]
