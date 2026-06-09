import mysql.connector
import random
import threading
import hashlib
import os

# Ai generated lists of random user values
usernames = [
    "ShadowNinja99",
    "CosmicWanderer",
    "BlueOcean22",
    "PixelPioneer",
    "LunaStar88",
    "TechWizard_X",
    "CrimsonPhoenix",
    "SilentEcho123",
    "NeonDreamer",
    "QuantumLeap00"
]

first_names = [
    "Alice",
    "Bob",
    "Charlie",
    "Diana",
    "Aytaan",
    "Fiona",
    "George",
    "Hannah",
    "Ian",
    "Julia"
]

last_names = [
    "Smith",
    "Johnson",
    "Skye",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez"
]

emails = [
    "alice.smith@example.com",
    "bjohnson99@test.org",
    "charlie.w@mail.net",
    "diana_brown@domain.com",
    "ejones@email.co",
    "fgarcia88@webmail.com",#s
    "george.miller@inbox.net",
    "hdavis@service.org",
    "ian_rodriguez@company.com",
    "julia.m@platform.io"
]


class UserDatabase:
    def __init__(self, db_name: str, table_name: str, spots: int):
        self.table_name = table_name
        self.db_name = db_name
        self.lock = threading.Lock()
        self.free_spots = threading.Semaphore(spots)
        self.create_db()
        self.create_table()

    # UNIQUE = everyone must be different
    # KEY AUTOINCREMENT = new user_id is automatically generated
    # NOT NULL = can't be empty

    def create_db(self):
        conn = mysql.connector.connect(host="localhost",username="root", password="Itay2008!",port=3306)
        my_cursor = conn.cursor()
        my_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.db_name}")
        conn.commit()
        conn.close()

    def create_table(self):
        query = f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} ( 
                 user_ID INT AUTO_INCREMENT PRIMARY KEY , 
                user_name VARCHAR(50) NOT NULL UNIQUE, 
                first_name TEXT NOT NULL, 
                last_name TEXT NOT NULL, 
                email VARCHAR(255) NOT NULL UNIQUE, 
                password TEXT NOT NULL,
                salt BINARY(16) NOT NULL
                )
            """
        with self.lock:
            conn = self.open_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()
            conn.close()

    # If the table exists, it will be deleted
    def delete_users_table(self):
        with self.lock:
            conn = self.open_connection()
            query = f"DROP TABLE IF EXISTS {self.table_name}"
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()
            conn.close()


    # Inserting a new user into the database.
    # Returns the new user_ID on success, or None if the insert failed
    def insert_user(self, uname: str, fname: str, lname: str, email: str, password: str):
        with self.lock:
            salt = os.urandom(16)
            conn = self.open_connection()
            cursor = conn.cursor()
            salted_password = password+str(salt)
            hashed_pass = hashlib.sha256(salted_password.encode())
            new_id = None
            try:
                query = f"INSERT INTO {self.table_name} (user_name,first_name, last_name, email, password,salt) VALUES (%s, %s, %s, %s, %s,%s)"
                cursor.execute(query, (uname, fname, lname, email, hashed_pass.hexdigest(),salt))
                conn.commit()
                new_id = cursor.lastrowid
            except Exception as e:
                print(e)
            conn.close()
            return new_id


    def insert_random_user(self):
        self.insert_user(random.choice(usernames), random.choice(first_names),  # creating a random user
                         random.choice(last_names), random.choice(emails), "01234")

    # Gets all users from the database.
    def fetch_all_users(self):  # Getting all users from the database.
        with self.free_spots:
            conn = self.open_connection()
            cursor = conn.cursor()

            query = f"SELECT * FROM {self.table_name}"

            cursor.execute(query)
            users = cursor.fetchall()

            conn.close()
        return users

    def display_users(self):
        users = self.fetch_all_users()
        if users:
            print("\nUsers:")
            for user in users:
                print(user[0], user[1], user[2], user[3], user[4], user[5],user[6],
                      sep=", ")  # Sep is the separator between the values.
        else:
            print("\nNo users found in the database.")

    def delete_user_by_email(self, email: str):
        table_name = self.table_name
        with self.lock:
            conn = self.open_connection()
            query = "DELETE FROM table_name WHERE email = %s"
            cursor = conn.cursor()
            cursor.execute(query, (email,))
            conn.commit()
            conn.close()


    def select_user_by_full_name(self, fname: str, lname :str):
        conn = self.open_connection()
        with self.free_spots:
            query = f"SELECT * FROM {self.table_name} WHERE first_name = %s AND last_name = %s"
            cursor = conn.cursor()
            cursor.execute(query, (fname, lname))
        user = cursor.fetchone()
        conn.close()
        return user

    def search_user_by_user_name_and_password(self, uname, password):
        conn = self.open_connection()
        query = f"SELECT salt FROM {self.table_name} WHERE user_name = %s"
        cursor = conn.cursor()
        cursor.execute(query, (uname,))

        salt = cursor.fetchone()
        if salt is None:
            return None
        salted_password = password + str(salt[0])
        hashed_pass = hashlib.sha256(salted_password.encode())
        with self.free_spots:
            query = f"SELECT * FROM {self.table_name} WHERE user_name = %s AND password = %s"
            cursor = conn.cursor()
            cursor.execute(query, (uname, hashed_pass.hexdigest()))
        user = cursor.fetchone()
        conn.close()
        return user

    def search_user_by_email_and_password(self,email,password):
        conn = self.open_connection()
        query = f"SELECT salt FROM {self.table_name} WHERE email = %s"
        cursor = conn.cursor()
        cursor.execute(query, (email,))

        salt = cursor.fetchone()
        if salt is None:
            return None
        salted_password = password + str(salt[0])
        hashed_pass = hashlib.sha256(salted_password.encode())
        with self.free_spots:
            query = f"SELECT * FROM {self.table_name} WHERE email = %s AND password = %s"
            cursor = conn.cursor()
            cursor.execute(query, (email, hashed_pass.hexdigest()))
        user = cursor.fetchone()
        conn.close()
        return user

    def search_name_by_id(self, user_id : str):
        user_id = int(user_id)
        conn = self.open_connection()
        query = f"SELECT USER_NAME FROM {self.table_name} WHERE user_ID = %s"
        cursor = conn.cursor()
        cursor.execute(query, (user_id,))
        user_name = cursor.fetchone()
        if not user_name:
            return None
        return user_name[0]

    def search_id_by_name(self,user_name):
        conn = self.open_connection()
        query = f"SELECT user_ID FROM {self.table_name} WHERE USER_NAME = %s"
        cursor = conn.cursor()
        cursor.execute(query, (user_name,))
        user_id = cursor.fetchone()
        if not user_id:
            return None
        return str(user_id[0])

    def is_user_name_available(self, uname):
        conn = self.open_connection()
        query = f"SELECT user_ID FROM {self.table_name} WHERE user_name = %s"
        cursor = conn.cursor()
        cursor.execute(query, (uname,))
        user = cursor.fetchone()
        conn.close()
        return user is None   # no row -> the name is available

    def is_email_available(self, email):
        conn = self.open_connection()
        query = f"SELECT user_ID FROM {self.table_name} WHERE email = %s"
        cursor = conn.cursor()
        cursor.execute(query, (email,))
        user = cursor.fetchone()
        conn.close()
        return user is None   # no row -> the email is available


    def open_connection(self):
        self.create_db()
        conn = mysql.connector.connect(host="localhost", database=self.db_name,username="root", password="Itay2008!",port=3306)
        return conn

