import customtkinter as ctk
from Project_Classes.general_classes import SEP, sql_query_flags
from Encryption.encrypt_class import client_send, client_recv

CHUNK_SIZE = 1024


class TalkHobiLogin(ctk.CTkFrame):
    def __init__(self, parent, query_sock):
        ctk.CTkFrame.__init__(self,parent)

        self.query_sock = query_sock
        self.server_addr = query_sock.getpeername()
        self.user_id = None

        self.configure(width=900, height=600)

        self.login_frame = ctk.CTkFrame(self, corner_radius=20, width=320, height=420)
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center")

        # --- App Title ---
        self.title_label = ctk.CTkLabel(
            self.login_frame,
            text="TalkHobi",
            font=ctk.CTkFont(family="Roboto", size=36, weight="bold")
        )
        self.title_label.place(relx=0.5, rely=0.15, anchor="center")

        self.subtitle_label = ctk.CTkLabel(
            self.login_frame,
            text="Sign in",
            font=ctk.CTkFont(family="Roboto", size=14),
            text_color="gray"
        )
        self.subtitle_label.place(relx=0.5, rely=0.25, anchor="center")

        # --- Username / Email Field ---
        self.username_entry = ctk.CTkEntry(
            self.login_frame,
            width=240,
            height=40,
            placeholder_text="Email or Username",
            corner_radius=8
        )
        self.username_entry.place(relx=0.5, rely=0.42, anchor="center")

        self.password_entry = ctk.CTkEntry(
            self.login_frame,
            width=240,
            height=40,
            placeholder_text="Password",
            show="*",
            corner_radius=8
        )
        self.password_entry.place(relx=0.5, rely=0.56, anchor="center")

        self.login_button = ctk.CTkButton(
            self.login_frame,
            text="Login",
            width=240,
            height=40,
            corner_radius=8,
            command=self.login_button_command,
            font=ctk.CTkFont(family="Roboto", size=15, weight="bold")
        )
        self.login_button.place(relx=0.5, rely=0.72, anchor="center")

        self.register_button = ctk.CTkButton(
            self.login_frame,
            text="Don't have an account? Sign up",
            font=ctk.CTkFont(family="Roboto", size=12,weight="bold"),
            fg_color="transparent",
            hover_color='#363636',
            text_color='white',
            command=self.go_to_signup
        )
        self.register_button.bind("<Enter>", self.on_enter)
        self.register_button.bind("<Leave>", self.on_leave)
        self.register_button.place(relx=0.5, rely=0.88, anchor="center")


    # --- Button Functions ---
    def login_button_command(self):
        field1 = self.username_entry.get()
        password = self.password_entry.get()
        client_send(self.query_sock,
                    sql_query_flags['username_login'] + SEP + field1.encode() + SEP + password.encode(),
                    self.server_addr)
        query_answer = client_recv(self.query_sock, CHUNK_SIZE)[0].split(SEP)
        print(query_answer)
        if query_answer[0] == sql_query_flags['username_login']:
            if query_answer[1] == b'True':
                self.login_button.configure(fg_color="#43b027", hover_color="#368f1f")
                print("Logging in...")
                client_send(self.query_sock, sql_query_flags['user_ID_by_username'] + SEP + field1.encode(), self.server_addr)
                query_answer, _ = client_recv(self.query_sock, CHUNK_SIZE)
                query_answer = query_answer.split(SEP)

                if query_answer[0] == sql_query_flags['user_ID_by_username']:
                    self.user_id = query_answer[1].decode()
            else:
                self.login_button.configure(fg_color="#611616", hover_color="#4d1010")
                print("Login failed")

    def go_to_signup(self):
        self.master.show_frame('signup')

    def on_enter(self,event):
        self.register_button.configure(text_color="#3B8ED0",fg_color="#363636")

    def on_leave(self,event):
       self.register_button.configure(text_color='White',fg_color="transparent")

