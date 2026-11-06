import os
import hashlib
import secrets
import sqlite3
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Try importing bcrypt for cryptographically salted password hashing
try:
    import bcrypt
except ImportError:
    bcrypt = None

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

# Helper functions to hash and verify passwords securely using bcrypt
def hash_password(password: str) -> str:
    """Hashes a password using cryptographically secure bcrypt with a randomly generated salt."""
    if bcrypt:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    # High-security standard PBKDF2 fallback if bcrypt library is not present
    salt = secrets.token_hex(16)
    return f"pbkdf2_sha256${salt}${hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies password using bcrypt, with transparent auto-migration from legacy SHA-256."""
    if not hashed_password or not plain_password:
        return False

    # Standard Bcrypt ($2a$, $2b$, $2y$)
    if hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
        if bcrypt:
            try:
                return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
            except Exception:
                return False
        return False

    # PBKDF2 fallback
    if hashed_password.startswith("pbkdf2_sha256$"):
        parts = hashed_password.split("$")
        if len(parts) == 3:
            _, salt, hash_val = parts
            computed = hashlib.pbkdf2_hmac('sha256', plain_password.encode(), salt.encode(), 100000).hex()
            return computed == hash_val

    # Backward compatibility with existing local accounts hashed via legacy SHA-256
    legacy_salt = "mini_project_secret_salt_2026"
    legacy_hash = hashlib.sha256((plain_password + legacy_salt).encode("utf-8")).hexdigest()
    return legacy_hash == hashed_password

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
                    CREATE TABLE IF NOT EXISTS password_resets (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        email VARCHAR(150) NOT NULL,
                        token_hash VARCHAR(255) NOT NULL,
                        expires_at DATETIME NOT NULL,
                        used TINYINT DEFAULT 0,
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
            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used INTEGER DEFAULT 0,
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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_resets_email ON password_resets(email);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_userid ON chat_history(user_id);")
    sqlite_conn.close()
    return True

# --- User Management Functions ---

def create_user(username: str, email: str, password: str):
    """Registers a new user with bcrypt-hashed password (minimum 8 characters required)."""
    email = email.strip().lower()
    if not email:
        return None, "Email address is required."
    if not password or len(password.strip()) < 8:
        return None, "Password must be at least 8 characters long."

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
            return None, "Email is already registered. Please sign in."
        with conn:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?);",
                (username or email.split("@")[0].title(), email, hashed)
            )
            return {"id": cursor.lastrowid, "username": username or email.split("@")[0].title(), "email": email}, None
    finally:
        conn.close()

def create_or_get_google_user(email: str, name: str, google_sub: str = ""):
    """
    Authenticates or creates a user verified by real Google OAuth 2.0 (Google Identity Services).
    No password is ever entered or collected on our site; a high-entropy random bcrypt hash protects the account.
    """
    email = email.strip().lower()
    if not email:
        return None, "Google verified email is required."

    name = name.strip() or email.split("@")[0].title()

    if MYSQL_ACTIVE:
        conn = get_mysql_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id, username, email FROM users WHERE email = %s;", (email,))
                    existing = cursor.fetchone()
                    if existing:
                        return {"id": existing["id"], "username": existing["username"], "email": existing["email"]}, None
                    
                    random_pwd_hash = hash_password(secrets.token_urlsafe(32))
                    cursor.execute(
                        "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s);",
                        (name, email, random_pwd_hash)
                    )
                    return {"id": cursor.lastrowid, "username": name, "email": email}, None
            finally:
                conn.close()

    # SQLite Fast Path
    conn = get_sqlite_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email FROM users WHERE email = ?;", (email,))
        row = cursor.fetchone()
        if row:
            return {"id": row["id"], "username": row["username"], "email": row["email"]}, None

        random_pwd_hash = hash_password(secrets.token_urlsafe(32))
        with conn:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?);",
                (name, email, random_pwd_hash)
            )
            return {"id": cursor.lastrowid, "username": name, "email": email}, None
    finally:
        conn.close()

def authenticate_user(email: str, password: str):
    """Verifies user login credentials and transparently upgrades legacy hashes to bcrypt."""
    email = email.strip().lower()
    if not email:
        return None, "Email address is required."
    if not password:
        return None, "Password is required."

    password = password.strip()

    if MYSQL_ACTIVE:
        conn = get_mysql_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id, username, email, password_hash FROM users WHERE email = %s;", (email,))
                    user = cursor.fetchone()
                    if not user:
                        return None, "Account not found with this email. Please click 'Create Account' to register."
                    
                    if not verify_password(password, user["password_hash"]):
                        return None, "Incorrect password. Please try again or use 'Forgot Password?'."
                    
                    # Transparently upgrade legacy SHA-256 hash to bcrypt on successful login
                    if not str(user["password_hash"]).startswith(("$2a$", "$2b$", "$2y$")):
                        new_bcrypt = hash_password(password)
                        cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s;", (new_bcrypt, user["id"]))

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
        
        if not verify_password(password, row["password_hash"]):
            return None, "Incorrect password. Please try again or use 'Forgot Password?'."

        # Transparently upgrade legacy SHA-256 hash to bcrypt on successful login
        if not str(row["password_hash"]).startswith(("$2a$", "$2b$", "$2y$")):
            new_bcrypt = hash_password(password)
            with conn:
                cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?;", (new_bcrypt, row["id"]))

        return {"id": row["id"], "username": row["username"], "email": row["email"]}, None
    finally:
        conn.close()

# --- Secure Token-Based Password Reset ---

def create_password_reset_code(email: str) -> tuple[str | None, str | None]:
    """
    Generates a cryptographically secure 6-digit verification code with 10-minute validity.
    Outputs to server console/audit log so only the genuine account owner / developer can reset.
    """
    email = email.strip().lower()
    if not email:
        return None, "Email address is required."

    user = get_user_by_email(email)
    if not user:
        return None, "No account is registered with this email address."

    # Cryptographically secure 6-digit integer code (100000 - 999999)
    code = str(secrets.randbelow(900000) + 100000)
    token_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    expires_at_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")

    if MYSQL_ACTIVE:
        conn = get_mysql_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO password_resets (email, token_hash, expires_at, used) VALUES (%s, %s, %s, 0);",
                        (email, token_hash, expires_at_str)
                    )
            finally:
                conn.close()
    else:
        conn = get_sqlite_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO password_resets (email, token_hash, expires_at, used) VALUES (?, ?, ?, 0);",
                    (email, token_hash, expires_at_str)
                )
        finally:
            conn.close()

    print(f"\n=================================================================")
    print(f"🔐 [SECURITY AUDIT] PASSWORD RESET CODE DISPATCHED")
    print(f"👉 Recipient:   {email}")
    print(f"👉 Reset Code:  {code}")
    print(f"👉 Valid For:   10 minutes (expires at {expires_at_str} UTC)")
    print(f"=================================================================\n")

    return code, None

def verify_and_reset_password(email: str, code: str, new_password: str) -> tuple[bool, str | None]:
    """
    Validates the 6-digit reset code and updates the password using bcrypt.
    Enforces a strict minimum of 8 characters and prevents unauthorized account takeover.
    """
    email = email.strip().lower()
    code = str(code).strip()
    new_password = new_password.strip()

    if not email:
        return False, "Email address is required."
    if not code:
        return False, "Verification code is required."
    if not new_password or len(new_password) < 8:
        return False, "New password must be at least 8 characters long."

    token_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    now_utc_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    if MYSQL_ACTIVE:
        conn = get_mysql_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM password_resets WHERE email = %s AND token_hash = %s AND used = 0 AND expires_at > %s ORDER BY id DESC LIMIT 1;",
                        (email, token_hash, now_utc_str)
                    )
                    row = cursor.fetchone()
                    if not row:
                        return False, "Invalid or expired verification code. Please request a new code."
                    
                    matched_id = row["id"]
                    new_hash = hash_password(new_password)
                    cursor.execute("UPDATE users SET password_hash = %s WHERE email = %s;", (new_hash, email))
                    cursor.execute("UPDATE password_resets SET used = 1 WHERE id = %s;", (matched_id,))
                    return True, None
            finally:
                conn.close()
    else:
        conn = get_sqlite_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM password_resets WHERE email = ? AND token_hash = ? AND used = 0 AND expires_at > ? ORDER BY id DESC LIMIT 1;",
                (email, token_hash, now_utc_str)
            )
            row = cursor.fetchone()
            if not row:
                return False, "Invalid or expired verification code. Please request a new code."

            matched_id = row["id"]
            new_hash = hash_password(new_password)
            with conn:
                cursor.execute("UPDATE users SET password_hash = ? WHERE email = ?;", (new_hash, email))
                cursor.execute("UPDATE password_resets SET used = 1 WHERE id = ?;", (matched_id,))
            return True, None
        finally:
            conn.close()

    return False, "Database connection error."

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
        if row:
            return {"id": row["id"], "username": row["username"], "email": row["email"]}
        return None
    finally:
        conn.close()

# --- Chat History Functions ---

def save_chat_message(user_id: int | None, role: str, message: str):
    """Appends a chat message to history."""
    if role not in ("user", "assistant"):
        return False
    if not message:
        return False

    if MYSQL_ACTIVE:
        conn = get_mysql_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO chat_history (user_id, role, message) VALUES (%s, %s, %s);",
                        (user_id, role, message)
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
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO chat_history (user_id, role, message) VALUES (?, ?, ?);",
                (user_id, role, message)
            )
        return True
    except Exception:
        return False
    finally:
        conn.close()

def get_chat_history(user_id: int | None = None, limit: int = 50):
    """Retrieves recent chat history."""
    if MYSQL_ACTIVE:
        conn = get_mysql_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    if user_id:
                        cursor.execute(
                            "SELECT id, user_id, role, message, created_at FROM chat_history WHERE user_id = %s ORDER BY id ASC LIMIT %s;",
                            (user_id, limit)
                        )
                    else:
                        cursor.execute(
                            "SELECT id, user_id, role, message, created_at FROM chat_history WHERE user_id IS NULL ORDER BY id ASC LIMIT %s;",
                            (limit,)
                        )
                    return cursor.fetchall() or []
            except Exception:
                pass
            finally:
                conn.close()

    # SQLite Fast Path
    conn = get_sqlite_connection()
    try:
        cursor = conn.cursor()
        if user_id:
            cursor.execute(
                "SELECT id, user_id, role, message, created_at FROM chat_history WHERE user_id = ? ORDER BY id ASC LIMIT ?;",
                (user_id, limit)
            )
        else:
            cursor.execute(
                "SELECT id, user_id, role, message, created_at FROM chat_history WHERE user_id IS NULL ORDER BY id ASC LIMIT ?;",
                (limit,)
            )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def clear_chat_history(user_id: int | None = None) -> bool:
    """Clears conversation history for the given user."""
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
            except Exception:
                pass
            finally:
                conn.close()

    # SQLite Fast Path
    conn = get_sqlite_connection()
    try:
        with conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute("DELETE FROM chat_history WHERE user_id = ?;", (user_id,))
            else:
                cursor.execute("DELETE FROM chat_history WHERE user_id IS NULL;")
        return True
    except Exception:
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
