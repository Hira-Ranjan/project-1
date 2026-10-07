import customtkinter as ctk
import random
import string
import os
import re
import time
import tkinter as tk
import pyperclip
from tkinter import filedialog, messagebox
from PIL import Image, ImageDraw, ImageOps


from database import Database
import crypto_utils

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

_rng = random.SystemRandom()  # cryptographically secure RNG for generated passwords
AUTO_LOCK_OPTIONS = {"1 minute": 1, "2 minutes": 2, "5 minutes": 5, "10 minutes": 10,
                     "15 minutes": 15, "30 minutes": 30, "Never": 0}
DEFAULT_AUTO_LOCK_MINUTES = 5
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AddEditCredentialModal(ctk.CTkToplevel):
    """Modal popup for adding a new encrypted credential."""
    def __init__(self, parent, on_save_callback, record=None):
        super().__init__(parent)
        self.transient(parent)
        self.title("Edit Credential" if record else "Add New Credential")
        self.geometry("450x500")
        self.resizable(False, False)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.close)

        self.on_save_callback = on_save_callback
        self.record = record

        # Center popup on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (450 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (500 // 2)
        self.geometry(f"+{x}+{y}")

        ctk.CTkLabel(self, text="Edit Credential" if record else "Add New Credential", font=("Arial", 18, "bold")).pack(pady=(20, 15))

        form_frame = ctk.CTkFrame(self, fg_color="transparent")
        form_frame.pack(fill="both", expand=True, padx=30)

        # Category
        ctk.CTkLabel(form_frame, text="Category:", anchor="w").pack(fill="x", pady=(5, 2))
        self.cat_menu = ctk.CTkOptionMenu(form_frame, values=["Login", "Cards", "Secure Note", "Academic"])
        self.cat_menu.pack(fill="x", pady=(0, 10))

        # Service
        ctk.CTkLabel(form_frame, text="Service Name:", anchor="w").pack(fill="x", pady=(5, 2))
        self.service_entry = ctk.CTkEntry(form_frame, placeholder_text="e.g., RUET Portal, GitHub")
        self.service_entry.pack(fill="x", pady=(0, 10))

        # Username
        ctk.CTkLabel(form_frame, text="Username / Email:", anchor="w").pack(fill="x", pady=(5, 2))
        self.user_entry = ctk.CTkEntry(form_frame, placeholder_text="e.g., student_id, user@gmail.com")
        self.user_entry.pack(fill="x", pady=(0, 10))

        # Password
        ctk.CTkLabel(form_frame, text="Password:", anchor="w").pack(fill="x", pady=(5, 2))
        pass_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        pass_frame.pack(fill="x", pady=(0, 5))
        
        self.pass_entry = ctk.CTkEntry(pass_frame, show="*")
        self.pass_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.show_pass_btn = ctk.CTkButton(pass_frame, text="👁", width=40, command=self.toggle_password)
        self.show_pass_btn.pack(side="right")

        ctk.CTkButton(pass_frame, text="Generate", width=85, command=self.open_generator).pack(side="right", padx=(0, 5))

        self.error_label = ctk.CTkLabel(form_frame, text="", text_color="#FF4D4D")
        self.error_label.pack(pady=5)

        if record:
            self.cat_menu.set(record["category"])
            self.service_entry.insert(0, record["service"])
            self.user_entry.insert(0, record["username"])
            self.pass_entry.insert(0, record["password"])

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=15)

        ctk.CTkButton(btn_frame, text="Cancel", fg_color="#555555", hover_color="#333333", width=110, command=self.close).pack(side="left")
        ctk.CTkButton(btn_frame, text="Update Entry" if record else "Save Entry", width=110, command=self.save_data).pack(side="right")

        for entry in (self.service_entry, self.user_entry, self.pass_entry):
            entry.bind("<Return>", lambda e: self.save_data())
        self.after(100, lambda: PasswordManagerApp.safe_focus(self.service_entry))

    def close(self):
        self.grab_release()
        self.destroy()
        if self.master.winfo_exists():
            self.master.grab_set()
            self.master.focus_set()

    def toggle_password(self):
        if self.pass_entry.cget("show") == "*":
            self.pass_entry.configure(show="")
        else:
            self.pass_entry.configure(show="*")

    def open_generator(self):
        PasswordGeneratorModal(self, on_generated=self.use_generated_password)

    def use_generated_password(self, password):
        self.pass_entry.delete(0, "end")
        self.pass_entry.insert(0, password)
        self.pass_entry.configure(show="*")

    def save_data(self):
        cat = self.cat_menu.get()
        service = self.service_entry.get().strip()
        user = self.user_entry.get().strip()
        pwd = self.pass_entry.get().strip()

        if not service or not pwd:
            self.error_label.configure(text="Service and Password are required!")
            return

        self.on_save_callback(cat, service, user, pwd, self.record["id"] if self.record else None)
        self.close()


class PasswordGeneratorModal(ctk.CTkToplevel):
    """Modal utility for generating random passwords."""
    def __init__(self, parent, on_generated=None):
        super().__init__(parent)
        self.transient(parent)
        self.title("Password Generator")
        self.geometry("400x380")
        self.resizable(False, False)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.on_generated = on_generated

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (400 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (380 // 2)
        self.geometry(f"+{x}+{y}")

        ctk.CTkLabel(self, text="Password Generator", font=("Arial", 18, "bold")).pack(pady=(20, 10))

        self.output_entry = ctk.CTkEntry(self, font=("Courier", 16, "bold"), justify="center", height=40)
        self.output_entry.pack(fill="x", padx=30, pady=10)

        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=30, pady=10)

        length_row = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        length_row.pack(fill="x")
        ctk.CTkLabel(length_row, text="Length:", anchor="w").pack(side="left")
        self.length_entry = ctk.CTkEntry(length_row, width=70, justify="center")
        self.length_entry.insert(0, "16")
        self.length_entry.pack(side="right")
        self.length_entry.bind("<Return>", self.update_length_from_entry)
        self.length_entry.bind("<FocusOut>", self.update_length_from_entry)
        self.slider = ctk.CTkSlider(ctrl_frame, from_=8, to=32, number_of_steps=24, command=self.update_length)
        self.slider.set(16)
        self.slider.pack(fill="x", pady=(0, 15))

        self.symbols_var = ctk.BooleanVar(value=True)
        self.numbers_var = ctk.BooleanVar(value=True)

        ctk.CTkSwitch(ctrl_frame, text="Include Special Symbols (@#$%)", variable=self.symbols_var, command=self.generate).pack(anchor="w", pady=4)
        ctk.CTkSwitch(ctrl_frame, text="Include Numbers (0-9)", variable=self.numbers_var, command=self.generate).pack(anchor="w", pady=4)

        symbols_row = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        symbols_row.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(symbols_row, text="Minimum special symbols:").pack(side="left")
        self.min_symbols_entry = ctk.CTkEntry(symbols_row, width=70, justify="center")
        self.min_symbols_entry.insert(0, "1")
        self.min_symbols_entry.pack(side="right")
        self.min_symbols_entry.bind("<Return>", self.update_min_symbols)
        self.min_symbols_entry.bind("<FocusOut>", self.update_min_symbols)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=20)

        ctk.CTkButton(btn_frame, text="Generate", width=150, command=self.generate).pack(side="left")
        ctk.CTkButton(btn_frame, text="Copy & Close", fg_color="#2FA572", hover_color="#1E704C", width=150, command=self.copy_and_close).pack(side="right")

        self.generate()

    def update_length(self, value):
        length = int(value)
        self.length_entry.delete(0, "end")
        self.length_entry.insert(0, str(length))
        self.generate()

    def update_length_from_entry(self, event=None):
        try:
            length = max(8, min(32, int(self.length_entry.get())))
        except ValueError:
            length = 16
        self.slider.set(length)
        self.length_entry.delete(0, "end")
        self.length_entry.insert(0, str(length))
        self.generate()

    def update_min_symbols(self, event=None):
        try:
            minimum = int(self.min_symbols_entry.get())
        except ValueError:
            minimum = 1
        maximum = int(self.length_entry.get())
        minimum = max(0, min(maximum, minimum)) if self.symbols_var.get() else 0
        self.min_symbols_entry.delete(0, "end")
        self.min_symbols_entry.insert(0, str(minimum))
        self.generate()

    def generate(self):
        chars = string.ascii_letters
        if self.numbers_var.get():
            chars += string.digits
        symbols = "!@#$%^&*()_+-="
        if self.symbols_var.get():
            chars += symbols

        try:
            length = max(8, min(32, int(self.length_entry.get())))
        except ValueError:
            length = 16
        try:
            minimum_symbols = int(self.min_symbols_entry.get())
        except ValueError:
            minimum_symbols = 1
        minimum_symbols = max(0, min(length, minimum_symbols)) if self.symbols_var.get() else 0

        password_chars = [_rng.choice(symbols) for _ in range(minimum_symbols)]
        password_chars.extend(_rng.choice(chars) for _ in range(length - minimum_symbols))
        _rng.shuffle(password_chars)
        pwd = "".join(password_chars)
        
        self.output_entry.delete(0, "end")
        self.output_entry.insert(0, pwd)

    def copy_and_close(self):
        password = self.output_entry.get()
        pyperclip.copy(password)
        if self.on_generated:
            self.on_generated(password)
        self.close()

    def close(self):
        self.grab_release()
        self.destroy()
        if self.master.winfo_exists():
            self.master.focus_set()


class PasswordManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__(className="LocalVault")

        self.tk.call("tk", "appname", "local-vault")
        self.title("Local Vault Password Manager")
        self.geometry("900x600")
        self.resizable(False, False)
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 900) // 2
        y = (self.winfo_screenheight() - 600) // 2
        self.geometry(f"900x600+{x}+{y}")

        # Database & Key State
        self.db = Database()
        self.master_key = None  # Ephemeral 256-bit key kept in RAM while unlocked
        self.current_email = ""  # Email of the account that is (or was last) logged in
        self.remembered_email = self.db.get_setting("remembered_email", "") or ""
        self._status_after_id = None     # pending footer-message reset
        self._last_activity = time.monotonic()  # last mouse/keyboard activity (for auto-lock)
        try:
            self.auto_lock_minutes = int(self.db.get_setting("auto_lock_minutes", DEFAULT_AUTO_LOCK_MINUTES))
        except ValueError:
            self.auto_lock_minutes = DEFAULT_AUTO_LOCK_MINUTES
        self._clipboard_after_id = None  # pending clipboard auto-clear

        self.current_category_filter = "All"
        self.current_search_query = ""

        # Any mouse/keyboard activity (in any window or popup) resets the inactivity timer
        for sequence in ("<Motion>", "<KeyPress>", "<ButtonPress>", "<MouseWheel>"):
            self.bind_all(sequence, self._on_activity, add="+")
        self.after(1000, self._check_inactivity)

        # Launch appropriate screen
        self.show_auth_screen()

    def show_auth_screen(self, mode=None, prefill_email=None, notice=""):
        """Renders Create Account or Login view. mode: 'create' | 'login' (auto if None)."""
        for widget in self.winfo_children():
            widget.destroy()

        self.master_key = None  # Clear key from RAM when locked
        self.db.account_id = None
        self.current_category_filter = "All"
        self.current_search_query = ""
        if self._status_after_id:
            self.after_cancel(self._status_after_id)
            self._status_after_id = None

        has_accounts = self.db.is_vault_initialized()
        if mode is None:
            mode = "login" if has_accounts else "create"
        if prefill_email is None:
            prefill_email = self.current_email or self.remembered_email

        if mode == "create":
            auth_card = ctk.CTkFrame(self, width=740, height=530, corner_radius=15)
        else:
            remembered = bool(prefill_email) and prefill_email == self.remembered_email
            auth_card = ctk.CTkFrame(self, width=420, height=390 if remembered else 450, corner_radius=15)
        auth_card.pack_propagate(False)
        auth_card.place(relx=0.5, rely=0.5, anchor="center")

        if mode == "create":
            # CREATE ACCOUNT (first time, or adding another account on this device)
            ctk.CTkLabel(auth_card, text="Create Account", font=("Arial", 22, "bold")).pack(pady=(25, 4))
            ctk.CTkLabel(auth_card, text="Your master password encrypts everything in this vault, so choose it carefully.",
                         text_color="gray").pack(pady=(0, 14))

            body = ctk.CTkFrame(auth_card, fg_color="transparent")
            body.pack(padx=30, fill="x")

            # Left: form
            form = ctk.CTkFrame(body, fg_color="transparent")
            form.pack(side="left", anchor="n")

            self.setup_email = ctk.CTkEntry(form, placeholder_text="Email...", width=300, height=38)
            self.setup_email.pack(pady=6)

            self.setup_username = ctk.CTkEntry(form, placeholder_text="Username...", width=300, height=38)
            self.setup_username.pack(pady=6)

            pass_row = ctk.CTkFrame(form, fg_color="transparent")
            pass_row.pack(pady=6)
            self.setup_pass = ctk.CTkEntry(pass_row, placeholder_text="New Master Password...", show="*", width=252, height=38)
            self.setup_pass.pack(side="left")
            ctk.CTkButton(pass_row, text="👁", width=40, height=38,
                          command=lambda: self.toggle_master_visibility(self.setup_pass, self.confirm_pass)).pack(side="left", padx=(8, 0))

            self.confirm_pass = ctk.CTkEntry(form, placeholder_text="Confirm Master Password...", show="*", width=300, height=38)
            self.confirm_pass.pack(pady=6)

            self.remember_email_var = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(
                form,
                text="Remember this email on this device",
                variable=self.remember_email_var
            ).pack(anchor="w", pady=(2, 6))

            # Right: live strength meter + requirements checklist
            panel = ctk.CTkFrame(body, fg_color="#242424", corner_radius=10)
            panel.pack(side="right", fill="both", expand=True, padx=(20, 0))

            ctk.CTkLabel(panel, text="Password strength", font=("Arial", 13, "bold"), anchor="w").pack(fill="x", padx=15, pady=(12, 4))
            self.strength_bar = ctk.CTkProgressBar(panel, height=8)
            self.strength_bar.set(0)
            self.strength_bar.pack(fill="x", padx=15)
            self.strength_label = ctk.CTkLabel(panel, text="Start typing a password", text_color="gray", anchor="w", font=("Arial", 12))
            self.strength_label.pack(fill="x", padx=15, pady=(4, 8))

            self.rule_labels = {}
            rule_defs = [(k, d) for k, d, _ in crypto_utils.check_password_strength("")["rules"]]
            rule_defs.append(("match", "Both passwords match"))
            for key, desc in rule_defs:
                lbl = ctk.CTkLabel(panel, text=f"○  {desc}", text_color="gray", anchor="w", font=("Arial", 12))
                lbl.pack(fill="x", padx=15, pady=2)
                self.rule_labels[key] = (lbl, desc)
            ctk.CTkLabel(panel, text="Tip: a longer passphrase is stronger.", text_color="gray",
                         anchor="w", font=("Arial", 11)).pack(fill="x", padx=15, pady=(6, 10))

            self.error_label = ctk.CTkLabel(auth_card, text="", text_color="#FF4D4D")
            self.error_label.pack(pady=(10, 4))

            self.setup_btn = ctk.CTkButton(auth_card, text="Create Account & Continue", width=300, height=40,
                                           fg_color="#2FA572", hover_color="#1E704C", state="disabled", command=self.handle_setup)
            self.setup_btn.pack(pady=6)

            if has_accounts:
                ctk.CTkButton(auth_card, text="← Back to login", width=300, fg_color="transparent", text_color="#3B8ED0",
                              hover_color="#2B2B2B", command=lambda: self.show_auth_screen(mode="login")).pack()

            for entry in (self.setup_email, self.setup_username, self.setup_pass, self.confirm_pass):
                entry.bind("<Return>", lambda e: self.handle_setup())
            self.setup_pass.bind("<KeyRelease>", self.update_strength_meter)
            self.confirm_pass.bind("<KeyRelease>", self.update_strength_meter)
            self.update_strength_meter()
            self.after(100, lambda: self.safe_focus(self.setup_email))

        else:
            # RETURNING USER LOGIN
            remembered = bool(prefill_email) and prefill_email == self.remembered_email
            if remembered:
                ctk.CTkLabel(auth_card, text="Welcome Back", font=("Arial", 22, "bold")).pack(pady=(40, 5))
                ctk.CTkLabel(auth_card, text=f"Unlock vault for {prefill_email}", text_color="gray").pack(pady=(0, 20))

                pass_row = ctk.CTkFrame(auth_card, fg_color="transparent")
                pass_row.pack(pady=10)
                self.master_pass_entry = ctk.CTkEntry(pass_row, placeholder_text="Master Password...", show="*", width=252, height=40)
                self.master_pass_entry.pack(side="left")
                self.master_pass_entry.bind("<Return>", lambda e: self.handle_login())
                ctk.CTkButton(pass_row, text="👁", width=40, height=40,
                              command=lambda: self.toggle_master_visibility(self.master_pass_entry)).pack(side="left", padx=(8, 0))

                ctk.CTkButton(auth_card, text="Unlock Vault", width=300, height=40, command=self.handle_login).pack(pady=15)

                self.error_label = ctk.CTkLabel(auth_card, text="", text_color="#FF4D4D")
                self.error_label.pack(pady=5)

                ctk.CTkButton(auth_card, text="Use another account", width=300, fg_color="transparent", text_color="#3B8ED0",
                              hover_color="#2B2B2B", command=lambda: self.show_auth_screen(mode="login", prefill_email="")).pack()

                self.login_email_entry = None
                self.after(100, lambda: self.safe_focus(self.master_pass_entry))
            else:
                ctk.CTkLabel(auth_card, text="Welcome Back", font=("Arial", 22, "bold")).pack(pady=(35, 5))
                ctk.CTkLabel(auth_card, text="Enter your email and master password to unlock", text_color="gray").pack(pady=(0, 20))

                self.login_email_entry = ctk.CTkEntry(auth_card, placeholder_text="Email...", width=300, height=40)
                self.login_email_entry.pack(pady=10)
                self.login_email_entry.bind("<Return>", lambda e: self.handle_login())

                pass_row = ctk.CTkFrame(auth_card, fg_color="transparent")
                pass_row.pack(pady=10)
                self.master_pass_entry = ctk.CTkEntry(pass_row, placeholder_text="Master Password...", show="*", width=252, height=40)
                self.master_pass_entry.pack(side="left")
                self.master_pass_entry.bind("<Return>", lambda e: self.handle_login())
                ctk.CTkButton(pass_row, text="👁", width=40, height=40,
                              command=lambda: self.toggle_master_visibility(self.master_pass_entry)).pack(side="left", padx=(8, 0))

                ctk.CTkButton(auth_card, text="Unlock Vault", width=300, height=40, command=self.handle_login).pack(pady=15)

                self.error_label = ctk.CTkLabel(auth_card, text="", text_color="#FF4D4D")
                self.error_label.pack(pady=5)

                ctk.CTkButton(auth_card, text="+ Create new account", width=300, fg_color="transparent", text_color="#3B8ED0",
                              hover_color="#2B2B2B", command=lambda: self.show_auth_screen(mode="create")).pack()

                if prefill_email:
                    self.login_email_entry.insert(0, prefill_email)
                    self.after(100, lambda: self.safe_focus(self.master_pass_entry))
                else:
                    self.after(100, lambda: self.safe_focus(self.login_email_entry))

        if notice and mode == "login":
            self.error_label.configure(text=notice, text_color="#F0AD4E")

    @staticmethod
    def safe_focus(widget):
        """Focus a widget, ignoring the case where its screen was already replaced."""
        try:
            widget.focus_set()
        except Exception:
            pass

    def toggle_master_visibility(self, *entries):
        """Show/hide the master password field(s)."""
        hidden = entries[0].cget("show") == "*"
        for entry in entries:
            entry.configure(show="" if hidden else "*")

    def update_strength_meter(self, event=None):
        """Live-updates the strength bar, requirement checklist and the Create button."""
        pwd = self.setup_pass.get()
        confirm = self.confirm_pass.get()
        result = crypto_utils.check_password_strength(pwd)

        for key, _desc, ok in result["rules"]:
            lbl, desc = self.rule_labels[key]
            lbl.configure(text=f"{'✓' if ok else '○'}  {desc}", text_color="#2FA572" if ok else "gray")

        match_ok = bool(confirm) and pwd == confirm
        lbl, desc = self.rule_labels["match"]
        if confirm and not match_ok:
            lbl.configure(text=f"✗  {desc}", text_color="#FF4D4D")
        else:
            lbl.configure(text=f"{'✓' if match_ok else '○'}  {desc}", text_color="#2FA572" if match_ok else "gray")

        self.strength_bar.set(result["score"])
        self.strength_bar.configure(progress_color=result["color"] if pwd else "#3B8ED0")
        self.strength_label.configure(
            text=f"Strength: {result['label']}" if pwd else "Start typing a password",
            text_color=result["color"]
        )
        self.setup_btn.configure(state="normal" if result["acceptable"] and match_ok else "disabled")

    def show_auth_error(self, message):
        self.error_label.configure(text=message, text_color="#FF4D4D")

    def show_auth_busy(self, message):
        """Key derivation takes a moment (by design), so tell the user something is happening."""
        self.error_label.configure(text=message, text_color="gray")
        self.update_idletasks()

    def handle_setup(self):
        email = self.setup_email.get().strip().lower()
        p1 = self.setup_pass.get()
        p2 = self.confirm_pass.get()
        username = self.setup_username.get().strip()

        if not email or not p1 or not p2 or not username:
            self.show_auth_error("Email, username and both password fields are required!")
            return
        if not EMAIL_PATTERN.match(email):
            self.show_auth_error("Please enter a valid email address!")
            return
        if not crypto_utils.check_password_strength(p1)["acceptable"]:
            self.show_auth_error("Master password doesn't meet all the requirements yet.")
            return
        if p1 != p2:
            self.show_auth_error("Passwords do not match!")
            return
        if self.db.get_account_by_email(email):
            self.show_auth_error("An account with this email already exists!")
            return

        self.show_auth_busy("Creating your encrypted vault…")

        # Initialize Master Security Metadata
        salt = crypto_utils.os.urandom(16)
        key = crypto_utils.derive_key(p1, salt)
        verifier = crypto_utils.encrypt_data("VERIFY_VAULT", key)

        account_id = self.db.create_account(email, username, salt, verifier)
        if account_id is None:
            self.show_auth_error("An account with this email already exists!")
            return

        self.db.account_id = account_id
        self.current_email = email
        if self.remember_email_var.get():
            self.db.set_setting("remembered_email", email)
            self.remembered_email = email
        else:
            self.db.set_setting("remembered_email", "")
            self.remembered_email = ""
        self.master_key = key
        self.show_dashboard_screen()

    def handle_login(self):
        if self.login_email_entry is None:
            email = self.remembered_email.lower()
        else:
            email = self.login_email_entry.get().strip().lower()
        entered_pass = self.master_pass_entry.get()  # not stripped: must match exactly what was set
        if not email or not entered_pass:
            self.show_auth_error("Please enter your email and master password!")
            return

        account = self.db.get_account_by_email(email)
        if not account:
            self.show_auth_error("No account found with this email!")
            return

        account_id, salt, verifier = account
        self.show_auth_busy("Unlocking…")
        key = crypto_utils.derive_key(entered_pass, salt)

        try:
            ok = crypto_utils.decrypt_data(verifier, key) == "VERIFY_VAULT"
        except Exception:
            ok = False

        if ok:
            self.db.account_id = account_id
            self.current_email = email
            self.master_key = key
            self.show_dashboard_screen()
        else:
            self.show_auth_error("Incorrect Master Password!")
            self.master_pass_entry.delete(0, "end")
            self.master_pass_entry.focus_set()

    def get_avatar_image(self, avatar_path, size=58):
        if not avatar_path or not os.path.exists(avatar_path):
            return None
        try:
            image = ImageOps.fit(Image.open(avatar_path).convert("RGBA"), (size, size), method=Image.Resampling.LANCZOS)
            mask = Image.new("L", (size, size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
            image.putalpha(mask)
            return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))
        except Exception:
            return None

    def show_dashboard_screen(self):
        """Renders Main Dashboard."""
        self._on_activity()  # a fresh unlock always starts a fresh idle timer
        for widget in self.winfo_children():
            widget.destroy()

        # TOP BAR
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=(15, 5))

        self.cat_buttons = {}
        for category in ["All", "Login", "Cards", "Secure Note", "Academic"]:
            btn = ctk.CTkButton(
                top_bar, 
                text=category, 
                width=80, 
                height=30, 
                fg_color="#1F6AA5" if category == self.current_category_filter else "#2B2B2B",
                command=lambda c=category: self.filter_category(c)
            )
            btn.pack(side="left", padx=4)
            self.cat_buttons[category] = btn

        profile = self.db.get_profile()
        profile_name = profile[0] if profile else "Profile"
        initials = "".join(part[0] for part in profile_name.split()[:2]).upper() or "P"
        profile_control = ctk.CTkFrame(top_bar, fg_color="transparent")
        profile_control.pack(side="right", padx=4)
        avatar_image = self.get_avatar_image(profile[1] if profile else "")
        profile_button = ctk.CTkButton(
            profile_control,
            text="" if avatar_image else initials,
            image=avatar_image,
            width=62,
            height=62,
            corner_radius=31,
            fg_color="transparent" if avatar_image else "#1F6AA5",
            hover_color="#2B7DB8",
            font=("Arial", 16, "bold"),
            command=lambda: self.show_profile_menu(profile_button)
        )
        profile_button.pack()
        profile_button.image = avatar_image
        ctk.CTkLabel(profile_control, text=profile_name, font=("Arial", 11)).pack()
        ctk.CTkButton(top_bar, text="🔒 Lock", width=70, height=30, fg_color="#D9534F", hover_color="#A52A2A", command=self.show_auth_screen).pack(side="right", padx=4)

        # TOOLBAR
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(toolbar, text="(+) Add Entry", width=120, fg_color="#2FA572", hover_color="#1E704C", command=self.open_add_modal).pack(side="left", padx=4)
        ctk.CTkButton(toolbar, text="🎲 Generator", width=120, command=self.open_generator_modal).pack(side="left", padx=4)

        self.search_entry = ctk.CTkEntry(toolbar, placeholder_text="🔍 Search service name...", width=260)
        self.search_entry.pack(side="right", padx=4)
        self.search_entry.bind("<KeyRelease>", self.on_search_type)

        # TABLE HEADER
        header_frame = ctk.CTkFrame(self, height=35, fg_color="#2B2B2B")
        header_frame.pack(fill="x", padx=20, pady=(10, 0))

        headers = [("Category", 100), ("Service Name", 180), ("Username / Email", 200), ("Password", 120), ("Actions", 150)]
        for title, width in headers:
            ctk.CTkLabel(header_frame, text=title, font=("Arial", 12, "bold"), width=width, anchor="w").pack(side="left", padx=10)

        # SCROLLABLE TABLE
        self.scroll_frame = ctk.CTkScrollableFrame(self, height=360)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=(5, 10))

        # FOOTER
        self.footer_frame = ctk.CTkFrame(self, height=25, fg_color="#1A1A1A")
        self.footer_frame.pack(fill="x", side="bottom")

        self.status_label = ctk.CTkLabel(self.footer_frame, text="Status: 🔒 Vault Unlocked", font=("Arial", 11), text_color="#2FA572")
        self.status_label.pack(side="left", padx=15)

        self.count_label = ctk.CTkLabel(self.footer_frame, text="", font=("Arial", 11), text_color="gray")
        self.count_label.pack(side="right", padx=15)

        self.refresh_records_list()

    def filter_category(self, cat):
        self.current_category_filter = cat
        for c, btn in self.cat_buttons.items():
            btn.configure(fg_color="#1F6AA5" if c == cat else "#2B2B2B")
        self.refresh_records_list()

    def on_search_type(self, event):
        self.current_search_query = self.search_entry.get().lower().strip()
        self.refresh_records_list()

    def refresh_records_list(self):
        """Fetches encrypted data from SQLite, decrypts in RAM, and displays."""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        raw_records = self.db.get_all_credentials()
        decrypted_records = []

        for row in raw_records:
            rec_id, cat, service, user, encrypted_pwd = row
            try:
                plain_pwd = crypto_utils.decrypt_data(encrypted_pwd, self.master_key)
            except Exception:
                plain_pwd = "DECRYPTION_ERROR"

            decrypted_records.append({
                "id": rec_id,
                "category": cat,
                "service": service,
                "username": user,
                "password": plain_pwd
            })

        # Apply Search & Filter
        filtered = []
        for r in decrypted_records:
            if self.current_category_filter != "All" and r["category"] != self.current_category_filter:
                continue
            if self.current_search_query and self.current_search_query not in r["service"].lower():
                continue
            filtered.append(r)

        if not filtered:
            empty_msg = ("Your vault is empty.\nClick \"(+) Add Entry\" to save your first credential."
                         if not decrypted_records else "No credentials match your search or filter.")
            ctk.CTkLabel(self.scroll_frame, text=empty_msg, font=("Arial", 14), text_color="gray", justify="center").pack(pady=40)
        else:
            for rec in filtered:
                self.create_data_row(rec)

        self.count_label.configure(text=f"Total Shown: {len(filtered)} / {len(decrypted_records)}")

    def create_data_row(self, record):
        row = ctk.CTkFrame(self.scroll_frame, height=40, fg_color="#242424")
        row.pack(fill="x", pady=3)

        ctk.CTkLabel(row, text=record["category"], width=100, anchor="w", text_color="#3B8ED0").pack(side="left", padx=10)
        ctk.CTkLabel(row, text=record["service"], width=180, anchor="w", font=("Arial", 13, "bold")).pack(side="left", padx=10)
        ctk.CTkLabel(row, text=record["username"], width=200, anchor="w", text_color="gray").pack(side="left", padx=10)
        ctk.CTkLabel(row, text="••••••••", width=120, anchor="w").pack(side="left", padx=10)

        btn_container = ctk.CTkFrame(row, fg_color="transparent")
        btn_container.pack(side="right", padx=10)

        ctk.CTkButton(btn_container, text="Copy", width=50, height=26, fg_color="#3B8ED0", command=lambda p=record["password"]: self.copy_password(p)).pack(side="left", padx=2)
        ctk.CTkButton(btn_container, text="Edit", width=50, height=26, command=lambda r=record: self.open_edit_modal(r)).pack(side="left", padx=2)
        ctk.CTkButton(btn_container, text="Delete", width=50, height=26, fg_color="#D9534F", hover_color="#A52A2A", command=lambda i=record["id"], s=record["service"]: self.delete_record(i, s)).pack(side="left", padx=2)

    def flash_status(self, text, color="#3B8ED0", ms=3000):
        """Shows a temporary footer message, then restores the default status."""
        if self._status_after_id:
            self.after_cancel(self._status_after_id)
        self.status_label.configure(text=text, text_color=color)
        self._status_after_id = self.after(ms, self.reset_status)

    def reset_status(self):
        self._status_after_id = None
        try:
            self.status_label.configure(text="Status: 🔒 Vault Unlocked", text_color="#2FA572")
        except Exception:
            pass  # footer no longer exists (vault was locked)

    def copy_password(self, pwd):
        pyperclip.copy(pwd)
        # Restart the 15s timer on every copy so an older timer can't wipe a newer copy early
        if self._clipboard_after_id:
            self.after_cancel(self._clipboard_after_id)
        self._clipboard_after_id = self.after(15000, lambda: self.clear_clipboard(pwd))
        self.flash_status("Status: 📋 Password copied to clipboard (clears in 15s)", ms=15000)

    def clear_clipboard(self, pwd):
        self._clipboard_after_id = None
        try:
            if pyperclip.paste() == pwd:  # don't wipe something else the user copied since
                pyperclip.copy("")
        except Exception:
            pass
        self.reset_status()

    def save_record(self, category, service, username, password, rec_id=None):
        encrypted_pwd = crypto_utils.encrypt_data(password, self.master_key)

        if rec_id is None:
            self.db.add_credential(category, service, username, encrypted_pwd)
            status = "Status: ✅ Entry saved"
        else:
            self.db.update_credential(rec_id, category, service, username, encrypted_pwd)
            status = "Status: ✅ Entry updated"

        self.refresh_records_list()
        self.flash_status(status, "#2FA572")

    def open_edit_modal(self, record):
        AddEditCredentialModal(self, on_save_callback=self.save_record, record=record)

    def delete_record(self, rec_id, service=""):
        if not messagebox.askyesno("Delete credential", f"Delete '{service}'?\nThis cannot be undone.", icon="warning", parent=self):
            return
        self.db.delete_credential(rec_id)
        self.refresh_records_list()
        self.flash_status("Status: 🗑 Entry deleted", "#D9534F")

    def show_profile_menu(self, anchor_widget):
        """Dropdown under the profile avatar: open profile, switch account, or add an account."""
        menu = tk.Menu(self, tearoff=0, bg="#2B2B2B", fg="white", activebackground="#1F6AA5",
                       activeforeground="white", bd=0, font=("Arial", 11))
        menu.add_command(label="👤  My Profile", command=self.show_profile_screen)
        menu.add_separator()

        for acc_id, email, username, _avatar in self.db.get_accounts():
            if acc_id == self.db.account_id:
                menu.add_command(label=f"✓  {username} ({email})", state="disabled")
            else:
                menu.add_command(label=f"     {username} ({email})",
                                 command=lambda e=email: self.switch_account(e))

        menu.add_separator()
        menu.add_command(label="➕  Add another account", command=lambda: self.show_auth_screen(mode="create"))

        x = anchor_widget.winfo_rootx()
        y = anchor_widget.winfo_rooty() + anchor_widget.winfo_height()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _on_activity(self, event=None):
        self._last_activity = time.monotonic()

    def _check_inactivity(self):
        """Runs every second: warns shortly before locking, then locks after the idle timeout."""
        try:
            if self.master_key is not None and self.auto_lock_minutes > 0:
                remaining = self.auto_lock_minutes * 60 - (time.monotonic() - self._last_activity)
                if remaining <= 0:
                    self.auto_lock()
                elif remaining <= 10:
                    try:
                        self.flash_status(f"Status: ⏳ Auto-locking in {int(remaining) + 1}s - move the mouse or press a key to stay unlocked",
                                          "#F0AD4E", ms=1500)
                    except Exception:
                        pass  # no footer on this screen (e.g. profile page)
        finally:
            self.after(1000, self._check_inactivity)

    def auto_lock(self):
        """Locks the vault: wipes the key from RAM and closes any open popups."""
        self.show_auth_screen(mode="login", notice="🔒 Vault locked after inactivity")

    def set_auto_lock(self, label):
        self.auto_lock_minutes = AUTO_LOCK_OPTIONS.get(label, DEFAULT_AUTO_LOCK_MINUTES)
        self.db.set_setting("auto_lock_minutes", self.auto_lock_minutes)
        self._on_activity()

    def switch_account(self, email):
        """Locks the current account and asks for the other account's master password."""
        self.show_auth_screen(mode="login", prefill_email=email)

    def show_profile_screen(self):
        for widget in self.winfo_children():
            widget.destroy()

        profile = self.db.get_profile() or ("Profile", "")
        username, avatar_path = profile
        initials = "".join(part[0] for part in username.split()[:2]).upper() or "P"

        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", padx=25, pady=20)
        ctk.CTkButton(top_row, text="Back to Vault", width=120, command=self.show_dashboard_screen).pack(side="left")
        autolock_menu = ctk.CTkOptionMenu(top_row, values=list(AUTO_LOCK_OPTIONS), width=115, command=self.set_auto_lock)
        autolock_menu.set(next((l for l, m in AUTO_LOCK_OPTIONS.items() if m == self.auto_lock_minutes), "5 minutes"))
        autolock_menu.pack(side="right")
        ctk.CTkLabel(top_row, text="🔒 Auto-lock after:").pack(side="right", padx=(0, 8))
        ctk.CTkLabel(self, text="Your Profile", font=("Arial", 26, "bold")).pack(pady=(5, 15))

        avatar = ctk.CTkLabel(self, text=initials, width=150, height=150, corner_radius=75,
                              fg_color="#1F6AA5", font=("Arial", 42, "bold"))
        if avatar_path and os.path.exists(avatar_path):
            try:
                image = ImageOps.fit(Image.open(avatar_path).convert("RGB"), (150, 150), method=Image.Resampling.LANCZOS)
                avatar_image = ctk.CTkImage(light_image=image, dark_image=image, size=(150, 150))
                avatar.configure(text="", image=avatar_image, fg_color="transparent", corner_radius=0)
                avatar.image = avatar_image
            except Exception:
                pass
        avatar.pack(pady=10)

        ctk.CTkLabel(self, text=username, font=("Arial", 20, "bold")).pack(pady=5)
        ctk.CTkLabel(self, text=self.current_email, text_color="gray").pack()
        ctk.CTkButton(self, text="Choose Profile Picture", command=self.choose_avatar).pack(pady=12)

        total_entries = len(self.db.get_all_credentials())
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.pack(fill="x", padx=100, pady=25)
        ctk.CTkLabel(stats_frame, text=f"Total Entries\n{total_entries}", font=("Arial", 18, "bold")).pack(side="left", expand=True)

        categories = self.db.get_category_counts()
        category_text = "\n".join(f"{category}: {count}" for category, count in categories) or "No entries yet"
        ctk.CTkLabel(stats_frame, text=f"Entry Types\n{category_text}", justify="left", font=("Arial", 15)).pack(side="right", expand=True)

    def choose_avatar(self):
        selected_path = filedialog.askopenfilename(
            title="Choose Profile Picture",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif"), ("All files", "*.*")]
        )
        if selected_path:
            profile = self.db.get_profile() or ("Profile", "")
            self.db.save_profile(profile[0], selected_path)
            self.show_profile_screen()

    def open_add_modal(self):
        AddEditCredentialModal(self, on_save_callback=self.save_record)

    def open_generator_modal(self):
        PasswordGeneratorModal(self)


if __name__ == "__main__":
    app = PasswordManagerApp()
    app.mainloop()