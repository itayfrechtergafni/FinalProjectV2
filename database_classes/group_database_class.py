import mysql.connector
import threading

# --- Connection settings ---
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "Itay2008!"
DB_PORT = 3306
DB_NAME = "talkhobi"
USER_TABLE = "user_table"

class GroupDatabase:


    def __init__(self, db_name: str = DB_NAME,
                 groups_table: str = "groups_table",
                 members_table: str = "group_members"):
        self.db_name = db_name
        self.groups_table = groups_table
        self.members_table = members_table
        self.lock = threading.Lock()
        self.create_db()
        self.create_tables()

    # --- Setup ---

    def create_db(self):
        conn = mysql.connector.connect(host=DB_HOST, username=DB_USER,
                                       password=DB_PASSWORD, port=DB_PORT)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.db_name}")
        conn.commit()
        conn.close()

    def open_connection(self):
        return mysql.connector.connect(host=DB_HOST, database=self.db_name,
                                       username=DB_USER, password=DB_PASSWORD,
                                       port=DB_PORT)

    def create_tables(self):
        groups_query = f"""
            CREATE TABLE IF NOT EXISTS {self.groups_table} (
                group_id   INT AUTO_INCREMENT PRIMARY KEY,
                group_name VARCHAR(50) NOT NULL,
                owner_id   INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES {USER_TABLE}(user_ID)
            )
            """
        members_query = f"""
            CREATE TABLE IF NOT EXISTS {self.members_table} (
                group_id INT NOT NULL,
                user_id  INT NOT NULL,
                role     VARCHAR(10) NOT NULL DEFAULT 'member',
                PRIMARY KEY (group_id, user_id),
                FOREIGN KEY (group_id) REFERENCES {self.groups_table}(group_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id)  REFERENCES {USER_TABLE}(user_ID)
            )
            """
        with self.lock:
            conn = self.open_connection()
            cursor = conn.cursor()
            cursor.execute(groups_query)
            cursor.execute(members_query)
            conn.commit()
            conn.close()

    def drop_tables(self):
        with self.lock:
            conn = self.open_connection()
            cursor = conn.cursor()
            # members first because of the foreign key
            cursor.execute(f"DROP TABLE IF EXISTS {self.members_table}")
            cursor.execute(f"DROP TABLE IF EXISTS {self.groups_table}")
            conn.commit()
            conn.close()

    # --- Group actions ---

    def create_group(self, group_name: str, owner_id: int):
        with self.lock:
            conn = self.open_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    f"INSERT INTO {self.groups_table} (group_name, owner_id) VALUES (%s, %s)",
                    (group_name, owner_id))
                group_id = cursor.lastrowid
                cursor.execute(
                    f"INSERT INTO {self.members_table} (group_id, user_id, role) VALUES (%s, %s, 'owner')",
                    (group_id, owner_id))
                conn.commit()
                return group_id
            except Exception as e:
                print(e)
                conn.rollback()
                return None
            finally:
                conn.close()

    def delete_group(self, group_id: int):
        with self.lock:
            conn = self.open_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(f"DELETE FROM {self.groups_table} WHERE group_id = %s", (group_id,))
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                print(e)
                return False
            finally:
                conn.close()

    def rename_group(self, group_id: int, new_name: str):
        with self.lock:
            conn = self.open_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    f"UPDATE {self.groups_table} SET group_name = %s WHERE group_id = %s",
                    (new_name, group_id))
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                print(e)
                return False
            finally:
                conn.close()

    # --- Member actions ---

    def add_member(self, group_id: int, user_id: int, role: str = 'member'):
        with self.lock:
            conn = self.open_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    f"INSERT INTO {self.members_table} (group_id, user_id, role) VALUES (%s, %s, %s)",
                    (group_id, user_id, role))
                conn.commit()
                return True
            except Exception as e:
                print(e)
                return False
            finally:
                conn.close()

    def remove_member(self, group_id: int, user_id: int):
        with self.lock:
            conn = self.open_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    f"DELETE FROM {self.members_table} WHERE group_id = %s AND user_id = %s AND role <> 'owner'",
                    (group_id, user_id))
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                print(e)
                return False
            finally:
                conn.close()

    # --- Queries ---

    def get_group(self, group_id: int):
        conn = self.open_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT group_id, group_name, owner_id, created_at FROM {self.groups_table} WHERE group_id = %s",
            (group_id,))
        row = cursor.fetchone()
        conn.close()
        return row

    def get_all_groups(self):
        conn = self.open_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT group_id, group_name, owner_id, created_at FROM {self.groups_table} ORDER BY group_id")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_group_id_by_name(self, group_name: str):
        conn = self.open_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT group_id FROM {self.groups_table} WHERE group_name = %s LIMIT 1",
            (group_name,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def list_groups_for_user(self, user_id: int):
        conn = self.open_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"""SELECT g.group_id, g.group_name, g.owner_id
                FROM {self.groups_table} g
                JOIN {self.members_table} m ON g.group_id = m.group_id
                WHERE m.user_id = %s
                ORDER BY g.group_id""",
            (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return rows

    def list_members(self, group_id: int):
        conn = self.open_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"""SELECT m.user_id, u.user_name, m.role
                FROM {self.members_table} m
                JOIN {USER_TABLE} u ON m.user_id = u.user_ID
                WHERE m.group_id = %s
                ORDER BY m.role <> 'owner', u.user_name""",
            (group_id,))
        rows = cursor.fetchall()
        conn.close()
        return rows

    def is_member(self, group_id: int, user_id: int):
        conn = self.open_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT 1 FROM {self.members_table} WHERE group_id = %s AND user_id = %s LIMIT 1",
            (group_id, user_id))
        found = cursor.fetchone() is not None
        conn.close()
        return found

    def is_owner(self, group_id: int, user_id: int):
        conn = self.open_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT 1 FROM {self.groups_table} WHERE group_id = %s AND owner_id = %s LIMIT 1",
            (group_id, user_id))
        found = cursor.fetchone() is not None
        conn.close()
        return found

    def print_tables(self):
        conn = self.open_connection()
        cursor = conn.cursor()

        print(f"\n=== {self.groups_table} ===")
        cursor.execute(
            f"SELECT group_id, group_name, owner_id, created_at FROM {self.groups_table} ORDER BY group_id")
        groups = cursor.fetchall()
        if groups:
            for gid, name, owner, created in groups:
                print(f"  group_id={gid}, name={name}, owner_id={owner}, created={created}")
        else:
            print("  (empty)")

        print(f"\n=== {self.members_table} ===")
        cursor.execute(
            f"SELECT group_id, user_id, role FROM {self.members_table} ORDER BY group_id, role <> 'owner', user_id")
        members = cursor.fetchall()
        if members:
            for gid, uid, role in members:
                print(f"  group_id={gid}, user_id={uid}, role={role}")
        else:
            print("  (empty)")

        conn.close()



def _print_groups(db: GroupDatabase):
    groups = db.get_all_groups()
    if not groups:
        print("  (no groups yet)")
        return
    for gid, name, owner, created in groups:
        print(f"  [{gid}] {name}  (owner_id={owner}, created {created})")


def _menu():
    db = GroupDatabase()
    print("Connected to group database. Tables ready.")

    actions = """
Choose an action:
  1) Create group
  2) Delete group
  3) Rename group
  4) Add member
  5) Remove member
  6) List all groups
  7) List groups for a user
  8) List members of a group
  9) Print both tables
  0) Quit
"""
    while True:
        print(actions)
        choice = input("> ").strip()
        try:
            if choice == "1":
                name = input("Group name: ").strip()
                owner = int(input("Owner user_id: ").strip())
                gid = db.create_group(name, owner)
                print(f"Created group_id={gid}" if gid else "Failed to create group.")
            elif choice == "2":
                gid = int(input("group_id to delete: ").strip())
                print("Deleted." if db.delete_group(gid) else "Nothing deleted.")
            elif choice == "3":
                gid = int(input("group_id: ").strip())
                name = input("New name: ").strip()
                print("Renamed." if db.rename_group(gid, name) else "Nothing renamed.")
            elif choice == "4":
                gid = int(input("group_id: ").strip())
                uid = int(input("user_id to add: ").strip())
                print("Added." if db.add_member(gid, uid) else "Failed (already a member / bad id?).")
            elif choice == "5":
                gid = int(input("group_id: ").strip())
                uid = int(input("user_id to remove: ").strip())
                print("Removed." if db.remove_member(gid, uid) else "Nothing removed (owner / not a member?).")
            elif choice == "6":
                _print_groups(db)
            elif choice == "7":
                uid = int(input("user_id: ").strip())
                for gid, name, owner in db.list_groups_for_user(uid):
                    print(f"  [{gid}] {name}  (owner_id={owner})")
            elif choice == "8":
                gid = int(input("group_id: ").strip())
                for uid, uname, role in db.list_members(gid):
                    print(f"  {uid}: {uname} ({role})")
            elif choice == "9":
                db.print_tables()
            elif choice == "0":
                break
            else:
                print("Unknown option.")
        except ValueError:
            print("That needs to be a number.")
        except Exception as e:
            print("Error:", e)


if __name__ == "__main__":
    _menu()
