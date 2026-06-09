import customtkinter as ctk
from Project_Classes.video_gui_class import VideoGui
from Project_Classes.text_gui_class import TextGui
from Project_Classes.audio_class import AudioClient
from database_classes.client_query_helper import ClientQueryHelper
import socket



class ChatsClass(ctk.CTkFrame):
    def __init__(self,parent: ctk.CTk,user_id, group_id,
                 video_socket: socket.socket,
                 text_socket: socket.socket,
                    audio_socket: socket.socket,
                 query_sock : socket.socket,
                 announcements_socket: socket.socket = None):

        super().__init__(parent)

        # --- Socket Init ---
        self.video_socket = video_socket
        self.text_socket = text_socket
        self.audio_socket = audio_socket
        self.announcements_socket = announcements_socket

        # Is this user the owner of the group? Only the owner may post in the
        # announcements channel (everyone else gets a read-only view).
        try:
            self.is_owner = ClientQueryHelper(query_sock).is_owner(group_id, user_id)
        except Exception as e:
            print('owner check failed:', e)
            self.is_owner = False

        # --- Grid Configuration ---
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # --- Sidebar Navigation Init ---
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#161618")
        self.sidebar.grid(row=0, column=0, sticky="nsew",rowspan=2,pady=20)

        # --- Title Init ---
        self.logo_label = ctk.CTkLabel(
            self.sidebar,
            text="TalkHobi",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 40))

        # --- Navigation Buttons Init ---
        self.announcements_channel_button = ctk.CTkButton(
            self.sidebar,
            text="⌂",
            anchor="w",
            height=40,
            fg_color="transparent",
            hover_color="#242428",
            font=ctk.CTkFont(size=20),
            command=lambda: self.show_frame("Announcements")
        )
        self.announcements_channel_button.grid(row=1, column=0, padx=15, pady=5, sticky="ew")

        self.video_channel_button = ctk.CTkButton(
            self.sidebar,
            text="Video Chat",
            anchor="w",
            height=40,
            fg_color="transparent",
            hover_color="#242428",
            font=ctk.CTkFont(size=14),
            command= lambda: self.show_frame("VideoGui")
        )
        self.video_channel_button.grid(row=2, column=0, padx=15, pady=5, sticky="ew")

        self.text_channel_button = ctk.CTkButton(
            self.sidebar,
            text="Text Chat",
            anchor="w",
            height=40,
            fg_color="transparent",
            hover_color="#242428",
            font=ctk.CTkFont(size=14),
            command= lambda: self.show_frame("TextGui")
        )
        self.text_channel_button.grid(row=3, column=0, padx=15, pady=5, sticky="ew")

        self.sidebar_dict = {
            "Announcements": self.announcements_channel_button,
            "VideoGui": self.video_channel_button,
            "TextGui": self.text_channel_button }

        # --- Main Container Init ---
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="black")
        self.main_container.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_container_tb = ctk.CTkLabel(self.main_container)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # --- Control Panel Init ---
        self.controls_frame = ctk.CTkFrame(self, height=70, corner_radius=0, fg_color="#181818")
        self.controls_frame.grid_columnconfigure(0, weight=1)
        self.controls_frame.grid_columnconfigure(4, weight=1)

        mic_button = ctk.CTkButton(
            self.controls_frame,
            text="🎙",
            command=self.mic_button_command,
            width=160,
            height=40,
            fg_color="#1f538d",
            hover_color="#14375e",
            font=ctk.CTkFont(size=25, weight="bold")
        )

        camera_button = ctk.CTkButton(
            self.controls_frame,
            text="Turn Camera Off",
            command=self.cam_button_command,
            width=160,
            height=40,
            fg_color="#1f538d",
            hover_color="#14375e",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        exit_button = ctk.CTkButton(
            self.controls_frame,
            text="⏻",
            command=self.leave_button_command,
            width=160,
            height=40,
            fg_color="#611616",
            hover_color="#450e0e",
            font=ctk.CTkFont(size=25, weight="bold")
        )
        join_button = ctk.CTkButton(
            self.controls_frame,
            text="⏻",
            command=self.join_button_command,
            width=160,
            height=40,
            fg_color="#1f538d",
            hover_color="#14375e",
            font=ctk.CTkFont(size=25, weight="bold")
        )
        # Default UI State
        self.controls_dict = {
            'mic': mic_button,
            'cam': camera_button,
            'exit': exit_button,
            'join': join_button,}

        # The announcements channel is a text channel on its own relay where
        # only the group owner can post; everyone else sees it read-only.
        if self.announcements_socket is not None:
            announcements = TextGui(
                user_id=user_id,
                sock=self.announcements_socket,
                parent=self.main_container,
                query_sock=query_sock, group_id=group_id,
                can_send=self.is_owner,
                placeholder="Post an announcement...",
                read_only_notice="📢 Only the group owner can post announcements.")
        else:
            announcements = self._create_placeholder_frame("Announcements Coming Soon...")

        video = VideoGui(
                sock=self.video_socket,
                parent=self.main_container,
                query_sock=query_sock,
                 user_id= user_id, group_id=group_id)

        text = TextGui(user_id=user_id,
                sock=text_socket,
                parent=self.main_container,
                query_sock=query_sock, group_id=group_id)

        audio = AudioClient(sock=self.audio_socket,
                                                query_sock=query_sock,
                                                video_gui=video,user_id=user_id, group_id=group_id)

        self.chats = {

        "Announcements":  announcements,

        "VideoGui" :  video,

        "TextGui":  text,

        "AudioClient" : audio }

        self.show_frame("Announcements")

    def mic_button_command(self):
        if self.chats.get("AudioClient").mic_switch():
            self.controls_dict['mic'].configure(fg_color="#611616", hover_color="#450e0e")
        else:
            self.controls_dict['mic'].configure(fg_color="#1f538d", hover_color="#14375e")
        self.chats["VideoGui"].change_box_outline()

    def join_button_command(self):
        self.controls_dict['join'].grid_forget()
        self.controls_dict['mic'].grid(column=1, row=0, padx=10, pady=10)
        self.controls_dict['cam'].grid(column=2, row=0, padx=10, pady=10)
        self.controls_dict['exit'].grid(column=3, row=0, padx=10, pady=10)
        self.main_container_tb.configure(text="")
        self.main_container_tb.grid_forget()
        self.chats.get("VideoGui").enter_chat()
        self.chats.get("AudioClient").enter_chat()

    def leave_button_command(self):
        self.controls_dict['exit'].grid_forget()
        self.controls_dict['cam'].grid_forget()
        self.controls_dict['mic'].grid_forget()
        self.controls_dict['join'].grid(column=1, row=0, padx=10, pady=10)
        self.main_container_tb.configure(text="You have left the chat room.")
        self.main_container_tb.grid(row=1,column=0)

        self.chats.get("VideoGui").leave_chat()
        self.chats.get("AudioClient").leave_chat()

    def cam_button_command(self):
        if self.chats.get("VideoGui").camera_switch():
            self.controls_dict['cam'].configure(text="Turn Camera On", fg_color="#611616", hover_color="#450e0e")
        else:
            self.controls_dict['cam'].configure(text="Turn Camera Off", fg_color="#1f538d", hover_color="#14375e")


    def _create_placeholder_frame(self, text):
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        label = ctk.CTkLabel(frame, text=text, text_color="gray", font=ctk.CTkFont(size=18))
        label.pack(expand=True)
        return frame

    def show_frame(self, active_frame_name: str):
        for frame in self.chats.values():
            if frame != self.chats[active_frame_name]:
                try:
                    if not (active_frame_name == "VideoGui" and frame == self.chats["AudioClient"]):
                        frame.leave_chat()
                    frame.grid_forget()
                except:
                    pass
            else:
                try:
                    if not active_frame_name == "VideoGui":
                        self.controls_frame.grid_forget()
                        self.main_container_tb.configure(text="")
                        self.main_container_tb.grid_forget()
                    else:
                        print('video gui is active')
                        self.controls_frame.grid(row=1, column=1, pady=(0, 20), sticky="nsew", padx=10)
                        self.controls_dict['mic'].grid(column=1, row=0, padx=10, pady=10)
                        self.controls_dict['cam'].grid(column=2, row=0, padx=10, pady=10)
                        self.controls_dict['exit'].grid(column=3, row=0, padx=10, pady=10)
                        self.chats["AudioClient"].enter_chat()
                    frame.enter_chat()
                except:
                    pass
        self.chats[active_frame_name].grid(row=0, column=0, sticky="nsew")
        self.chats[active_frame_name].tkraise()
        self._highlight_nav_button(self.sidebar_dict[active_frame_name])

    def reset_control_panel(self):
        self.controls_dict['mic'].configure(fg_color="#1f538d", hover_color="#14375e")
        self.controls_dict['cam'].configure(fg_color="#1f538d", hover_color="#14375e")
        self.controls_dict['exit'].configure(fg_color="#611616", hover_color="#450e0e")

    def _highlight_nav_button(self, active_button):
        for button in self.sidebar.winfo_children():
            button.configure(fg_color="transparent")
        active_button.configure(fg_color="#1f538d")