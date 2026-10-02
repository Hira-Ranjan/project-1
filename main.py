import customtkinter as ctk
import random
import string
import os
import pyperclip
from tkinter import filedialog
from PIL import Image, ImageDraw, ImageOps


from database import Database
import crypto_utils

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")



class AddEditCredentialModal(ctk.CTkToplevel):
    """Modal popup for adding a new encrypted credential."""
    def __init__(self, parent, on_save_callback):
        super().__init__(parent)
        self.transient(parent)
        self.title("Add New Credential")
        self.geometry("450x500")
        self.resizable(False, False)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.close)

        self.on_save_callback = on_save_callback

        # Center popup on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (450 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (500 // 2)
        self.geometry(f"+{x}+{y}")

        ctk.CTkLabel(self, text="Add New Credential", font=("Arial", 18, "bold")).pack(pady=(20, 15))

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

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=15)

        ctk.CTkButton(btn_frame, text="Cancel", fg_color="#555555", hover_color="#333333", width=110, command=self.close).pack(side="left")
        ctk.CTkButton(btn_frame, text="Save Entry", width=110, command=self.save_data).pack(side="right")

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

        self.on_save_callback(cat, service, user, pwd)
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

        password_chars = [random.choice(symbols) for _ in range(minimum_symbols)]
        password_chars.extend(random.choice(chars) for _ in range(length - minimum_symbols))
        random.shuffle(password_chars)
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

        self.current_category_filter = "All"
        self.current_search_query = ""

        # Launch appropriate screen
        self.show_auth_screen()

    def show_auth_screen(self):
        """Renders either First-Time Setup or Returning Login View."""
        for widget in self.winfo_children():
            widget.destroy()

        self.master_key = None  # Clear key from RAM when locked

        auth_card = ctk.CTkFrame(self, width=420, height=450, corner_radius=15)
        auth_card.place(relx=0.5, rely=0.5, anchor="center")

        if not self.db.is_vault_initialized():
            # FIRST TIME SETUP
            ctk.CTkLabel(auth_card, text="Create Master Vault", font=("Arial", 22, "bold")).pack(pady=(25, 5))
            ctk.CTkLabel(auth_card, text="Set a master key to encrypt your local database", text_color="gray").pack(pady=(0, 15))

            self.setup_pass = ctk.CTkEntry(auth_card, placeholder_text="New Master Password...", show="*", width=300, height=38)
            self.setup_pass.pack(pady=8)

            self.setup_username = ctk.CTkEntry(auth_card, placeholder_text="Username...", width=300, height=38)
            self.setup_username.pack(pady=8)

            self.confirm_pass = ctk.CTkEntry(auth_card, placeholder_text="Confirm Master Password...", show="*", width=300, height=38)
            self.confirm_pass.pack(pady=8)

            self.error_label = ctk.CTkLabel(auth_card, text="", text_color="#FF4D4D")
            self.error_label.pack(pady=5)

            ctk.CTkButton(auth_card, text="Create Vault & Continue", width=300, height=40, fg_color="#2FA572", command=self.handle_setup).pack(pady=10)

        else:
            # RETURNING USER LOGIN
            ctk.CTkLabel(auth_card, text="Welcome Back", font=("Arial", 22, "bold")).pack(pady=(35, 5))
            ctk.CTkLabel(auth_card, text="Enter Master Password to unlock", text_color="gray").pack(pady=(0, 20))

            self.master_pass_entry = ctk.CTkEntry(auth_card, placeholder_text="Master Password...", show="*", width=300, height=40)
            self.master_pass_entry.pack(pady=10)
            self.master_pass_entry.bind("<Return>", lambda e: self.handle_login())

            ctk.CTkButton(auth_card, text="Unlock Vault", width=300, height=40, command=self.handle_login).pack(pady=15)

            self.error_label = ctk.CTkLabel(auth_card, text="", text_color="#FF4D4D")
            self.error_label.pack(pady=5)

    def handle_setup(self):
        p1 = self.setup_pass.get()
        p2 = self.confirm_pass.get()
        username = self.setup_username.get().strip()

        if not p1 or not p2 or not username:
            self.error_label.configure(text="Username and both password fields are required!")
            return
        if p1 != p2:
            self.error_label.configure(text="Passwords do not match!")
            return
        if len(p1) < 6:
            self.error_label.configure(text="Master password must be at least 6 chars!")
            return

        # Initialize Master Security Metadata
        salt = crypto_utils.os.urandom(16)
        key = crypto_utils.derive_key(p1, salt)
        verifier = crypto_utils.encrypt_data("VERIFY_VAULT", key)

        self.db.save_master_meta(salt, verifier)
        self.db.save_profile(username)
        self.master_key = key
        self.show_dashboard_screen()

    def handle_login(self):
        entered_pass = self.master_pass_entry.get().strip()
        if not entered_pass:
            self.error_label.configure(text="Please enter your master password!")
            return

        salt, verifier = self.db.get_master_meta()
        key = crypto_utils.derive_key(entered_pass, salt)

        try:
            decrypted_check = crypto_utils.decrypt_data(verifier, key)
            if decrypted_check == "VERIFY_VAULT":
                self.master_key = key
                self.show_dashboard_screen()
            else:
                self.error_label.configure(text="Incorrect Master Password!")
        except Exception:
            self.error_label.configure(text="Incorrect Master Password!")

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
            command=self.show_profile_screen
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
            ctk.CTkLabel(self.scroll_frame, text="No credentials found.", font=("Arial", 14), text_color="gray").pack(pady=40)
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

        ctk.CTkButton(btn_container, text="Copy", width=55, height=26, fg_color="#3B8ED0", command=lambda p=record["password"]: self.copy_password(p)).pack(side="left", padx=2)
        ctk.CTkButton(btn_container, text="Delete", width=55, height=26, fg_color="#D9534F", hover_color="#A52A2A", command=lambda i=record["id"]: self.delete_record(i)).pack(side="left", padx=2)

    def copy_password(self, pwd):
        pyperclip.copy(pwd)
        self.status_label.configure(text="Status: 📋 Password copied to clipboard (Clears in 15s)!", text_color="#3B8ED0")
        # Auto-clear clipboard after 15 seconds
        self.after(15000, self.clear_clipboard)

    def clear_clipboard(self):
        pyperclip.copy("")
        self.status_label.configure(text="Status: 🔒 Vault Unlocked", text_color="#2FA572")

    def save_new_record(self, category, service, username, password):
        # Encrypt plaintext password before saving
        encrypted_pwd = crypto_utils.encrypt_data(password, self.master_key)
        self.db.add_credential(category, service, username, encrypted_pwd)
        self.refresh_records_list()

    def delete_record(self, rec_id):
        self.db.delete_credential(rec_id)
        self.refresh_records_list()

    def show_profile_screen(self):
        for widget in self.winfo_children():
            widget.destroy()

        profile = self.db.get_profile() or ("Profile", "")
        username, avatar_path = profile
        initials = "".join(part[0] for part in username.split()[:2]).upper() or "P"

        ctk.CTkButton(self, text="Back to Vault", width=120, command=self.show_dashboard_screen).pack(anchor="nw", padx=25, pady=20)
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
        AddEditCredentialModal(self, on_save_callback=self.save_new_record)

    def open_generator_modal(self):
        PasswordGeneratorModal(self)


if __name__ == "__main__":
    app = PasswordManagerApp()
    app.mainloop()