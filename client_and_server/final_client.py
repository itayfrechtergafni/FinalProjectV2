import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import socket
from Project_Classes.prime_gui_class import PrimeGui

HOST = '192.168.98.103'

VIDEO_PORT, TEXT_PORT, AUDIO_PORT, QUERY_PORT, ANNOUNCE_PORT = 3005, 3006, 3007, 3008, 3009


def connect(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect((HOST, port))
    return sock


if __name__ == "__main__":
    video_sock = connect(VIDEO_PORT)
    text_sock = connect(TEXT_PORT)
    audio_sock = connect(AUDIO_PORT)
    query_sock = connect(QUERY_PORT)
    announce_sock = connect(ANNOUNCE_PORT)

    PrimeGui(video_sock, text_sock, audio_sock, query_sock, announce_sock).mainloop()
