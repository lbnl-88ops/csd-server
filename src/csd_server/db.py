import sqlite3
import os
from datetime import datetime
from pathlib import Path

class ServerDatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.getenv("CSD_DB_PATH", "evaluations.db")
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        # Ensure the parent directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
            except Exception as e:
                print(f"Warning: Could not create database directory {db_dir}: {e}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operator_id INTEGER,
                csd_timestamp TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (operator_id) REFERENCES users (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evaluation_isotopes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evaluation_id INTEGER,
                symbol TEXT NOT NULL,
                s TEXT,
                m INTEGER,
                z INTEGER,
                status TEXT NOT NULL,
                FOREIGN KEY (evaluation_id) REFERENCES evaluations (id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def get_all_users(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users ORDER BY last_used DESC, username ASC")
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        return users

    def add_user(self, username):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (username,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Server DB error: {e}")
            return False
        finally:
            conn.close()

    def update_last_used(self, username):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_used = ? WHERE username = ?",
            (datetime.now().isoformat(), username)
        )
        conn.commit()
        conn.close()
        return True

    def get_user_stats(self, username):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            user_row = cursor.fetchone()
            
            # If user not found, treat as new user
            if not user_row:
                cursor.execute("SELECT COUNT(DISTINCT csd_timestamp) FROM evaluations")
                return 0, cursor.fetchone()[0]
            
            user_id = user_row[0]
            cursor.execute("SELECT COUNT(DISTINCT csd_timestamp) FROM evaluations WHERE operator_id = ?", (user_id,))
            eval_count = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(DISTINCT csd_timestamp) FROM evaluations 
                WHERE operator_id != ? 
                AND csd_timestamp NOT IN (SELECT csd_timestamp FROM evaluations WHERE operator_id = ?)
            """, (user_id, user_id))
            pending_count = cursor.fetchone()[0]

            return eval_count, pending_count
        finally:
            conn.close()

    def get_random_pending_timestamp(self, username):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            user_row = cursor.fetchone()
            
            if not user_row:
                cursor.execute("SELECT DISTINCT csd_timestamp FROM evaluations ORDER BY RANDOM() LIMIT 1")
                row = cursor.fetchone()
                return row[0] if row else None

            user_id = user_row[0]
            cursor.execute("""
                SELECT DISTINCT csd_timestamp FROM evaluations 
                WHERE operator_id != ? 
                AND csd_timestamp NOT IN (SELECT csd_timestamp FROM evaluations WHERE operator_id = ?)
                ORDER BY RANDOM() LIMIT 1
            """, (user_id, user_id))
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def get_leaderboard(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT u.username, COUNT(DISTINCT e.csd_timestamp) as count
                FROM users u
                JOIN evaluations e ON u.id = e.operator_id
                GROUP BY u.username
                ORDER BY count DESC
                LIMIT 3
            """)
            return cursor.fetchall()
        finally:
            conn.close()

    def save_evaluation(self, username, csd_timestamp, isotopes):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            user_row = cursor.fetchone()
            if not user_row:
                return False
            user_id = user_row[0]

            cursor.execute(
                "INSERT INTO evaluations (operator_id, csd_timestamp) VALUES (?, ?)",
                (user_id, csd_timestamp)
            )
            eval_id = cursor.lastrowid

            for iso in isotopes:
                # symbol, s, m, z, status
                cursor.execute(
                    "INSERT INTO evaluation_isotopes (evaluation_id, symbol, s, m, z, status) VALUES (?, ?, ?, ?, ?, ?)",
                    (eval_id, iso[0], iso[1], iso[2], iso[3], iso[4])
                )
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Server DB error saving evaluation: {e}")
            return False
        finally:
            conn.close()
