"""Tests for Project_Classes.prime_gui_class.PrimeGui"""
import sys
import unittest
from unittest.mock import MagicMock, patch
import socket

# ============================================================
# Stub heavy/GUI dependencies before any project-module import
# ============================================================

class _W:
    """Minimal stub for any tkinter-like widget."""
    def __init__(self, *a, **kw): pass
    def grid(self, *a, **kw): pass
    def grid_forget(self): pass
    def grid_rowconfigure(self, *a, **kw): pass
    def grid_columnconfigure(self, *a, **kw): pass
    def tkraise(self): pass
    def configure(self, *a, **kw): pass
    def place(self, *a, **kw): pass
    def bind(self, *a, **kw): pass
    def pack(self, *a, **kw): pass
    def winfo_children(self): return []

class _CTk(_W):
    def _set_appearance_mode(self, *a): pass
    def title(self, *a): pass
    def geometry(self, *a): pass
    def minsize(self, *a): pass
    def protocol(self, *a, **kw): pass
    def destroy(self): pass

_ctk = MagicMock()
_ctk.CTk = _CTk
_ctk.CTkFrame = _W
_ctk.CTkFont = MagicMock(return_value=MagicMock())
_ctk.CTkLabel = MagicMock(side_effect=lambda *a, **kw: MagicMock())
_ctk.CTkEntry = MagicMock(side_effect=lambda *a, **kw: MagicMock())
_ctk.CTkButton = MagicMock(side_effect=lambda *a, **kw: MagicMock())
_ctk.CTkImage = MagicMock(return_value=MagicMock())
sys.modules['customtkinter'] = _ctk

_pil_img = MagicMock()
_pil_img.new = MagicMock(return_value=MagicMock())
_pil = MagicMock()
_pil.Image = _pil_img
sys.modules['PIL'] = _pil
sys.modules['PIL.Image'] = _pil_img

for _dep in ('cv2', 'pyaudio', 'numpy', 'mysql', 'mysql.connector', 'keyboard'):
    sys.modules[_dep] = MagicMock()

# Reload project modules so they pick up the stubs
for _key in list(sys.modules.keys()):
    if _key.startswith('Project_Classes'):
        del sys.modules[_key]

from Project_Classes.prime_gui_class import PrimeGui


# ============================================================
# Helpers
# ============================================================

def _make_sockets():
    # video, text, audio, query, announcements
    return [MagicMock(spec=socket.socket) for _ in range(5)]

def _start_patchers(*targets):
    patchers = [patch(t) for t in targets]
    mocks = [p.start() for p in patchers]
    return patchers, mocks

def _stop_patchers(patchers):
    for p in patchers:
        p.stop()


# ============================================================
# Test classes
# ============================================================

class TestPrimeGuiInit(unittest.TestCase):

    _PATCHES = (
        'Project_Classes.prime_gui_class.TalkHobiLogin',
        'Project_Classes.prime_gui_class.ChatsClass',
        'Project_Classes.prime_gui_class.threading.Thread',
    )

    def setUp(self):
        self._patchers, (self.ml, self.mc, self.mt) = _start_patchers(*self._PATCHES)
        self._login_inst = MagicMock()
        self._login_inst.user_id = None
        self.ml.return_value = self._login_inst
        self.mt.return_value = MagicMock()
        self.socks = _make_sockets()
        self.gui = PrimeGui(*self.socks)

    def tearDown(self):
        _stop_patchers(self._patchers)

    def test_video_socket_stored(self):
        self.assertIs(self.gui.video_socket, self.socks[0])

    def test_text_socket_stored(self):
        self.assertIs(self.gui.text_socket, self.socks[1])

    def test_audio_socket_stored(self):
        self.assertIs(self.gui.audio_socket, self.socks[2])

    def test_query_socket_stored(self):
        self.assertIs(self.gui.query_socket, self.socks[3])

    def test_login_frame_created_with_correct_args(self):
        self.ml.assert_called_once_with(self.gui, self.socks[3])

    def test_login_frame_registered_in_frames(self):
        self.assertIs(self.gui.frames['login'], self._login_inst)

    def test_daemon_thread_started(self):
        self.mt.assert_called_once()
        _, kwargs = self.mt.call_args
        self.assertTrue(kwargs.get('daemon'))
        self.mt.return_value.start.assert_called_once()

    def test_title_set_to_client(self):
        with patch.object(_CTk, 'title') as mock_title:
            PrimeGui(*_make_sockets())
            mock_title.assert_called_with("Client")

    def test_geometry_set(self):
        with patch.object(_CTk, 'geometry') as mock_geo:
            PrimeGui(*_make_sockets())
            mock_geo.assert_called_with("1100x720")

    def test_close_handler_registered(self):
        with patch.object(_CTk, 'protocol') as mock_proto:
            gui = PrimeGui(*_make_sockets())
            mock_proto.assert_called_once_with("WM_DELETE_WINDOW", gui.on_close)


class TestPrimeGuiShowFrame(unittest.TestCase):

    _PATCHES = (
        'Project_Classes.prime_gui_class.TalkHobiLogin',
        'Project_Classes.prime_gui_class.ChatsClass',
        'Project_Classes.prime_gui_class.threading.Thread',
    )

    def setUp(self):
        self._patchers, (self.ml, self.mc, self.mt) = _start_patchers(*self._PATCHES)
        self._login_inst = MagicMock()
        self._login_inst.user_id = None
        self.ml.return_value = self._login_inst
        self.mt.return_value = MagicMock()
        self.gui = PrimeGui(*_make_sockets())
        self._login_inst.reset_mock()

    def tearDown(self):
        _stop_patchers(self._patchers)

    def test_active_frame_is_gridded(self):
        self.gui.show_frame('login')
        self._login_inst.grid.assert_called_with(row=0, column=0, sticky="nsew")

    def test_active_frame_is_raised(self):
        self.gui.show_frame('login')
        self._login_inst.tkraise.assert_called_once()

    def test_inactive_frame_is_forgotten(self):
        inactive = MagicMock()
        self.gui.frames['chats'] = inactive
        self.gui.show_frame('login')
        inactive.grid_forget.assert_called_once()

    def test_inactive_frame_enter_chat_not_called(self):
        inactive = MagicMock()
        self.gui.frames['chats'] = inactive
        self.gui.show_frame('login')
        inactive.enter_chat.assert_not_called()

    def test_enter_chat_called_on_active_frame(self):
        chats = MagicMock()
        self.gui.frames['chats'] = chats
        self.gui.show_frame('chats')
        chats.enter_chat.assert_called_once()

    def test_enter_chat_exception_is_swallowed(self):
        self._login_inst.enter_chat = MagicMock(side_effect=RuntimeError("no enter_chat"))
        self.gui.show_frame('login')  # should not raise

    def test_multiple_inactive_frames_all_forgotten(self):
        frame_a = MagicMock()
        frame_b = MagicMock()
        self.gui.frames['a'] = frame_a
        self.gui.frames['b'] = frame_b
        self.gui.show_frame('login')
        frame_a.grid_forget.assert_called_once()
        frame_b.grid_forget.assert_called_once()


class TestPrimeGuiLogpageLoop(unittest.TestCase):

    _PATCHES = (
        'Project_Classes.prime_gui_class.TalkHobiLogin',
        'Project_Classes.prime_gui_class.LobbyClass',
        'Project_Classes.prime_gui_class.ChatsClass',
        'Project_Classes.prime_gui_class.threading.Thread',
    )

    def setUp(self):
        self._patchers, (self.ml, self.mlobby, self.mc, self.mt) = _start_patchers(*self._PATCHES)
        self._login_inst = MagicMock()
        self._login_inst.user_id = None
        self.ml.return_value = self._login_inst
        self.mt.return_value = MagicMock()
        self.socks = _make_sockets()
        self.gui = PrimeGui(*self.socks)

    def tearDown(self):
        _stop_patchers(self._patchers)

    def _run_loop(self, user_id='42', group_id='3'):
        self._login_inst.user_id = user_id
        lobby_inst = MagicMock()
        lobby_inst.selected_group_id = group_id
        self.mlobby.return_value = lobby_inst
        mock_chat_inst = MagicMock()
        self.mc.return_value = mock_chat_inst
        with patch.object(self.gui, 'show_frame') as mock_show:
            self.gui._PrimeGui__logpage_loop()
        return mock_chat_inst, mock_show

    def test_user_id_stored_on_gui(self):
        self._run_loop('7')
        self.assertEqual(self.gui.user_id, '7')

    def test_lobby_created_with_user_and_query_sock(self):
        self._run_loop('7')
        self.mlobby.assert_called_once_with(self.gui, '7', self.socks[3])

    def test_chat_connector_created_with_correct_args(self):
        self._run_loop('42', '9')
        self.mc.assert_called_once_with(
            self.gui, '42', '9',
            self.socks[0], self.socks[1], self.socks[2], self.socks[3], self.socks[4]
        )

    def test_chats_frame_registered(self):
        mock_chat_inst, _ = self._run_loop('1')
        self.assertIs(self.gui.frames['chats'], mock_chat_inst)

    def test_show_frame_shows_lobby_then_chats(self):
        _, mock_show = self._run_loop('99')
        shown = [c.args[0] for c in mock_show.call_args_list]
        self.assertEqual(shown, ['lobby', 'chats'])

    def test_loop_uses_login_user_id(self):
        self._run_loop('55')
        self.mc.assert_called_once()
        call_args = self.mc.call_args[0]
        self.assertEqual(call_args[1], '55')


class TestPrimeGuiOnClose(unittest.TestCase):

    _PATCHES = (
        'Project_Classes.prime_gui_class.TalkHobiLogin',
        'Project_Classes.prime_gui_class.ChatsClass',
        'Project_Classes.prime_gui_class.threading.Thread',
    )

    def setUp(self):
        self._patchers, (self.ml, self.mc, self.mt) = _start_patchers(*self._PATCHES)
        self._login_inst = MagicMock()
        self._login_inst.user_id = None
        self.ml.return_value = self._login_inst
        self.mt.return_value = MagicMock()
        self.socks = _make_sockets()
        self.gui = PrimeGui(*self.socks)

    def tearDown(self):
        _stop_patchers(self._patchers)

    def test_all_sockets_closed(self):
        with patch.object(self.gui, 'destroy'):
            self.gui.on_close()
        for s in self.socks:
            s.close.assert_called_once()

    def test_window_destroyed(self):
        with patch.object(self.gui, 'destroy') as mock_destroy:
            self.gui.on_close()
        mock_destroy.assert_called_once()

    def test_no_chats_frame_does_not_raise(self):
        # only the login frame exists -> on_close must still close + destroy
        with patch.object(self.gui, 'destroy'):
            self.gui.on_close()  # should not raise

    def test_chat_components_closed(self):
        chat_a, chat_b = MagicMock(), MagicMock()
        chats_frame = MagicMock()
        chats_frame.chats = {'VideoGui': chat_a, 'AudioClient': chat_b}
        self.gui.frames['chats'] = chats_frame
        with patch.object(self.gui, 'destroy'):
            self.gui.on_close()
        chat_a.close.assert_called_once()
        chat_b.close.assert_called_once()

    def test_failing_component_close_is_swallowed(self):
        bad = MagicMock()
        bad.close.side_effect = RuntimeError("boom")
        chats_frame = MagicMock()
        chats_frame.chats = {'VideoGui': bad}
        self.gui.frames['chats'] = chats_frame
        with patch.object(self.gui, 'destroy') as mock_destroy:
            self.gui.on_close()  # should not raise
        mock_destroy.assert_called_once()


if __name__ == '__main__':
    unittest.main()
