import pyaudio
# import wave
import socket
import threading
import time
import queue
from Project_Classes.general_classes import SockFunctions, SEP, client_actions
from Project_Classes.video_gui_class import VideoGui
from Encryption.encrypt_class import secure_sendto, secure_recvfrom
FORMAT = pyaudio.paInt16  # 16-bit resolution
CHANNELS = 1  # Mono Sound
RATE = 44100  # Sample rate (44.1kHz)
CHUNK_SIZE = 2048 # Buffer size
thread_lock = threading.Lock()






class AudioClient(SockFunctions):

    def __init__(self, sock : socket.socket,query_sock : socket.socket,video_gui : VideoGui,user_id='0', group_id='0'):

        # --- Inheritance init ---
        SockFunctions.__init__(self,sock=sock,query_sock=query_sock,user_id=user_id,group_id=group_id)

        # --- PyAudio init ---
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=FORMAT, channels=CHANNELS,
            rate=RATE, input=True, output=True,
            frames_per_buffer=CHUNK_SIZE//2,
            stream_callback=self.__callback)
        # --- Threading Events & Flags init ---

        self.mic_status = threading.Event()
        self.socket_status = threading.Event()
        self.mic_status.clear()
        self.socket_status.clear()
        self.running = True   # cleared on shutdown to stop the worker loops

        # --- Queue init ---
        self.in_queue = queue.Queue()
        self.out_queue = queue.Queue(maxsize=5)




        # --- VideoGui init ---
        self.video_gui = video_gui

        threading.Thread(target=self.__input_handler, daemon=True).start()
        threading.Thread(target=self.__output_handler, daemon=True).start()



    # --- Public Methods ---

    def set_addr(self,addr):
        self.server_addr = addr

    def mic_switch(self):
        if self.mic_status.is_set():
            print("mute")
            self.mic_status.clear()
            self.in_queue = queue.Queue()
            packet = client_actions['mute']+SEP+self.user_id.encode()
            secure_sendto(self.sock, packet, self.server_addr)
            return True
        else:
            print("unmute")
            self.mic_status.set()
            secure_sendto(self.sock, client_actions['unmute']+SEP+self.user_id.encode(), self.server_addr)
            return False

    def leave_chat(self):
        if self.socket_status.is_set():
            self.alive = False
            print("leave audio chat")
            self.in_queue = queue.Queue()
            self.socket_status.clear()
            self.mic_status.clear()
            secure_sendto(self.sock, client_actions['kill'] + SEP + self.user_id.encode(), self.server_addr)

    def enter_chat(self):
        if not self.socket_status.is_set() and not self.mic_status.is_set():
            print("enter audio chat")
            self.in_queue = queue.Queue()
            self.out_queue = queue.Queue(maxsize=5)   # drop any audio still queued for playback
            self.__drain_socket()                     # discard audio buffered while we were away
            self.alive = True
            self.send_join()   # register this socket with our group on the server
            self.socket_status.set()
            self.mic_status.set()

    def close(self):
        # Stop the worker loops, tear down the audio stream and close the socket.
        self.running = False
        self.alive = False
        self.socket_status.set()    # unblock __output_handler if parked
        self.mic_status.set()       # unblock __input_handler if parked
        try:
            if self.stream.is_active():
                self.stream.stop_stream()
            self.stream.close()
        except Exception:
            pass
        try:
            self.audio.terminate()
        except Exception:
            pass
        try:
            secure_sendto(self.sock, client_actions['kill']+SEP+self.user_id.encode(), self.server_addr)
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass


    # --- Private Methods ---

    def __drain_socket(self):
        # Throw away audio the server buffered for us while we were away so a
        # stale burst isn't played back when we re-enter the chat.
        self.sock.setblocking(False)
        try:
            while True:
                self.sock.recvfrom(CHUNK_SIZE * 2)
        except (BlockingIOError, OSError):
            pass
        finally:
            self.sock.setblocking(True)

    # Occurs every time I capture a chunk of mic data.
    def __callback(self,in_data, frame_count, time_info, status):
        if self.mic_status.is_set():
            self.in_queue.put(in_data)
        if not self.out_queue.empty():  # checking to see if I have any data to play.

            out_data = self.out_queue.get_nowait()
            return out_data, pyaudio.paContinue  # play out_data and continue.
        else:
            return b'\x00' * frame_count * 2, pyaudio.paContinue  # play silence and continue


    def __input_handler(self):
        while self.running:
            while self.alive:
                if not self.mic_status.is_set():  # checking to see if we need to send audio
                    self.mic_status.wait()
                if not self.running:   # woken for shutdown
                    return
                try:
                    in_data = self.in_queue.get(timeout=0.1)  # blocks instead of busy-waiting
                except queue.Empty:
                    continue
                try:
                    secure_sendto(self.sock, in_data, self.server_addr)
                except OSError:
                    return
            time.sleep(0.01)




    def __output_handler(self):
        while self.running:
            while self.alive:
                if not self.socket_status.is_set():  # checking to see if we need to collect audio
                    print('waiting for socket to be set')
                    self.socket_status.wait()
                    print('socket is set')
                if not self.running:   # woken for shutdown
                    return
                time.sleep(0.01)
                try:
                    out_data, sender_addr = secure_recvfrom(self.sock, CHUNK_SIZE * 2)
                except OSError:
                    return
                if out_data.count(SEP) >= 1:
                    if out_data.split(SEP)[0] == client_actions['mute'] or out_data.split(SEP)[0] == client_actions['unmute']:
                        print('muting/unmute friend')
                        self.video_gui.after(0, func=lambda: self.video_gui.change_box_outline(out_data.split(SEP)[1].decode()))
                else:
                    try:
                        self.out_queue.put_nowait(out_data)
                    except queue.Full:
                        try:
                            self.out_queue.get_nowait()
                        except queue.Empty:
                            pass
                        try:
                            self.out_queue.put_nowait(out_data)
                        except queue.Full:
                            pass
            time.sleep(0.01)




