import customtkinter as ctk
import queue
import threading
import socket
import keyboard
from Project_Classes.general_classes import SockFunctions, SEP
from Encryption.encrypt_class import secure_sendto, secure_recvfrom

CHUNK_SIZE = 1024
class TextGui(SockFunctions, ctk.CTkFrame):
    def __init__(self, sock: socket.socket,query_sock : socket.socket,parent: ctk.CTkFrame,user_id = '0', group_id = '0',
                 can_send = True, placeholder = "Type a uncrypted...", read_only_notice = "Only the group owner can post here."):

        # --- Inheritance init ---
        SockFunctions.__init__(self,sock=sock,query_sock=query_sock,user_id=user_id,group_id=group_id)
        ctk.CTkFrame.__init__(self, parent)

        # Whether THIS user may post in this channel. For the announcements
        # channel non-owners get a read-only view (they still receive messages).
        self.can_send = can_send


        # --- List, Queue & Dict Init --
        self.chat_queue = queue.Queue()
        self.running = True   # cleared on shutdown to stop the worker loop


        # --- Gui Init ---
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)
        self.columnconfigure(0, weight=1)

        self.chat_frame = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.chat_frame.grid(row=0,column=0, sticky="nsew", padx=10, pady=10)

        self.input_frame = ctk.CTkFrame(self, height=80)
        self.input_frame.grid(row=1,column=0, sticky="ew", padx=20, pady=(0, 20))
        self.input_frame.grid_columnconfigure(0, weight=1)

        if self.can_send:
            self.entry = ctk.CTkEntry(self.input_frame, placeholder_text=placeholder,
                                      height=45, corner_radius=20, border_width=1)
            self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

            self.send_button = ctk.CTkButton(self.input_frame, text="➤", width=50, height=45,
                                             corner_radius=20, font=("bold", 20), command=self.__input_handler)
            self.send_button.grid(row=0, column=1)

            keyboard.add_hotkey('enter', self.__input_handler)
        else:
            # Read-only channel: no entry box, just a notice in place of the input bar.
            self.entry = None
            self.send_button = None
            ctk.CTkLabel(self.input_frame, text=read_only_notice,
                         text_color="gray", height=45).grid(row=0, column=0, sticky="ew", padx=10, pady=10)




        threading.Thread(target=self.__output_handler, daemon=True).start()

        self.update_chat()

    def add_message(self, sender_addr, text):
        color = "#2b719e" if sender_addr == self.name else "#42817b"
        text_color = "white"

        msg_container = ctk.CTkFrame(self.chat_frame, fg_color="transparent")


        bubble = ctk.CTkLabel(msg_container, text=text,
                              fg_color=color, text_color=text_color,
                              corner_radius=15, padx=15, pady=8,
                              wraplength=300)

        name_lbl = ctk.CTkLabel(msg_container, text=sender_addr, font=ctk.CTkFont(size=10))
        name_lbl.pack(side="right", padx=5)
        bubble.pack(side="right", padx=5)
        msg_container.pack(fill="x", pady=5)

    # s
    def update_chat(self):
        if not self.chat_queue.empty() and self.alive:
            msg, sender_username = self.chat_queue.get_nowait()
            self.add_message(sender_username, msg)

        self.after(ms=15, func=self.update_chat)

    def __input_handler(self):
        if self.alive and self.can_send and self.entry is not None:
            entry_text = self.entry.get()
            if entry_text:
                data = entry_text.encode()
                secure_sendto(self.sock, data+SEP+self.user_id.encode(), self.server_addr)

                self.add_message(self.name, entry_text)
                self.entry.delete(0, ctk.END)

    def __output_handler(self):
        while self.running:
            try:
                packet, sender_id = secure_recvfrom(self.sock, CHUNK_SIZE)[0].split(SEP)
            except OSError:
                break
            sender_id = sender_id.decode()

            message = packet.decode()

            if not self.chatters_dict.get(sender_id):
                sender_username = self.find_username_by_id(sender_id)
                self.chatters_dict[sender_id] = sender_username

            self.chat_queue.put((message, self.chatters_dict[sender_id]))

    def leave_chat(self):
        if self.alive:
            print('turning off text chat')
            self.alive = False

    def enter_chat(self):
        if not self.alive:
            print('turning on text chat')
            self.alive = True
            self.send_join()   # register this socket with our group on the server

    def close(self):
        # Stop the worker loop, drop the global hotkey and close the socket.
        self.running = False
        self.alive = False
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        try:
            self.sock.close()       # unblocks a pending recvfrom
        except Exception:
            pass