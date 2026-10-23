"""
Team allocation algorithms and database persistence for Emoji Team Generator.
Implements:
- Mode A: Number-of-teams-based balanced allocation
- Mode B: Maximum-team-size-based balanced allocation
Transactional backend generation ensuring all participants are assigned exactly once.
"""

import math
import random
from typing import List, Dict, Any, Tuple
from database import get_db


TEAM_EMOJI_THEMES = [
    "🚀", "⚡", "🔥", "💎", "🌟", "🎯", "🍀", "🎨",
    "🦄", "🦁", "🦊", "🐼", "🐙", "🌈", "👑", "🔮"
]


def allocate_teams_by_count(participants: List[Dict[str, Any]], num_teams: int) -> List[List[Dict[str, Any]]]:
    """
    Mode A: Distributes participants evenly across a fixed number of teams.
    Ensures team sizes differ by at most 1 participant.
    """
    if not participants:
        raise ValueError("Cannot generate teams: No participants have registered yet.")

    n = len(participants)
    if num_teams < 1:
        raise ValueError("Number of teams must be at least 1.")

    if num_teams > n:
        raise ValueError(f"Cannot form {num_teams} teams with only {n} registered participant(s). Maximum teams possible is {n}.")

    # Randomly shuffle participants
    shuffled = list(participants)
    random.shuffle(shuffled)

    teams = [[] for _ in range(num_teams)]
    for idx, participant in enumerate(shuffled):
        teams[idx % num_teams].append(participant)

    return teams


def allocate_teams_by_max_size(participants: List[Dict[str, Any]], max_team_size: int) -> List[List[Dict[str, Any]]]:
    """
    Mode B: Distributes participants such that no team exceeds max_team_size,
    avoiding unnecessary empty teams and balancing sizes evenly.
    """
    if not participants:
        raise ValueError("Cannot generate teams: No participants have registered yet.")

    n = len(participants)
    if max_team_size < 1:
        raise ValueError("Maximum team size must be at least 1.")

    num_teams = math.ceil(n / max_team_size)
    if num_teams < 1:
        num_teams = 1

    shuffled = list(participants)
    random.shuffle(shuffled)

    teams = [[] for _ in range(num_teams)]
    for idx, participant in enumerate(shuffled):
        teams[idx % num_teams].append(participant)

    return teams


def generate_and_save_teams(
    session_id: int,
    mode: str,
    team_count: int = 4,
    max_team_size: int = 5,
    conn=None
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Executes team allocation inside a database transaction.
    Clears existing teams and assignments for this session,
    creates new team records, and updates participant team IDs.

    Returns:
        (teams_list, total_assigned_participants)
    """
    db = conn or get_db()

    # Fetch all participants for this session
    participants_rows = db.execute(
        "SELECT id, name, normalized_name, selected_emoji FROM participants WHERE session_id = ? ORDER BY id ASC",
        (session_id,)
    ).fetchall()

    participants = [dict(r) for r in participants_rows]
    if not participants:
        raise ValueError("No participants registered in this session. Cannot generate teams.")

    # Calculate distribution
    if mode == "max_size":
        allocated = allocate_teams_by_max_size(participants, max_team_size)
    elif mode == "team_count":
        allocated = allocate_teams_by_count(participants, team_count)
    else:
        raise ValueError(f"Invalid team formation mode: '{mode}'. Must be 'team_count' or 'max_size'.")

    # Transactional persistence
    try:
        with db:
            # Clear previous team assignments
            db.execute("UPDATE participants SET team_id = NULL WHERE session_id = ?", (session_id,))
            db.execute("DELETE FROM teams WHERE session_id = ?", (session_id,))

            created_teams = []
            total_assigned = 0

            for i, team_members in enumerate(allocated, start=1):
                theme_icon = TEAM_EMOJI_THEMES[(i - 1) % len(TEAM_EMOJI_THEMES)]
                team_name = f"Team {i} {theme_icon}"

                cursor = db.execute(
                    "INSERT INTO teams (session_id, team_name) VALUES (?, ?)",
                    (session_id, team_name)
                )
                team_id = cursor.lastrowid

                # Assign participants to this team
                for member in team_members:
                    db.execute(
                        "UPDATE participants SET team_id = ? WHERE id = ? AND session_id = ?",
                        (team_id, member["id"], session_id)
                    )
                    total_assigned += 1

                created_teams.append({
                    "id": team_id,
                    "team_name": team_name,
                    "members": team_members,
                    "member_count": len(team_members)
                })

            # Update session formation mode and settings
            db.execute("""
                UPDATE sessions
                SET team_formation_mode = ?,
                    team_count = ?,
                    max_team_size = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (mode, len(created_teams), max_team_size, session_id))

        return created_teams, total_assigned
    except Exception as exc:
        raise RuntimeError(f"Database error while saving generated teams: {exc}") from exc


def get_session_teams_with_members(session_id: int, conn=None) -> List[Dict[str, Any]]:
    """
    Fetches all teams for the given session along with their assigned participants.
    """
    db = conn or get_db()
    teams_rows = db.execute(
        "SELECT id, team_name, created_at FROM teams WHERE session_id = ? ORDER BY id ASC",
        (session_id,)
    ).fetchall()

    teams_list = []
    for t_row in teams_rows:
        team_id = t_row["id"]
        members_rows = db.execute(
            """
            SELECT id, name, selected_emoji, created_at
            FROM participants
            WHERE session_id = ? AND team_id = ?
            ORDER BY name COLLATE NOCASE ASC
            """,
            (session_id, team_id)
        ).fetchall()

        members = [dict(m) for m in members_rows]
        teams_list.append({
            "id": team_id,
            "team_name": t_row["team_name"],
            "created_at": t_row["created_at"],
            "member_count": len(members),
            "members": members
        })

    return teams_list
