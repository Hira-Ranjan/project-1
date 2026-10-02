import sqlite3

class Database:
    def __init__(self, db_name="vault.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Table for Master Password Metadata (salt and verification hash)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS master_meta (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                salt BLOB NOT NULL,
                verifier BLOB NOT NULL
            )
        ''')
        # Table for Encrypted Credentials
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                service TEXT NOT NULL,
                username TEXT NOT NULL,
                encrypted_password BLOB NOT NULL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                username TEXT NOT NULL,
                avatar_path TEXT NOT NULL DEFAULT ''
            )
        ''')
        self.conn.commit()

    def is_vault_initialized(self) -> bool:
        self.cursor.execute("SELECT COUNT(*) FROM master_meta")
        return self.cursor.fetchone()[0] > 0

    def save_master_meta(self, salt: bytes, verifier: bytes):
        self.cursor.execute("INSERT INTO master_meta (id, salt, verifier) VALUES (1, ?, ?)", (salt, verifier))
        self.conn.commit()

    def get_master_meta(self):
        self.cursor.execute("SELECT salt, verifier FROM master_meta WHERE id = 1")
        return self.cursor.fetchone()

    def add_credential(self, category, service, username, encrypted_password):
        self.cursor.execute(
            "INSERT INTO credentials (category, service, username, encrypted_password) VALUES (?, ?, ?, ?)",
            (category, service, username, encrypted_password)
        )
        self.conn.commit()

    def get_all_credentials(self):
        self.cursor.execute("SELECT id, category, service, username, encrypted_password FROM credentials")
        return self.cursor.fetchall()

    def delete_credential(self, cred_id):
        self.cursor.execute("DELETE FROM credentials WHERE id = ?", (cred_id,))
        self.conn.commit()

    def save_profile(self, username, avatar_path=""):
        self.cursor.execute(
            "INSERT OR REPLACE INTO profile (id, username, avatar_path) VALUES (1, ?, ?)",
            (username, avatar_path)
        )
        self.conn.commit()

    def get_profile(self):
        self.cursor.execute("SELECT username, avatar_path FROM profile WHERE id = 1")
        return self.cursor.fetchone()

    def get_category_counts(self):
        self.cursor.execute(
            "SELECT category, COUNT(*) FROM credentials GROUP BY category ORDER BY category"
        )
        return self.cursor.fetchall()