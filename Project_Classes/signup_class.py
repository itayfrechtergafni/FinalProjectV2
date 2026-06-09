import customtkinter as ctk
from database_classes.client_query_helper import ClientQueryHelper


class TalkHobiSignup(ctk.CTkFrame):


    def __init__(self, parent, query_sock):
        ctk.CTkFrame.__init__(self, parent)

        self.query_helper = ClientQueryHelper(query_sock)

        self.configure(width=900, height=600)

        self.signup_frame = ctk.CTkFrame(self, corner_radius=20, width=360, height=560)
        self.signup_frame.place(relx=0.5, rely=0.5, anchor="center")
        self.signup_frame.grid_columnconfigure(0, weight=1)

        # --- Title ---
        ctk.CTkLabel(
            self.signup_frame,
            text="Create account",
            font=ctk.CTkFont(family="Roboto", size=28, weight="bold")
        ).grid(row=0, column=0, padx=40, pady=(30, 4), sticky="ew")

        ctk.CTkLabel(
            self.signup_frame,
            text="Join TalkHobi",
            font=ctk.CTkFont(family="Roboto", size=13),
            text_color="gray"
        ).grid(row=1, column=0, padx=40, pady=(0, 16), sticky="ew")

        # --- Entries ---
        self.username_entry = self.__field("Username", row=2)
        self.first_name_entry = self.__field("First name", row=3)
        self.last_name_entry = self.__field("Last name", row=4)
        self.email_entry = self.__field("Email", row=5)
        self.password_entry = self.__field("Password", row=6, show="*")
        self.confirm_entry = self.__field("Confirm password", row=7, show="*")

        # --- Status line (error / success) ---
        self.status_label = ctk.CTkLabel(
            self.signup_frame, text="", text_color="gray",
            font=ctk.CTkFont(family="Roboto", size=12)
        )
        self.status_label.grid(row=8, column=0, padx=40, pady=(8, 0), sticky="ew")

        # --- Buttons ---
        self.signup_button = ctk.CTkButton(
            self.signup_frame,
            text="Sign up",
            height=40,
            corner_radius=8,
            command=self.signup_button_command,
            font=ctk.CTkFont(family="Roboto", size=15, weight="bold")
        )
        self.signup_button.grid(row=9, column=0, padx=40, pady=(10, 4), sticky="ew")

        self.back_button = ctk.CTkButton(
            self.signup_frame,
            text="Already have an account? Log in",
            font=ctk.CTkFont(family="Roboto", size=12, weight="bold"),
            fg_color="transparent",
            hover_color="#363636",
            text_color="white",
            command=self.go_to_login
        )
        self.back_button.grid(row=10, column=0, padx=40, pady=(0, 24), sticky="ew")
        self.back_button.bind("<Enter>", self.on_enter)
        self.back_button.bind("<Leave>", self.on_leave)

    # --- Private Helpers ---
    def __field(self, placeholder, row, show=None):
        entry = ctk.CTkEntry(
            self.signup_frame, height=38, placeholder_text=placeholder,
            corner_radius=8, show=show if show else ""
        )
        entry.grid(row=row, column=0, padx=40, pady=5, sticky="ew")
        return entry

    def __set_status(self, text, signup_status=False):
        self.status_label.configure(text=text, text_color="#43b027" if signup_status else "#d14249")

    # --- Button commands ---
    def signup_button_command(self):
        username = self.username_entry.get().strip()
        first = self.first_name_entry.get().strip()
        last = self.last_name_entry.get().strip()
        email = self.email_entry.get().strip()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()

        # --- client-side validation ---
        if not all((username, first, last, email, password)):
            self.__set_status("Please fill in every field.")
            return
        if "@" not in email or "." not in email:
            self.__set_status("Please enter a valid email address.")
            return
        if password != confirm:
            self.__set_status("Passwords don't match.")
            return

        try:
            result = self.query_helper.register_user(username, first, last, email, password)
        except Exception as e:
            print("signup error:", e)
            self.__set_status("Couldn't reach the server. Try again.")
            return

        if result == "USERNAME_TAKEN":
            self.__set_status("That username is already taken.")
        elif result == "EMAIL_TAKEN":
            self.__set_status("An account with that email already exists.")
        elif result.isdigit():
            self.__set_status("Account created! Redirecting to login...", signup_status=True)
            self.after(900, lambda: self.go_to_login(prefill=username))
        else:
            self.__set_status("Something went wrong. Try again.")

    def go_to_login(self, prefill=None):
        login = self.master.frames.get("login")
        if prefill and login is not None:
            login.username_entry.delete(0, ctk.END)
            login.username_entry.insert(0, prefill)
        self.master.show_frame("login")

    # --- Hover effects for the link-style button ---
    def on_enter(self, event):
        self.back_button.configure(text_color="#3B8ED0", fg_color="#363636")

    def on_leave(self, event):
        self.back_button.configure(text_color="white", fg_color="transparent")
