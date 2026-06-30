"""
setup_database.py — one-shot database setup for TalkHobi.

Run this once before a demo/presentation to guarantee the `talkhobi`
database, its tables, and a known set of demo accounts + a demo group all
exist. It is safe to run repeatedly: tables are created with
`IF NOT EXISTS`, and seeding skips users/groups that are already present.

The schema itself is owned by UserDatabase / GroupDatabase (the same classes
the server uses), so this script just drives those classes — it never
re-declares the table layout. That keeps this file in sync with the server
automatically.

Usage (from the project root):
    python -m database_classes.setup_database
"""

import os
import sys

# Make the project root importable no matter where this is launched from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_classes.server_database_class import UserDatabase
from database_classes.group_database_class import GroupDatabase

DB_NAME = "talkhobi"
USER_TABLE = "user_table"

# Demo accounts (username, first, last, email, password). All share the
# password "demo" so they are easy to type during a live presentation.
DEMO_USERS = [
    ("demo1", "Demo", "One", "demo1@talkhobi.local", "demo"),
    ("demo2", "Demo", "Two", "demo2@talkhobi.local", "demo"),
]

# (group_name, owner_username, [member_usernames])
DEMO_GROUPS = [
    ("Demo Room", "demo1", ["demo2"]),
]


def ensure_users(user_db: UserDatabase) -> dict[str, int]:
    """Insert any demo users that don't exist yet. Returns {username: user_id}."""
    ids: dict[str, int] = {}
    for uname, fname, lname, email, password in DEMO_USERS:
        existing_id = user_db.search_id_by_name(uname)
        if existing_id is not None:
            ids[uname] = int(existing_id)
            print(f"  user '{uname}' already exists (id={existing_id})")
            continue
        new_id = user_db.insert_user(uname, fname, lname, email, password)
        ids[uname] = new_id
        print(f"  created user '{uname}' (id={new_id}, password='{password}')")
    return ids


def ensure_groups(group_db: GroupDatabase, user_ids: dict[str, int]) -> None:
    """Create any demo groups that don't exist yet and add their members."""
    for group_name, owner_uname, members in DEMO_GROUPS:
        owner_id = user_ids.get(owner_uname)
        if owner_id is None:
            print(f"  skipping group '{group_name}': owner '{owner_uname}' missing")
            continue

        gid = group_db.get_group_id_by_name(group_name)
        if gid is None:
            gid = group_db.create_group(group_name, owner_id)
            print(f"  created group '{group_name}' (id={gid}, owner={owner_uname})")
        else:
            print(f"  group '{group_name}' already exists (id={gid})")

        for member_uname in members:
            member_id = user_ids.get(member_uname)
            if member_id is None:
                print(f"    skipping member '{member_uname}': user missing")
                continue
            if group_db.is_member(gid, member_id):
                print(f"    '{member_uname}' already in '{group_name}'")
            elif group_db.add_member(gid, member_id):
                print(f"    added '{member_uname}' to '{group_name}'")


def main() -> None:
    print("=== TalkHobi database setup ===")

    # Constructing these creates the database + tables if they are missing
    # (CREATE DATABASE/TABLE IF NOT EXISTS happens inside their __init__).
    print("Ensuring database and tables exist...")
    user_db = UserDatabase(DB_NAME, USER_TABLE, spots=5)
    group_db = GroupDatabase()
    print("Schema ready.\n")

    print("Seeding demo users:")
    user_ids = ensure_users(user_db)

    print("\nSeeding demo groups:")
    ensure_groups(group_db, user_ids)

    print("\nDone. You can now log in with:")
    for uname, _, _, _, password in DEMO_USERS:
        print(f"  username '{uname}'  /  password '{password}'")


if __name__ == "__main__":
    main()
