import socket
import time
from database_classes.server_database_class import *
from database_classes.group_database_class import GroupDatabase
import queue
import threading
from Project_Classes.protocol_translator import SEP, COLSEP, ROWSEP, sql_query_flags, client_actions
from Encryption.encrypt_class import (
    client_send, client_recv,
    secure_sendto, aes_decrypt_bytes,
    create_rsa_keys, server_handle_handshake,
)


class SockFunctions:
    def __init__(self, sock: socket.socket,query_sock: socket.socket, user_id = '0', group_id = '0'):

        self.sock = sock
        self.query_sock = query_sock
        self.alive = False
        self.server_addr = self.sock.getpeername()
        self.query_addr = self.query_sock.getpeername()
        self.user_id = user_id
        self.group_id = group_id
        self.name = ""
        self.chatters_dict = {}
        if self.user_id:
            print(f"user id: {self.user_id}")
            self.name = self.find_username_by_id(self.user_id)
            print(f"my name {self.name}")
            self.chatters_dict[self.user_id] = self.name


        client_send(self.sock, self.user_id.encode(), self.server_addr)
        print(f"handshake with server")

    def find_username_by_id(self, user_id):
        client_send(self.query_sock,
                    sql_query_flags['username_by_user_ID'] + SEP + user_id.encode(), self.query_addr)
        query_answer, _ = client_recv(self.query_sock, 1024)
        query_answer = query_answer.split(SEP)

        return query_answer[1].decode()

    def send_join(self):
        # Tell the chat server which group this socket belongs to:
        #   join + SEP + user_id + SEP + group_id
        client_send(self.sock,
                    client_actions['join'] + SEP + self.user_id.encode() + SEP + self.group_id.encode(),
                    self.server_addr)



class ServerFunctions(UserDatabase, GroupDatabase):
    def __init__(self, sock: socket.socket, CHUNK_SIZE: int,server_type: str,server_name: str):
        UserDatabase.__init__(self, 'talkhobi', 'user_table', 5)
        GroupDatabase.__init__(self)
        self.sock = sock
        self.is_streaming = True
        self.server_name = server_name
        self.addr_list = []
        self.addr_to_group = {}        #  addr : group_id
        self.group_members_live = {}   # group_id -> set of live addrs
        self.data_queue = queue.Queue()  # list of what I am sending to the clients.
        self.CHUNK_SIZE = CHUNK_SIZE
        # --- Encryption ---
        # This server's RSA key pair (handed out during the handshake) and the
        # client AES keys we collect: {client_addr: aes_key}
        self.rsa_private, self.rsa_public = create_rsa_keys()
        self.client_keys = {}
        # An "announcements_server" relays exactly like a chat_server, except only
        # the group owner is allowed to broadcast (everyone else is read-only).
        self.owner_only = (server_type == "announcements_server")
        self._control_flags = set(client_actions.values())
        if server_type in ("chat_server", "announcements_server"):
            print("chat server")
            threading.Thread(target=self.__chat_sending_handler).start()
            threading.Thread(target=self.__chat_receiving_handler).start()
        elif server_type == "database_server":
            threading.Thread(target=self.__user_query_handler).start()
    # --- Live Chat Handlers ---

    def __add_to_group(self, addr, group_id):
        self.addr_to_group[addr] = group_id
        self.group_members_live.setdefault(group_id, set()).add(addr)

    def __remove_from_group(self, addr):
        group_id = self.addr_to_group.pop(addr, None)
        members = self.group_members_live.get(group_id)
        if members is not None:
            members.discard(addr)
            if not members:
                del self.group_members_live[group_id]

    def __chat_receiving_handler(self):

        while self.is_streaming:
            try:
                raw, addr = self.sock.recvfrom(self.CHUNK_SIZE * 2)

                # RSA->AES handshake
                if server_handle_handshake(self.sock, raw, addr,
                                           self.rsa_private, self.rsa_public, self.client_keys):
                    continue
                key = self.client_keys.get(addr)
                if key is None:
                    continue  # data before handshake completed -> ignore
                out_data = aes_decrypt_bytes(raw, key)

                parts = out_data.split(SEP)
                flag = parts[0]

                # join handshake: join + SEP + user_id + SEP + group_id
                if flag == client_actions['join']:
                    user_id, group_id = parts[1].decode(), parts[2].decode()
                    if self.is_member(int(group_id), int(user_id)):
                        self.__add_to_group(addr, group_id)
                        print(f"{addr} joined group {group_id} on {self.server_name}")
                    continue

                # ignore anything from an address that hasn't joined a group
                group_id = self.addr_to_group.get(addr)
                if group_id is None:
                    continue


                if self.owner_only and flag not in self._control_flags:
                    sender_id = parts[-1].decode()
                    if not self.is_owner(int(group_id), int(sender_id)):
                        continue


                if len(out_data) > 1:
                    self.data_queue.put((out_data, addr, group_id))

                if flag == client_actions['kill']:
                    self.__remove_from_group(addr)

            except OSError:
                break
            except Exception as e:
                print('chat receiver error:', e)
                continue

    def __chat_sending_handler(self):
        while True:
            try:
                if not self.data_queue.empty():
                    out_data, sender_addr, group_id = self.data_queue.get_nowait()
                    for addr in list(self.group_members_live.get(group_id, ())):
                        if addr != sender_addr:
                            key = self.client_keys.get(addr)
                            if key is not None:
                                secure_sendto(self.sock, out_data, addr, key)
                else:
                    time.sleep(0.01)
            except OSError:
                break

    # --- Database Query Socket Handler ---
    def __user_query_handler(self):

        while self.is_streaming:
            try:
                raw, addr = self.sock.recvfrom(self.CHUNK_SIZE * 2)

                # RSA->AES handshake before any real query.
                if server_handle_handshake(self.sock, raw, addr,
                                           self.rsa_private, self.rsa_public, self.client_keys):
                    continue
                key = self.client_keys.get(addr)
                if key is None:
                    continue
                out_data = aes_decrypt_bytes(raw, key)

                if addr not in self.addr_list:
                    print(f"New query socket connected at: {addr}")
                    self.addr_list.append(addr)

                if out_data and out_data.count(SEP) >= 1:
                    out_data = out_data.split(SEP)

                    answer = ''
                    flag_key = 'err'

                    if out_data[0] == sql_query_flags['username_login']:
                        flag_key = 'username_login'
                        user_name = out_data[1].decode()
                        password = out_data[2].decode()
                        if self.search_user_by_user_name_and_password(user_name,password):
                            answer = 'True'
                        else:
                            answer = 'False'


                    elif out_data[0] == sql_query_flags['user_ID_by_username']:
                        flag_key = 'user_ID_by_username'
                        user_name = out_data[1].decode()

                        if not self.is_user_name_available(user_name):
                            answer = self.search_id_by_name(user_name)

                    elif out_data[0] == sql_query_flags['username_by_user_ID']:
                        flag_key = 'username_by_user_ID'
                        user_id = out_data[1].decode()
                        answer = self.search_name_by_id(user_id)

                    elif out_data[0] == sql_query_flags['username_available']:
                        flag_key = 'username_available'
                        user_name = out_data[1].decode()
                        if self.is_user_name_available(user_name):
                            answer = 'True'
                        else:
                            answer = 'False'

                    elif out_data[0] == sql_query_flags['email_login']:
                        flag_key = 'email_login'
                        email = out_data[1].decode()
                        password = out_data[2].decode()
                        if self.search_user_by_email_and_password(email,password):
                            answer = 'True'
                        else:
                            answer = 'False'

                    elif out_data[0] == sql_query_flags['register_user']:
                        # register_user + SEP + username + SEP + first + SEP + last + SEP + email + SEP + password
                        flag_key = 'register_user'
                        uname = out_data[1].decode()
                        fname = out_data[2].decode()
                        lname = out_data[3].decode()
                        email = out_data[4].decode()
                        password = out_data[5].decode()
                        if not self.is_user_name_available(uname):
                            answer = 'USERNAME_TAKEN'
                        elif not self.is_email_available(email):
                            answer = 'EMAIL_TAKEN'
                        else:
                            new_id = self.insert_user(uname, fname, lname, email, password)
                            answer = str(new_id) if new_id else 'ERROR'

                    # --- Group flags ---
                    elif out_data[0] == sql_query_flags['create_group']:
                        flag_key = 'create_group'
                        group_name = out_data[1].decode()
                        owner_id = int(out_data[2].decode())
                        new_id = self.create_group(group_name, owner_id)
                        answer = str(new_id) if new_id else ''

                    elif out_data[0] == sql_query_flags['delete_group']:
                        flag_key = 'delete_group'
                        group_id = int(out_data[1].decode())
                        requester_id = int(out_data[2].decode())
                        answer = 'True' if (self.is_owner(group_id, requester_id)
                                            and self.delete_group(group_id)) else 'False'

                    elif out_data[0] == sql_query_flags['rename_group']:
                        flag_key = 'rename_group'
                        group_id = int(out_data[1].decode())
                        new_name = out_data[2].decode()
                        requester_id = int(out_data[3].decode())
                        answer = 'True' if (self.is_owner(group_id, requester_id)
                                            and self.rename_group(group_id, new_name)) else 'False'

                    elif out_data[0] == sql_query_flags['add_member']:
                        flag_key = 'add_member'
                        group_id = int(out_data[1].decode())
                        member_id = int(out_data[2].decode())
                        requester_id = int(out_data[3].decode())
                        answer = 'True' if (self.is_owner(group_id, requester_id)
                                            and self.add_member(group_id, member_id)) else 'False'

                    elif out_data[0] == sql_query_flags['remove_member']:
                        flag_key = 'remove_member'
                        group_id = int(out_data[1].decode())
                        member_id = int(out_data[2].decode())
                        requester_id = int(out_data[3].decode())
                        answer = 'True' if (self.is_owner(group_id, requester_id)
                                            and self.remove_member(group_id, member_id)) else 'False'

                    elif out_data[0] == sql_query_flags['groups_by_user_ID']:
                        flag_key = 'groups_by_user_ID'
                        user_id = int(out_data[1].decode())
                        col = COLSEP.decode()
                        row = ROWSEP.decode()
                        answer = row.join(
                            col.join(str(c) for c in group_row)
                            for group_row in self.list_groups_for_user(user_id))

                    elif out_data[0] == sql_query_flags['members_by_group_ID']:
                        flag_key = 'members_by_group_ID'
                        group_id = int(out_data[1].decode())
                        col = COLSEP.decode()
                        row = ROWSEP.decode()
                        answer = row.join(
                            col.join(str(c) for c in member_row)
                            for member_row in self.list_members(group_id))

                    elif out_data[0] == sql_query_flags['is_member']:
                        flag_key = 'is_member'
                        group_id = int(out_data[1].decode())
                        member_id = int(out_data[2].decode())
                        answer = 'True' if self.is_member(group_id, member_id) else 'False'

                    elif out_data[0] == sql_query_flags['is_owner']:
                        flag_key = 'is_owner'
                        group_id = int(out_data[1].decode())
                        member_id = int(out_data[2].decode())
                        answer = 'True' if self.is_owner(group_id, member_id) else 'False'

                    elif out_data[0] == sql_query_flags['group_ID_by_group_name']:
                        flag_key = 'group_ID_by_group_name'
                        group_name = out_data[1].decode()
                        gid = self.get_group_id_by_name(group_name)
                        answer = str(gid) if gid else ''

                    packet = sql_query_flags[flag_key]+SEP+answer.encode()
                    secure_sendto(self.sock, packet, addr, key)

            except OSError:
                break
            except Exception as e:
                print('query handler error:', e)
                continue


    def __close_conns(self):
        print('closing conn')
        self.is_streaming = False
        self.sock.close()

    def add_addr(self, addr):
        self.addr_list.append(addr)

    def check_addr(self, addr):
        if addr not in self.addr_list:
            return False
        return True

    def print_addr_list(self):
        print(self.addr_list)

