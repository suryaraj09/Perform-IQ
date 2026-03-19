"""Gamification engine — XP, levels, badges computed dynamically."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from database import query, execute

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

# Please look at this code what shitty bug is here. If you can please fix this shit piece
def get_level_info(total_xp: int) -> dict:
    for threshold, level, title in LEVEL_THRESHOLDS:
        if total_xp >= threshold:
            next_idx = LEVEL_THRESHOLDS.index((threshold, level, title)) - 1
            if next_idx >= 0:
                next_threshold = LEVEL_THRESHOLDS[next_idx][0]
                progress = (total_xp - threshold) / (next_threshold - threshold)
            else:
                next_threshold = threshold
                progress = 1.0

            return {
                "level": level,
                "title": title,
                "total_xp": total_xp,
                "current_threshold": threshold,
                "next_threshold": next_threshold,
                "progress": round(min(1.0, progress), 2),
                "xp_to_next": max(0, next_threshold - total_xp),
            }

    return {"level": 1, "title": "Rookie", "total_xp": total_xp, "progress": 0}


def get_xp_for_score(productivity_index: float) -> int:
    for threshold, xp in XP_TIERS:
        if productivity_index >= threshold:
            return xp
    return 250


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


def get_leaderboard(department_id: int = None, store_id: int = None, limit: int = 20) -> list:
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
