import os
import hashlib
import sqlite3
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Try importing pymysql safely; if not installed, gracefully fall back to SQLite
try:
    import pymysql
    import pymysql.cursors
except ImportError:
    pymysql = None

# Indian Standard Time (IST, UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

def get_current_ist_str() -> str:
    """Returns current IST timestamp string YYYY-MM-DD HH:MM:SS."""
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

def get_current_ist_display() -> str:
    """Returns current IST formatted time (e.g. 11:30 PM)."""
    return datetime.now(IST).strftime("%I:%M %p")

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "chatbot_db")

SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chatbot_local.db")

# Helper function to hash passwords securely using SHA-256
def hash_password(password: str) -> str:
    salt = "mini_project_secret_salt_2026"
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

def get_mysql_connection(include_db: bool = True):
    """Attempts to connect to MySQL if PyMySQL is available with short timeout."""
    if pymysql is None or DB_PASSWORD == "your_mysql_password":
        return None
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME if include_db else None,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=1,
            autocommit=True
        )
        return conn
    except Exception:
        return None

def get_sqlite_connection():
    """High-performance SQLite connection with WAL journal mode and busy timeout."""
    conn = sqlite3.connect(SQLITE_DB_PATH, timeout=15.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn

# Flag to remember if MySQL is working
MYSQL_ACTIVE = False

def init_db():
    """Initializes tables in MySQL if available, or falls back to SQLite."""
    global MYSQL_ACTIVE

    # Try MySQL first
    mysql_conn = get_mysql_connection(include_db=False)
    if mysql_conn:
        try:
            with mysql_conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4;")
                cursor.execute(f"USE `{DB_NAME}`;")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(100) NOT NULL,
                        email VARCHAR(150) NOT NULL UNIQUE,
                        password_hash VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_history (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NULL,
                        role ENUM('user', 'assistant') NOT NULL,
                        message TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    );
                """)
            mysql_conn.close()
            MYSQL_ACTIVE = True
            print(f"[Database] Connected to MySQL successfully! Database '{DB_NAME}' active.")
            return True
        except Exception as e:
            print(f"[Database Notice] MySQL setup error: {e}")
            try:
                mysql_conn.close()
            except Exception:
                pass

    # Fallback to local SQLite if MySQL isn't connected
    print("[Database] MySQL not reachable. Using local SQLite database (chatbot_local.db) in high-speed WAL mode.")
    MYSQL_ACTIVE = False
    sqlite_conn = get_sqlite_connection()
    with sqlite_conn:
        cursor = sqlite_conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NULL,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        # Ensure fast lookup indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_userid ON chat_history(user_id);")
    sqlite_conn.close()
    return True

# --- User Management Functions ---

def create_user(username: str, email: str, password: str):
    """Registers a new user with compulsory password. If user already exists with matching password, logs them in."""
    email = email.strip().lower()
    if not email:
        return None, "Email address is required."
    if not password or len(password.strip()) < 4:
        return None, "Password is required (minimum 4 characters)."

    password = password.strip()
    hashed = hash_password(password)

    if MYSQL_ACTIVE:
        conn = get_mysql_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id, username, email, password_hash FROM users WHERE email = %s;", (email,))
                    existing = cursor.fetchone()
                    if existing:
                        dummy_hash = hash_password(f"oauth_user_{email}")
                        if existing["password_hash"] == dummy_hash or verify_password(password, existing["password_hash"]):
                            cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s;", (hashed, existing["id"]))
                            return {"id": existing["id"], "username": existing["username"], "email": existing["email"]}, None
                        return None, "Email is already registered. Please sign in."
                    cursor.execute(
                        "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s);",
                        (username or email.split("@")[0].title(), email, hashed)
                    )
                    return {"id": cursor.lastrowid, "username": username, "email": email}, None
            except Exception as e:
                print(f"[MySQL Create Error]: {e}")
            finally:
                conn.close()

    # SQLite Fast Path
    conn = get_sqlite_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, password_hash FROM users WHERE email = ?;", (email,))
        row = cursor.fetchone()
        if row:
            dummy_hash = hash_password(f"oauth_user_{email}")
            if row["password_hash"] == dummy_hash or verify_password(password, row["password_hash"]):
                with conn:
                    cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?;", (hashed, row["id"]))
                return {"id": row["id"], "username": row["username"], "email": row["email"]}, None
            return None, "Email is already registered. Please sign in."
        with conn:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?);",
                (username or email.split("@")[0].title(), email, hashed)
            )
            return {"id": cursor.lastrowid, "username": username or email.split("@")[0].title(), "email": email}, None
    finally:
        conn.close()

def create_or_get_oauth_user(username: str, email: str, password: str):
    """Registers or logs in a user via Google or Phone with compulsory password."""
    email = email.strip().lower()
    if not email:
        return None, "Account identifier (email or phone) is required."
    if not password or len(password.strip()) < 4:
        return None, "Password is required (minimum 4 characters)."

    password = password.strip()
    hashed = hash_password(password)

    if MYSQL_ACTIVE:
        conn = get_mysql_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id, username, email, password_hash FROM users WHERE email = %s;", (email,))
                    existing = cursor.fetchone()
                    if existing:
                        dummy_hash = hash_password(f"oauth_user_{email}")
                        if existing["password_hash"] == dummy_hash:
                            cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s;", (hashed, existing["id"]))
                            return {"id": existing["id"], "username": existing["username"], "email": existing["email"]}, None
                        if not verify_password(password, existing["password_hash"]):
                            return None, "Incorrect password for this account. Please enter your existing password or use 'Forgot?'."
                        return {"id": existing["id"], "username": existing["username"], "email": existing["email"]}, None
                    # Create new account
                    cursor.execute(
                        "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s);",
                        (username or email.split("@")[0].title(), email, hashed)
                    )
                    return {"id": cursor.lastrowid, "username": username, "email": email}, None
            finally:
                conn.close()

    # SQLite Fast Path
    conn = get_sqlite_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, password_hash FROM users WHERE email = ?;", (email,))
        row = cursor.fetchone()
        if row:
            dummy_hash = hash_password(f"oauth_user_{email}")
            if row["password_hash"] == dummy_hash:
                with conn:
                    cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?;", (hashed, row["id"]))
                return {"id": row["id"], "username": row["username"], "email": row["email"]}, None
            if not verify_password(password, row["password_hash"]):
                return None, "Incorrect password for this account. Please enter your existing password or use 'Forgot?'."
            return {"id": row["id"], "username": row["username"], "email": row["email"]}, None

        # Create new account
        with conn:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?);",
                (username or email.split("@")[0].title(), email, hashed)
            )
            return {"id": cursor.lastrowid, "username": username or email.split("@")[0].title(), "email": email}, None
    finally:
        conn.close()

def authenticate_user(email: str, password: str):
    """Verifies user login credentials with compulsory password."""
    email = email.strip().lower()
    if not email:
        return None, "Email address is required."
    if not password:
        return None, "Password is required."

    password = password.strip()
    hashed = hash_password(password)

    if MYSQL_ACTIVE:
        conn = get_mysql_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id, username, email, password_hash FROM users WHERE email = %s;", (email,))
                    user = cursor.fetchone()
                    if not user:
                        return None, "Account not found with this email. Please click 'Create Account' to register."
                    dummy_hash = hash_password(f"oauth_user_{email}")
                    if user["password_hash"] == dummy_hash:
                        # Upgrade account from legacy dummy oauth password
                        cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s;", (hashed, user["id"]))
                        return {"id": user["id"], "username": user["username"], "email": user["email"]}, None
                    if not verify_password(password, user["password_hash"]):
                        return None, "Incorrect password. Please try again or use 'Forgot?'."
                    return {"id": user["id"], "username": user["username"], "email": user["email"]}, None
            finally:
                conn.close()

    # SQLite Fast Path
    conn = get_sqlite_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, password_hash FROM users WHERE email = ?;", (email,))
        row = cursor.fetchone()
        if not row:
            return None, "Account not found with this email. Please click 'Create Account' to register."
        dummy_hash = hash_password(f"oauth_user_{email}")
        if row["password_hash"] == dummy_hash:
            # Upgrade account from legacy dummy oauth password
            with conn:
                cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?;", (hashed, row["id"]))
            return {"id": row["id"], "username": row["username"], "email": row["email"]}, None
        if not verify_password(password, row["password_hash"]):
            return None, "Incorrect password. Please try again or use 'Forgot?'."
        return {"id": row["id"], "username": row["username"], "email": row["email"]}, None
    finally:
        conn.close()

def reset_user_password(email: str, new_password: str):
    """Updates the user password hash."""
    email = email.strip().lower()
    if not email or not new_password or len(new_password.strip()) < 4:
        return False, "Valid email and new password (min 4 characters) are required."

    hashed = hash_password(new_password.strip())
    if MYSQL_ACTIVE:
        conn = get_mysql_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("UPDATE users SET password_hash = %s WHERE email = %s;", (hashed, email))
                    if cursor.rowcount > 0:
                        return True, None
                    return False, "No account found with this email."
            finally:
                conn.close()

    # SQLite Fast Path
    conn = get_sqlite_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password_hash = ? WHERE email = ?;", (hashed, email))
            if cursor.rowcount > 0:
                return True, None
            return False, "No account found with this email."
    finally:
        conn.close()

def get_user_by_email(email: str):
    """Retrieves user info by email."""
    email = email.strip().lower()
    if MYSQL_ACTIVE:
        conn = get_mysql_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id, username, email FROM users WHERE email = %s;", (email,))
                    return cursor.fetchone()
            finally:
                conn.close()

    # SQLite Fast Path
    conn = get_sqlite_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email FROM users WHERE email = ?;", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

# --- Chat History Functions ---

def save_chat_message(user_id: int | None, role: str, message: str):
    """Saves a message to chat history with explicit IST timestamp."""
    ist_time = get_current_ist_str()
    if MYSQL_ACTIVE:
        conn = get_mysql_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO chat_history (user_id, role, message, created_at) VALUES (%s, %s, %s, %s);",
                        (user_id, role, message, ist_time)
                    )
                return True
            except Exception:
                pass
            finally:
                conn.close()

    # SQLite Fast Path
    conn = get_sqlite_connection()
    try:
        with conn:
            conn.cursor().execute(
                "INSERT INTO chat_history (user_id, role, message, created_at) VALUES (?, ?, ?, ?);",
                (user_id, role, message, ist_time)
            )
        return True
    except Exception as e:
        print(f"[DB Error saving message]: {e}")
        return False
    finally:
        conn.close()

def get_chat_history(user_id: int | None, limit: int = 30):
    """Fetches recent chat history formatted in IST."""
    if MYSQL_ACTIVE:
        conn = get_mysql_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    if user_id:
                        cursor.execute(
                            "SELECT id, role, message, DATE_FORMAT(created_at, '%%h:%%i %%p') as created_at FROM chat_history WHERE user_id = %s ORDER BY id ASC LIMIT %s;",
                            (user_id, limit)
                        )
                    else:
                        cursor.execute(
                            "SELECT id, role, message, DATE_FORMAT(created_at, '%%h:%%i %%p') as created_at FROM chat_history WHERE user_id IS NULL ORDER BY id ASC LIMIT %s;",
                            (limit,)
                        )
                    return cursor.fetchall()
            finally:
                conn.close()

    # SQLite Fast Path
    conn = get_sqlite_connection()
    try:
        cursor = conn.cursor()
        if user_id:
            cursor.execute(
                "SELECT id, role, message, created_at FROM chat_history WHERE user_id = ? ORDER BY id ASC LIMIT ?;",
                (user_id, limit)
            )
        else:
            cursor.execute(
                "SELECT id, role, message, created_at FROM chat_history WHERE user_id IS NULL ORDER BY id ASC LIMIT ?;",
                (limit,)
            )
        rows = cursor.fetchall()
        result = []
        for r in rows:
            row_dict = dict(r)
            raw_time = row_dict.get("created_at")
            if raw_time and len(str(raw_time)) >= 16:
                try:
                    dt = datetime.strptime(str(raw_time)[:19], "%Y-%m-%d %H:%M:%S")
                    row_dict["created_at"] = dt.strftime("%I:%M %p")
                except Exception:
                    pass
            result.append(row_dict)
        return result
    finally:
        conn.close()

def clear_chat_history(user_id: int | None):
    """Deletes all messages for a specific user or anonymous user."""
    if MYSQL_ACTIVE:
        conn = get_mysql_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    if user_id:
                        cursor.execute("DELETE FROM chat_history WHERE user_id = %s;", (user_id,))
                    else:
                        cursor.execute("DELETE FROM chat_history WHERE user_id IS NULL;")
                return True
            finally:
                conn.close()

    # SQLite Fast Path
    conn = get_sqlite_connection()
    try:
        with conn:
            if user_id:
                conn.cursor().execute("DELETE FROM chat_history WHERE user_id = ?;", (user_id,))
            else:
                conn.cursor().execute("DELETE FROM chat_history WHERE user_id IS NULL;")
        return True
    except Exception as e:
        print(f"[DB Error clearing history]: {e}")
        return False
    finally:
        conn.close()
