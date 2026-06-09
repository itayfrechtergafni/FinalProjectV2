"""Tests for Project_Classes.protocol — the loader that reads the
project_dictionary/*.txt files into separators and flag dictionaries.

Pure Python (only depends on pathlib), so no stubbing is needed.
"""
import unittest

from Project_Classes import protocol_translator


class TestSeparators(unittest.TestCase):

    def test_separators_are_bytes(self):
        for sep in (protocol_translator.SEP, protocol_translator.COLSEP, protocol_translator.ROWSEP):
            self.assertIsInstance(sep, bytes)

    def test_sep_value(self):
        self.assertEqual(protocol_translator.SEP, b"###_DATA_SEPARATOR_###")

    def test_separators_are_distinct(self):
        self.assertEqual(len({protocol_translator.SEP, protocol_translator.COLSEP, protocol_translator.ROWSEP}), 3)


class TestSqlQueryFlags(unittest.TestCase):

    def test_values_are_bytes(self):
        for code in protocol_translator.sql_query_flags.values():
            self.assertIsInstance(code, bytes)

    def test_known_user_flags(self):
        self.assertEqual(protocol_translator.sql_query_flags['err'], b'00')
        self.assertEqual(protocol_translator.sql_query_flags['username_login'], b'01')
        self.assertEqual(protocol_translator.sql_query_flags['user_ID_by_username'], b'02')
        self.assertEqual(protocol_translator.sql_query_flags['username_by_user_ID'], b'03')

    def test_group_flags_present(self):
        for name in ('create_group', 'delete_group', 'rename_group',
                     'add_member', 'remove_member', 'groups_by_user_ID',
                     'members_by_group_ID', 'is_member', 'group_ID_by_group_name'):
            self.assertIn(name, protocol_translator.sql_query_flags)

    def test_codes_are_unique(self):
        codes = list(protocol_translator.sql_query_flags.values())
        self.assertEqual(len(codes), len(set(codes)))


class TestClientActions(unittest.TestCase):

    def test_values_are_byte_codes(self):
        for code in protocol_translator.client_actions.values():
            self.assertIsInstance(code, bytes)

    def test_expected_actions_present(self):
        for name in ('kill', 'stop', 'mute', 'unmute', 'join'):
            self.assertIn(name, protocol_translator.client_actions)

    def test_known_action_codes(self):
        self.assertEqual(protocol_translator.client_actions['kill'], b'01')
        self.assertEqual(protocol_translator.client_actions['join'], b'05')

    def test_codes_are_unique(self):
        codes = list(protocol_translator.client_actions.values())
        self.assertEqual(len(codes), len(set(codes)))


if __name__ == '__main__':
    unittest.main()
