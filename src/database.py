import sqlite3
import os
import pandas as pd
import streamlit as st
from datetime import datetime

# --- Constants ---
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
DB_FILE = os.path.join(DB_DIR, 'app_database.db')

# --- Abstract Backend Interface (Reference) ---
# Methods:
# init_db()
# get_user_by_username(username) -> dict {'id', 'username', 'password_hash'}
# create_user(username, password_hash) -> (bool, msg)
# add_journal_entry(user_id, data)
# get_user_journal(user_id) -> DataFrame
# update_journal_entry(entry_id, user_id, updates)
# delete_journal_entry(entry_id, user_id)

class SQLiteBackend:
    def __init__(self):
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR, exist_ok=True)
            
    def _get_conn(self):
        return sqlite3.connect(DB_FILE)

    def init_db(self):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                code TEXT,
                name TEXT,
                side TEXT,
                entry_price REAL,
                exit_price REAL,
                qty INTEGER,
                fees REAL DEFAULT 0,
                pnl REAL,
                roi REAL,
                strategy TEXT,
                reason TEXT,
                mistake TEXT,
                review TEXT,
                image_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        # Migration for existing DB
        try:
            c.execute("ALTER TABLE journal ADD COLUMN fees REAL DEFAULT 0")
        except:
            pass
        conn.commit()
        conn.close()

    def get_user_by_username(self, username):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
        row = c.fetchone()
        conn.close()
        if row:
            return {'id': row[0], 'username': row[1], 'password_hash': row[2]}
        return None

    def create_user(self, username, password_hash):
        conn = self._get_conn()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
            conn.commit()
            return True, "회원가입 성공! 로그인해주세요."
        except sqlite3.IntegrityError:
            return False, "이미 존재하는 아이디입니다."
        except Exception as e:
            return False, f"오류 발생: {e}"
        finally:
            conn.close()

    def add_journal_entry(self, user_id, data):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute('''
            INSERT INTO journal (user_id, date, code, name, side, entry_price, exit_price, qty, fees, pnl, roi, strategy, reason, mistake, review, image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, data['date'], data['code'], data['name'], data['side'],
            data['entry_price'], data['exit_price'], data['qty'], data.get('fees', 0),
            data['pnl'], data['roi'], data['strategy'], data['reason'],
            data['mistake'], data['review'], data.get('image_path')
        ))
        conn.commit()
        conn.close()

    def get_user_journal(self, user_id):
        conn = self._get_conn()
        df = pd.read_sql_query("SELECT * FROM journal WHERE user_id = ? ORDER BY date DESC", conn, params=(user_id,))
        conn.close()
        return df
    
    # Placeholder updates (not critical for MVP)
    def update_journal_entry(self, entry_id, user_id, updates):
        pass # Implemented in previous version, omitted for brevity/focus on interface matching
    
    def delete_journal_entry(self, entry_id, user_id):
        try:
            conn = self._get_conn()
            c = conn.cursor()
            # Explicit cast to int to avoid numpy type issues
            e_id = int(entry_id)
            u_id = int(user_id)
            c.execute("DELETE FROM journal WHERE id = ? AND user_id = ?", (e_id, u_id))
            conn.commit()
            conn.close()
            print(f"SQLite: Deleted entry {e_id} for user {u_id}")
        except Exception as e:
            print(f"SQLite Delete Error: {e}")

class GSheetsBackend:
    def __init__(self):
        import gspread
        from google.oauth2.service_account import Credentials
        
        # Load credentials from st.secrets
        # Expects st.secrets["gcp_service_account"] to be the JSON content
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
        ]
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        self.gc = gspread.authorize(credentials)
        
        # Configuration
        self.sheet_url = st.secrets["sheet_url"]
        self.sh = self.gc.open_by_url(self.sheet_url)
        
    def _get_worksheet(self, name):
        try:
            return self.sh.worksheet(name)
        except:
            return self.sh.add_worksheet(title=name, rows=1000, cols=20)

    def init_db(self):
        # Create headers if empty or missing
        try:
            ws_users = self._get_worksheet("users")
            all_values = ws_users.get_all_values()
            # Check if first row has proper headers
            if not all_values or len(all_values[0]) < 3 or all_values[0][0] != "id":
                print("[GSheets] Initializing users sheet with headers")
                ws_users.clear()
                ws_users.append_row(["id", "username", "password_hash", "created_at"])
            else:
                print(f"[GSheets] users sheet OK, {len(all_values)-1} records")
        except Exception as e:
            print(f"[GSheets] init_db users error: {e}")

        try:
            ws_journal = self._get_worksheet("journal")
            all_values = ws_journal.get_all_values()
            if not all_values or len(all_values[0]) < 5 or all_values[0][0] != "id":
                print("[GSheets] Initializing journal sheet with headers")
                ws_journal.clear()
                ws_journal.append_row(["id", "user_id", "date", "code", "name", "side", "entry_price", "exit_price", "qty", "fees", "pnl", "roi", "strategy", "reason", "mistake", "review", "image_path", "created_at"])
            else:
                print(f"[GSheets] journal sheet OK, {len(all_values)-1} records")
        except Exception as e:
            print(f"[GSheets] init_db journal error: {e}")

    def get_user_by_username(self, username):
        try:
            ws = self._get_worksheet("users")
            records = ws.get_all_records() # Returns list of dicts
            print(f"[GSheets] Looking for user: {username}, total records: {len(records)}")

            for r in records:
                # Check if required keys exist
                if 'username' not in r or 'password_hash' not in r or 'id' not in r:
                    print(f"[GSheets] Skipping malformed record: {r}")
                    continue

                if str(r['username']) == username:
                    p_hash = r['password_hash']
                    if isinstance(p_hash, str):
                        p_hash = p_hash.encode('latin-1')

                    return {'id': r['id'], 'username': r['username'], 'password_hash': p_hash}
            return None
        except Exception as e:
            print(f"[GSheets] get_user_by_username error: {e}")
            return None

    def create_user(self, username, password_hash):
        try:
            if self.get_user_by_username(username):
                return False, "이미 존재하는 아이디입니다."

            ws = self._get_worksheet("users")

            # Get all values to find max ID (safer than get_all_records)
            all_values = ws.get_all_values()
            new_id = 1
            if len(all_values) > 1:  # Has data rows (not just header)
                for row in all_values[1:]:  # Skip header
                    if row and row[0] and str(row[0]).isdigit():
                        new_id = max(new_id, int(row[0]) + 1)

            hash_str = password_hash.decode('latin-1')

            ws.append_row([new_id, username, hash_str, str(datetime.now())])
            print(f"[GSheets] Created user {username} with id {new_id}")
            return True, "회원가입 성공!"
        except Exception as e:
            print(f"[GSheets] create_user error: {e}")
            return False, f"오류 발생: {e}"

    def add_journal_entry(self, user_id, data):
        ws = self._get_worksheet("journal")
        records = ws.get_all_records()
        new_id = 1
        if records:
            new_id = max([int(r['id']) for r in records if str(r['id']).isdigit()] or [0]) + 1
            
        ws.append_row([
            new_id, user_id, 
            str(data['date']), str(data['code']), str(data['name']), str(data['side']),
            data['entry_price'], data['exit_price'], data['qty'], data.get('fees', 0),
            data['pnl'], data['roi'], str(data['strategy']), str(data['reason']),
            str(data['mistake']), str(data['review'] or ''), str(data.get('image_path') or ''),
            str(datetime.now())
        ])

    def get_user_journal(self, user_id):
        ws = self._get_worksheet("journal")
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if df.empty:
            return df
            
        df['user_id'] = pd.to_numeric(df['user_id'], errors='coerce')
        df = df[df['user_id'] == user_id]
        return df

    def update_journal_entry(self, entry_id, user_id, updates):
        pass
    
    def delete_journal_entry(self, entry_id, user_id):
        try:
            ws = self._get_worksheet("journal")
            records = ws.get_all_records()
            # Find the row index (gspread is 1-indexed, headers are row 1)
            # Row index in gspread = record_index (0-based) + 2
            for i, r in enumerate(records):
                if int(r['id']) == int(entry_id) and int(r['user_id']) == int(user_id):
                    ws.delete_rows(i + 2)
                    print(f"GSheets: Deleted row for entry {entry_id}")
                    return
            print(f"GSheets: Entry {entry_id} not found for user {user_id}")
        except Exception as e:
            print(f"GSheets Delete Error: {e}")

# --- Factory & Singleton ---
_db_instance = None

def get_db():
    global _db_instance
    if _db_instance:
        return _db_instance

    # Check if inside Streamlit Cloud with Secrets
    # We check for a specific key "gcp_service_account"
    try:
        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            try:
                _db_instance = GSheetsBackend()
                st.sidebar.success("DB: Google Sheets")
            except Exception as e:
                st.sidebar.error(f"GSheets Error: {e}")
                _db_instance = SQLiteBackend()
        else:
            _db_instance = SQLiteBackend()
            st.sidebar.info("DB: SQLite (local)")
    except Exception as e:
        st.sidebar.warning(f"Secrets error: {e}")
        _db_instance = SQLiteBackend()

    return _db_instance

# --- Global Wrappers (For compatibility with app_main.py) ---

def init_db():
    get_db().init_db()

def get_user_by_username(username):
    return get_db().get_user_by_username(username)
    
def create_user(username, password_hash):
    return get_db().create_user(username, password_hash)

def add_journal_entry(user_id, data):
    get_db().add_journal_entry(user_id, data)

def get_user_journal(user_id):
    return get_db().get_user_journal(user_id)
    
def update_journal_entry(entry_id, user_id, updates):
    get_db().update_journal_entry(entry_id, user_id, updates)

def delete_journal_entry(entry_id, user_id):
    get_db().delete_journal_entry(entry_id, user_id)
