
import os
import sys

# make Project_Classes / database_classes / project_dictionary importable
# no matter what directory this is launched from
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import socket
import threading
from Project_Classes.general_classes import ServerFunctions

VIDEO_PORT, TEXT_PORT, AUDIO_PORT, QUERY_PORT, ANNOUNCE_PORT = 3005, 3006, 3007, 3008, 3009
VIDEO_CHUNK, TEXT_CHUNK, AUDIO_CHUNK = 50000, 1024, 2048


def _bind(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))
    return sock


def main():
    query_sock = _bind(QUERY_PORT)
    audio_sock = _bind(AUDIO_PORT)
    text_sock = _bind(TEXT_PORT)
    video_sock = _bind(VIDEO_PORT)
    announce_sock = _bind(ANNOUNCE_PORT)

    # keep references so the servers (and their handler threads) stay alive
    servers = [
        ServerFunctions(query_sock, TEXT_CHUNK, "database_server", "query"),
        ServerFunctions(audio_sock, AUDIO_CHUNK, "chat_server", "audio"),
        ServerFunctions(text_sock, TEXT_CHUNK, "chat_server", "text"),
        ServerFunctions(video_sock, VIDEO_CHUNK, "chat_server", "video"),
        ServerFunctions(announce_sock, TEXT_CHUNK, "announcements_server", "announcements"),
    ]

    print(f"Servers running:  video={VIDEO_PORT}  text={TEXT_PORT}  "
          f"audio={AUDIO_PORT}  query={QUERY_PORT}  announcements={ANNOUNCE_PORT}")
    print("Press Ctrl+C to stop.")
    try:
        threading.Event().wait()   # block forever
    except KeyboardInterrupt:
        print("\nstopping servers")
        os._exit(0)   # force-exit (the handler threads block on recvfrom)


if __name__ == "__main__":
    main()
