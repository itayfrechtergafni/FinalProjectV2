"""Tests for Project_Classes.group_client.ClientQueryHelper.

Mocks the query socket, so it exercises the request encoding and the
COLSEP/ROWSEP reply parsing without a server or MySQL.
"""
import unittest
from unittest.mock import MagicMock
import socket

from Project_Classes.protocol_translator import SEP, COLSEP, ROWSEP, sql_query_flags
from database_classes.client_query_helper import ClientQueryHelper


def _sock(reply: bytes):
    s = MagicMock(spec=socket.socket)
    s.getpeername.return_value = ('localhost', 3008)
    s.recvfrom.return_value = (reply, ('localhost', 3008))
    return s


class TestRequestEncoding(unittest.TestCase):

    def test_create_group_request(self):
        s = _sock(sql_query_flags['create_group'] + SEP + b'42')
        ClientQueryHelper(s).create_group('myteam', 7)
        sent = s.sendto.call_args[0][0]
        self.assertEqual(sent, sql_query_flags['create_group'] + SEP + b'myteam' + SEP + b'7')

    def test_add_member_request(self):
        s = _sock(sql_query_flags['add_member'] + SEP + b'True')
        ClientQueryHelper(s).add_member(3, 9, 7)
        sent = s.sendto.call_args[0][0]
        self.assertEqual(sent, sql_query_flags['add_member'] + SEP + b'3' + SEP + b'9' + SEP + b'7')


class TestReplyParsing(unittest.TestCase):

    def test_create_group_returns_id(self):
        c = ClientQueryHelper(_sock(sql_query_flags['create_group'] + SEP + b'42'))
        self.assertEqual(c.create_group('x', 1), '42')

    def test_create_group_empty_is_none(self):
        c = ClientQueryHelper(_sock(sql_query_flags['create_group'] + SEP + b''))
        self.assertIsNone(c.create_group('x', 1))

    def test_list_my_groups(self):
        payload = (b'1' + COLSEP + b'team a' + COLSEP + b'7'
                   + ROWSEP + b'2' + COLSEP + b'team b' + COLSEP + b'9')
        c = ClientQueryHelper(_sock(sql_query_flags['groups_by_user_ID'] + SEP + payload))
        self.assertEqual(c.list_my_groups(7),
                         [('1', 'team a', '7'), ('2', 'team b', '9')])

    def test_list_my_groups_empty(self):
        c = ClientQueryHelper(_sock(sql_query_flags['groups_by_user_ID'] + SEP + b''))
        self.assertEqual(c.list_my_groups(7), [])

    def test_list_members(self):
        payload = (b'7' + COLSEP + b'alice' + COLSEP + b'owner'
                   + ROWSEP + b'9' + COLSEP + b'bob' + COLSEP + b'member')
        c = ClientQueryHelper(_sock(sql_query_flags['members_by_group_ID'] + SEP + payload))
        self.assertEqual(c.list_members(1),
                         [('7', 'alice', 'owner'), ('9', 'bob', 'member')])

    def test_is_member_true(self):
        c = ClientQueryHelper(_sock(sql_query_flags['is_member'] + SEP + b'True'))
        self.assertTrue(c.is_member(1, 7))

    def test_is_member_false(self):
        c = ClientQueryHelper(_sock(sql_query_flags['is_member'] + SEP + b'False'))
        self.assertFalse(c.is_member(1, 7))

    def test_is_owner_true(self):
        c = ClientQueryHelper(_sock(sql_query_flags['is_owner'] + SEP + b'True'))
        self.assertTrue(c.is_owner(1, 7))

    def test_is_owner_false(self):
        c = ClientQueryHelper(_sock(sql_query_flags['is_owner'] + SEP + b'False'))
        self.assertFalse(c.is_owner(1, 7))

    def test_group_id_by_name(self):
        c = ClientQueryHelper(_sock(sql_query_flags['group_ID_by_group_name'] + SEP + b'5'))
        self.assertEqual(c.group_id_by_name('team a'), '5')

    def test_id_by_username(self):
        c = ClientQueryHelper(_sock(sql_query_flags['user_ID_by_username'] + SEP + b'12'))
        self.assertEqual(c.id_by_username('bob'), '12')

    def test_id_by_username_unknown_is_none(self):
        c = ClientQueryHelper(_sock(sql_query_flags['user_ID_by_username'] + SEP + b''))
        self.assertIsNone(c.id_by_username('nobody'))


if __name__ == '__main__':
    unittest.main()
