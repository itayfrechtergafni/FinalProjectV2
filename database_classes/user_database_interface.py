import mysql.connector
import hashlib
import os

HOST = "localhost"
USER = "root"
PASSWORD = "Itay2008!"
PORT = 3306
DB = "talkhobi"
TABLE = "user_table"


def open_conn():
    return mysql.connector.connect(host=HOST, database=DB, username=USER, password=PASSWORD, port=PORT)


def hash_password(password: str, salt: bytes) -> str:
    salted = password + str(salt)
    return hashlib.sha256(salted.encode()).hexdigest()


def list_users():
    conn = open_conn()
    cursor = conn.cursor()
    cursor.execute(f"SELECT user_ID, user_name, first_name, last_name, email FROM {TABLE}")
    users = cursor.fetchall()
    conn.close()

    if not users:
        print("\nNo users found.")
        return

    print(f"\n{'ID':<6} {'Username':<20} {'First':<12} {'Last':<20} {'Email'}")
    print("-" * 80)
    for u in users:
        print(f"{u[0]:<6} {u[1]:<20} {u[2]:<12} {u[3]:<20} {u[4]}")


def add_user():
    print("\n--- Add User ---")
    uname = input("Username: ").strip()
    fname = input("First name: ").strip()
    lname = input("Last name: ").strip()
    email = input("Email: ").strip()
    password = input("Password: ").strip()

    salt = os.urandom(16)
    hashed = hash_password(password, salt)

    conn = open_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"INSERT INTO {TABLE} (user_name, first_name, last_name, email, password, salt) VALUES (%s, %s, %s, %s, %s, %s)",
            (uname, fname, lname, email, hashed, salt)
        )
        conn.commit()
        print(f"User '{uname}' added successfully.")
    except mysql.connector.IntegrityError as e:
        print(f"Error: {e}")
    finally:
        conn.close()


def remove_user():
    print("\n--- Remove User ---")
    uname = input("Username to remove: ").strip()

    conn = open_conn()
    cursor = conn.cursor()
    cursor.execute(f"SELECT user_ID, user_name, email FROM {TABLE} WHERE user_name = %s", (uname,))
    user = cursor.fetchone()

    if not user:
        print(f"No user found with username '{uname}'.")
        conn.close()
        return

    print(f"Found: ID={user[0]}, Username={user[1]}, Email={user[2]}")
    confirm = input("Are you sure you want to delete this user? (yes/no): ").strip().lower()
    if confirm == "yes":
        cursor.execute(f"DELETE FROM {TABLE} WHERE user_name = %s", (uname,))
        conn.commit()
        print(f"User '{uname}' deleted.")
    else:
        print("Cancelled.")
    conn.close()


def change_password():
    print("\n--- Change Password ---")
    uname = input("Username: ").strip()

    conn = open_conn()
    cursor = conn.cursor()
    cursor.execute(f"SELECT user_ID FROM {TABLE} WHERE user_name = %s", (uname,))
    user = cursor.fetchone()

    if not user:
        print(f"No user found with username '{uname}'.")
        conn.close()
        return

    new_password = input("New password: ").strip()
    new_salt = os.urandom(16)
    new_hash = hash_password(new_password, new_salt)

    cursor.execute(
        f"UPDATE {TABLE} SET password = %s, salt = %s WHERE user_name = %s",
        (new_hash, new_salt, uname)
    )
    conn.commit()
    print(f"Password updated for '{uname}'.")
    conn.close()


def edit_user():
    print("\n--- Edit User ---")
    uname = input("Username to edit: ").strip()

    conn = open_conn()
    cursor = conn.cursor()
    cursor.execute(f"SELECT user_name, first_name, last_name, email FROM {TABLE} WHERE user_name = %s", (uname,))
    user = cursor.fetchone()

    if not user:
        print(f"No user found with username '{uname}'.")
        conn.close()
        return

    print(f"\nCurrent values:")
    print(f"  1. Username  : {user[0]}")
    print(f"  2. First name: {user[1]}")
    print(f"  3. Last name : {user[2]}")
    print(f"  4. Email     : {user[3]}")
    print("  (leave blank to keep current value)")

    new_uname = input(f"New username [{user[0]}]: ").strip() or user[0]
    new_fname = input(f"New first name [{user[1]}]: ").strip() or user[1]
    new_lname = input(f"New last name [{user[2]}]: ").strip() or user[2]
    new_email = input(f"New email [{user[3]}]: ").strip() or user[3]

    try:
        cursor.execute(
            f"UPDATE {TABLE} SET user_name=%s, first_name=%s, last_name=%s, email=%s WHERE user_name=%s",
            (new_uname, new_fname, new_lname, new_email, uname)
        )
        conn.commit()
        print("User updated successfully.")
    except mysql.connector.IntegrityError as e:
        print(f"Error: {e}")
    finally:
        conn.close()


MENU = {
    "1": ("List all users",    list_users),
    "2": ("Add user",          add_user),
    "3": ("Remove user",       remove_user),
    "4": ("Change password",   change_password),
    "5": ("Edit user details", edit_user),
    "0": ("Exit",              None),
}

def main():
    print("=== TalkHobi User Manager ===")
    while True:
        print()
        for key, (label, _) in MENU.items():
            print(f"  [{key}] {label}")
        choice = input("\nChoice: ").strip()

        if choice == "0":
            break
        elif choice in MENU:
            _, fn = MENU[choice]
            try:
                fn()
            except Exception as e:
                print(f"Unexpected error: {e}")
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()