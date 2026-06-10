import customtkinter
import customtkinter as ctk
from Project_Classes.login_class import TalkHobiLogin
from Project_Classes.signup_class import TalkHobiSignup
from Project_Classes.lobby_class import LobbyClass
from Project_Classes.chat_connector import ChatsClass
import threading
import time
import socket
class PrimeGui(ctk.CTk):
    def __init__(self, video_socket: socket.socket,
                    text_socket: socket.socket,
                        audio_socket: socket.socket,
                            query_socket : socket.socket,
                                announcements_socket: socket.socket = None):

        super().__init__()
        customtkinter.set_appearance_mode("dark")
        # --- Window Configuration ---
        self.title("Client")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.video_socket = video_socket
        self.text_socket = text_socket
        self.audio_socket = audio_socket
        self.query_socket = query_socket
        self.announcements_socket = announcements_socket

        self.frames : dict = {
            'login': TalkHobiLogin(self, self.query_socket),
            'signup': TalkHobiSignup(self, self.query_socket),
        }
        self.grid_rowconfigure(0,weight=1)
        self.grid_columnconfigure(0,weight=1)#s

        self.frames['login'].grid(row=0, column=0, sticky="nsew")
        threading.Thread(target=self.__logpage_loop, daemon=True).start()

        # Shut everything down cleanly when the window is closed.
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        chats_frame = self.frames.get('chats')
        if chats_frame is not None:
            for chat in chats_frame.chats.values():
                    try:
                        chat.close()
                    except Exception:
                        pass

        for sock in (self.video_socket, self.text_socket,
                     self.audio_socket, self.query_socket,
                     self.announcements_socket):
            if sock is None:
                continue
            try:
                sock.close()
            except Exception:
                pass

        self.destroy()

    def __logpage_loop(self):
        while True:
            if self.frames['login'].user_id:
                self.user_id = self.frames['login'].user_id
                break
            time.sleep(0.005)

        self.frames['lobby'] = LobbyClass(self, self.user_id, self.query_socket)
        self.show_frame('lobby')
        while True:
            group_id = self.frames['lobby'].selected_group_id
            if group_id:
                break
            time.sleep(0.05)

        self.frames['chats'] = ChatsClass(self, self.user_id, group_id,
                                          self.video_socket,
                                          self.text_socket,
                                          self.audio_socket,
                                          self.query_socket,
                                          self.announcements_socket)
        self.show_frame('chats')

    def show_frame(self, active_frame_name: str):
        for value in self.frames.values():
            if value != self.frames[active_frame_name]:
                value.grid_forget()
            else:
                try:
                    value.enter_chat()
                except:
                    pass

        self.frames[active_frame_name].grid(row=0, column=0, sticky="nsew")
        self.frames[active_frame_name].tkraise()