import customtkinter as ctk
import socket
from database_classes.client_query_helper import ClientQueryHelper



class LobbyClass(ctk.CTkFrame):


    def __init__(self, parent, user_id, query_sock: socket.socket):
        super().__init__(parent)
        self.user_id = user_id
        self.query_helper = ClientQueryHelper(query_sock)
        self.selected_group_id = None
        self.selected_group_name = None
        self._owned_group_ids = {}   # group_name -> group_id (groups this user owns)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Header ---
        ctk.CTkLabel(self, text="Your Groups",
                     font=ctk.CTkFont(size=24, weight="bold")
                     ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # --- Scrollable list of groups ---
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.list_frame.grid_columnconfigure(0, weight=1)

        # --- Controls ---
        self.controls = ctk.CTkFrame(self, fg_color="transparent")
        self.controls.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.controls.grid_columnconfigure(0, weight=1)   # left side grows; Refresh hugs the right

        # create a new group owned by you
        self.create_group_frame = ctk.CTkFrame(self.controls, fg_color="transparent")
        self.create_group_frame.grid(row=0, column=0, sticky="ew")
        self.create_group_frame.grid_columnconfigure(0, weight=1)

        self.new_group_entry = ctk.CTkEntry(self.create_group_frame, placeholder_text="New group name", height=40)
        self.new_group_entry.grid(row=0, column=0, padx=(0, 8), pady=10, sticky="ew")

        self.create_group_button = ctk.CTkButton(self.create_group_frame, text="Create group", width=160, height=40,
                      command=self.__create_group)
        self.create_group_button.grid(row=0, column=1, pady=10)

        self.add_member_frame = ctk.CTkFrame(self.controls, fg_color="transparent")
        self.add_member_frame.grid(row=1, column=0, sticky="ew")
        self.add_member_frame.grid_columnconfigure(0, weight=1)

        # add a member to one of your owned groups
        self.group_menu = ctk.CTkOptionMenu(self.add_member_frame, values=[], width=160, height=40)
        self.group_menu.grid(row=0, column=0, padx=(0, 8), sticky="ew")


        self.add_user_entry = ctk.CTkEntry(self.add_member_frame, placeholder_text="USERNAME",
                                           width=120, height=40)
        self.add_user_entry.grid(row=0, column=1, padx=(0, 8))

        self.add_button = ctk.CTkButton(self.add_member_frame, text="Add member", width=120, height=40,
                                        command=self.__add_member)
        self.add_button.grid(row=0, column=2)

        # refresh group list button — sits to the right, vertically centred on the rows to its left.
        # rowspan=2 means it spans the create row + add-member row when both are shown; when the
        # add-member row is hidden, that row collapses to 0 height and Refresh lines up with the
        # create row instead.
        self.refresh_button = ctk.CTkButton(self.controls, text="Refresh", width=120, height=40,
                      command=self.refresh)
        self.refresh_button.grid(row=0, column=1, rowspan=2, padx=(16, 0), pady=10, sticky="ns")

        self.status_label = ctk.CTkLabel(self.controls, text="", text_color="gray")
        self.status_label.grid(row=2, column=0, pady=(2, 0), sticky="w")

        self.refresh()

    # --- Public ---

    def refresh(self):
        # wipe groups in list
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        try:
            # get groups from the query socket
            groups = self.query_helper.list_my_groups(self.user_id)
        except Exception as e:
            print('lobby refresh error:', e)
            groups = []

        self._owned_group_ids = {}
        if not groups:
            ctk.CTkLabel(self.list_frame, text="No Friends? — create a group below.",
                         text_color="gray").grid(row=0, column=0, pady=10)
        else:
            for i, row in enumerate(groups):

                group_id, group_name = row[0], row[1]
                owner_id = row[2] if row[2] else ''
                owned = (owner_id == str(self.user_id))
                label = group_name + ("   ★" if owned else "")   # star = owner
                # Bind group_id/group_name as default args so each button keeps
                # ITS OWN values. A bare `lambda: ...(group_id, group_name)` would
                # close over the loop variable and every button would select the
                # LAST group in the list.
                ctk.CTkButton(self.list_frame, text=label, anchor="w",
                              command=lambda gid=group_id, gname=group_name: self.__select_group(gid, gname)
                              ).grid(row=i, column=0, padx=5, pady=4, sticky="ew")
                if owned:
                    self._owned_group_ids[group_name] = group_id


        # checking to see if we own any groups

        if self._owned_group_ids:
            self.add_member_frame.grid(row=1, column=0, sticky="ew")
            owned_names = list(self._owned_group_ids.keys())
            self.group_menu.configure(values=owned_names)
            self.group_menu.set(owned_names[0])
        else:
            # no owned groups: hide the add-member row. The Refresh button (rowspan=2) then
            # collapses onto the create row, so it lines up with the new-group entry/button.
            self.add_member_frame.grid_forget()

    # --- Private ---

    def __select_group(self, group_id, group_name):
        self.selected_group_name = group_name
        self.selected_group_id = group_id

    def __create_group(self):
        group_name = self.new_group_entry.get().strip()
        if not group_name:
            return
        if self.query_helper.create_group(group_name, self.user_id):
            self.new_group_entry.delete(0, ctk.END)
            self.refresh()

    def __add_member(self):
        group_name = self.group_menu.get()
        username = self.add_user_entry.get().strip()
        group_id = self._owned_group_ids.get(group_name)
        if not group_id or not username:
            return
        member_id = self.query_helper.id_by_username(username)
        if not member_id:
            self.status_label.configure(text=f"No user named {username!r}", text_color="#d14249")
            return
        if self.query_helper.add_member(group_id, member_id, self.user_id):
            self.status_label.configure(text=f"Added {username} to {group_name}", text_color="#43b027")
        else:
            self.status_label.configure(text=f"Couldn't add {username}", text_color="#d14249")
        self.add_user_entry.delete(0, ctk.END)
        self.refresh()
