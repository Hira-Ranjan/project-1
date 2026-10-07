import sqlite3

LEGACY_EMAIL = "legacy@local"  # Used only to migrate a vault created before email accounts existed


class Database:
    def __init__(self, db_name="vault.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.account_id = None  # Currently unlocked account (None while locked)
        self.create_tables()

    def create_tables(self):
        # One row per account: email + its own salt / verification hash + profile info
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                username TEXT NOT NULL,
                avatar_path TEXT NOT NULL DEFAULT '',
                salt BLOB NOT NULL,
                verifier BLOB NOT NULL
            )
        ''')
        # Table for Encrypted Credentials (each belongs to an account)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL DEFAULT 0,
                category TEXT NOT NULL,
                service TEXT NOT NULL,
                username TEXT NOT NULL,
                encrypted_password BLOB NOT NULL
            )
        ''')
        # Simple key/value app settings (e.g. auto-lock timeout)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        # Upgrade an older vault.db that has no account_id column
        cols = [r[1] for r in self.cursor.execute("PRAGMA table_info(credentials)").fetchall()]
        if "account_id" not in cols:
            self.cursor.execute("ALTER TABLE credentials ADD COLUMN account_id INTEGER NOT NULL DEFAULT 0")
        self._migrate_legacy_vault()
        self.conn.commit()

    def _migrate_legacy_vault(self):
        """Moves the old single-vault data (master_meta + profile) into the accounts table."""
        tables = {r[0] for r in self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "master_meta" not in tables:
            return
        if self.cursor.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] > 0:
            return
        meta = self.cursor.execute("SELECT salt, verifier FROM master_meta WHERE id = 1").fetchone()
        if not meta:
            return
        profile = None
        if "profile" in tables:
            profile = self.cursor.execute("SELECT username, avatar_path FROM profile WHERE id = 1").fetchone()
        username, avatar = profile or ("User", "")
        self.cursor.execute(
            "INSERT INTO accounts (email, username, avatar_path, salt, verifier) VALUES (?, ?, ?, ?, ?)",
            (LEGACY_EMAIL, username, avatar, meta[0], meta[1])
        )
        new_id = self.cursor.lastrowid
        self.cursor.execute("UPDATE credentials SET account_id = ? WHERE account_id = 0", (new_id,))

    # ---------- Accounts ----------
    def is_vault_initialized(self) -> bool:
        """True if at least one account exists on this device."""
        self.cursor.execute("SELECT COUNT(*) FROM accounts")
        return self.cursor.fetchone()[0] > 0

    def create_account(self, email, username, salt: bytes, verifier: bytes):
        """Returns the new account id, or None if the email is already registered."""
        try:
            self.cursor.execute(
                "INSERT INTO accounts (email, username, salt, verifier) VALUES (?, ?, ?, ?)",
                (email, username, salt, verifier)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_account_by_email(self, email):
        """Returns (id, salt, verifier) or None."""
        self.cursor.execute("SELECT id, salt, verifier FROM accounts WHERE email = ?", (email,))
        return self.cursor.fetchone()

    def get_accounts(self):
        """Returns [(id, email, username, avatar_path), ...] for the account switcher."""
        self.cursor.execute("SELECT id, email, username, avatar_path FROM accounts ORDER BY username COLLATE NOCASE")
        return self.cursor.fetchall()

    # ---------- Credentials (always scoped to the current account) ----------
    def add_credential(self, category, service, username, encrypted_password):
        self.cursor.execute(
            "INSERT INTO credentials (account_id, category, service, username, encrypted_password) VALUES (?, ?, ?, ?, ?)",
            (self.account_id, category, service, username, encrypted_password)
        )
        self.conn.commit()

    def get_all_credentials(self):
        self.cursor.execute(
            "SELECT id, category, service, username, encrypted_password FROM credentials WHERE account_id = ?",
            (self.account_id,)
        )
        return self.cursor.fetchall()

    def delete_credential(self, cred_id):
        self.cursor.execute("DELETE FROM credentials WHERE id = ? AND account_id = ?", (cred_id, self.account_id))
        self.conn.commit()

    # ---------- Profile (current account) ----------
    def save_profile(self, username, avatar_path=""):
        self.cursor.execute(
            "UPDATE accounts SET username = ?, avatar_path = ? WHERE id = ?",
            (username, avatar_path, self.account_id)
        )
        self.conn.commit()

    def get_profile(self):
        self.cursor.execute("SELECT username, avatar_path FROM accounts WHERE id = ?", (self.account_id,))
        return self.cursor.fetchone()

    def get_category_counts(self):
        self.cursor.execute(
            "SELECT category, COUNT(*) FROM credentials WHERE account_id = ? GROUP BY category ORDER BY category",
            (self.account_id,)
        )
        return self.cursor.fetchall()

    # ---------- Settings (device-wide) ----------
    def get_setting(self, key, default=None):
        self.cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = self.cursor.fetchone()
        return row[0] if row else default

    def set_setting(self, key, value):
        self.cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        self.conn.commit()
    def update_credential(self, cred_id, category, service, username, encrypted_password):
        """Updates an existing credential belonging to the active account."""
        self.cursor.execute(
            "UPDATE credentials SET category = ?, service = ?, username = ?, encrypted_password = ? "
            "WHERE id = ? AND account_id = ?",
            (category, service, username, encrypted_password, cred_id, self.account_id)
        )
        self.conn.commit()