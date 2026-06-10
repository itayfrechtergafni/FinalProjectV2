import socket
from Project_Classes.protocol_translator import SEP, COLSEP, ROWSEP, sql_query_flags
from Encryption.encrypt_class import secure_sendto, secure_recvfrom

RECV_SIZE = 65535


class ClientQueryHelper:
    def __init__(self, query_sock: socket.socket):
        self.query_sock = query_sock
        self.query_addr = query_sock.getpeername()

    def __query(self, flag_name, *args): # *args means all args
        payload = sql_query_flags[flag_name]
        for arg in args:
            payload += SEP + str(arg).encode()
        secure_sendto(self.query_sock, payload, self.query_addr) # sends after adding all parameters needed for query
        reply = secure_recvfrom(self.query_sock, RECV_SIZE)[0] # recvs from server
        parts = reply.split(SEP, 1)   # [flag, answer]
        return parts[1] if len(parts) > 1 else b''

    def __parse_rows(self, data: bytes):
        # rows joined by ROWSEP, columns within a row joined by COLSEP
        if not data:
            return []
        return [tuple(col.decode() for col in row.split(COLSEP))
                for row in data.split(ROWSEP)]





    # --- account actions ---

    def register_user(self, username, first, last, email, password):
        return self.__query('register_user', username, first, last, email, password).decode()

    # --- group actions ---

    def create_group(self, name, owner_id):
        ans = self.__query('create_group', name, owner_id).decode()
        return ans or None

    def delete_group(self, group_id, requester_id):
        return self.__query('delete_group', group_id, requester_id) == b'True'

    def rename_group(self, group_id, new_name, requester_id):
        return self.__query('rename_group', group_id, new_name, requester_id) == b'True'

    def add_member(self, group_id, user_id, requester_id):
        return self.__query('add_member', group_id, user_id, requester_id) == b'True'

    def remove_member(self, group_id, user_id, requester_id):
        return self.__query('remove_member', group_id, user_id, requester_id) == b'True'

    def list_my_groups(self, user_id):
        # each row: (group_id, group_name, owner_id)
        return self.__parse_rows(self.__query('groups_by_user_ID', user_id))

    def list_members(self, group_id):
        # each row: (user_id, user_name, role)
        return self.__parse_rows(self.__query('members_by_group_ID', group_id))

    def is_member(self, group_id, user_id):
        return self.__query('is_member', group_id, user_id) == b'True'

    def is_owner(self, group_id, user_id):
        return self.__query('is_owner', group_id, user_id) == b'True'

    def group_id_by_name(self, name):
        ans = self.__query('group_ID_by_group_name', name).decode()
        return ans or None

    def id_by_username(self, username):
        ans = self.__query('user_ID_by_username', username).decode()
        return ans or None
