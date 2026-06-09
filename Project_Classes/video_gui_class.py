import customtkinter as ctk
import queue
import threading
import socket
import cv2
import time
import numpy as np
from PIL import Image
import math
from Project_Classes.general_classes import SockFunctions, SEP, client_actions
from Project_Classes.video_box import VideoBox


CHUNK_SIZE = 50000

black_ctk_image = ctk.CTkImage(dark_image=Image.new("RGB", color="black", size=(640, 480)), size=(320, 240))
thread_lock = threading.Lock()


class VideoGui(SockFunctions, ctk.CTkFrame):
    def __init__(self,  sock: socket.socket,query_sock : socket.socket, parent : ctk.CTkFrame,user_id = '0', group_id = '0'):

        # --- Inheritance init ---
        SockFunctions.__init__(self, sock=sock,query_sock=query_sock,user_id=user_id,group_id=group_id)
        ctk.CTkFrame.__init__(self, parent)

        # --- Queue & Dict Init ---
        self.new_images = queue.Queue()
        self.box_dict: dict[str, VideoBox] = {}

        # --- Threading Events init ---
        self.camera_active = threading.Event()
        self.socket_active = threading.Event()
        self.running = True   # cleared on shutdown to stop the worker loops

        # --- Camera init ---
        self.cap = cv2.VideoCapture(0)
        self.__init_cap()

        # -- GUI init ---
        self.video_gui_frame = ctk.CTkFrame(self)
        self.video_gui_frame.pack(fill="both", expand=True)
        self.video_gui_frame.grid_rowconfigure(0, weight=1)
        self.video_gui_frame.grid_rowconfigure(1, weight=0)
        self.video_gui_frame.grid_columnconfigure(0, weight=1)

        self.video_container = ctk.CTkFrame(self.video_gui_frame, fg_color="transparent")
        self.video_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)



        threading.Thread(target=self.__input_handler, daemon=True).start()
        threading.Thread(target=self.__output_handler, daemon=True).start()
        self.__update_video_stream()
        self.__update_video_stream()

    # --- Public Methods ---

    def leave_chat(self):
        if self.socket_active.is_set() and self.alive:
            print('leave chat')
            self.camera_active.clear()
            self.socket_active.clear()
            for widget in self.video_container.winfo_children():
                widget.destroy()
            self.box_dict.clear()
            self.chatters_dict = {}
            self.new_images = queue.Queue()
            self.sock.sendto(client_actions['kill']+SEP+self.user_id.encode(), self.server_addr)
            self.alive = False

    def enter_chat(self):
        if not self.alive and not self.socket_active.is_set():
            self.alive = True
            self.chatters_dict[self.user_id] = self.name
            self.__add_box(self.name)
            self.send_join()   # register this socket with our group on the server
            self.socket_active.set()
            self.camera_active.set()

    def camera_switch(self):
        if self.camera_active.is_set():
            self.camera_active.clear()
            self.new_images.put((self.name, ""))
            self.sock.sendto(client_actions['stop']+SEP+self.user_id.encode(), self.server_addr)
            print('sent stop signal to server')
            return True
        else:
            self.camera_active.set()
            return False

    # --- Visual Public Methods ---

    # Changes the outline color of a single box by address.
    def change_box_outline(self,box_addr=None):
        if box_addr is None:
            try:
                self.box_dict.get(self.name).switch_color()
            except:
                return
        else:
            try:
                self.box_dict.get(self.chatters_dict.get(box_addr)).switch_color()
            except Exception as e:
                print(e)


    # --- Private Methods ---

    def __add_box(self, username):
        if username in self.box_dict:   # already have a box for this user, don't orphan it
            return
        print('adding box for:',username)
        new_box = VideoBox(self.video_container, participant_name=str(username))
        self.box_dict[username] = new_box
        self.new_images.put((username, ""))
        self.__organize_grid()

    def __remove_box(self, username):
        self.box_dict[username].destroy()
        del self.box_dict[username]

    def __organize_grid(self):
        n = len(self.box_dict)
        if n == 0:
            return

        cols = math.ceil(math.sqrt(n)) # the sqrt of box_dict length is the proportions of a square grid.
        rows = math.ceil(n / cols)

        # Reset container weights
        for i in range(10):
            self.video_container.grid_columnconfigure(i, weight=0)
            self.video_container.grid_rowconfigure(i, weight=0)


        for i in range(cols):
            self.video_container.grid_columnconfigure(i, weight=0)
        for i in range(rows):
            self.video_container.grid_rowconfigure(i, weight=0)

        # Python sorts False (0) before True (1).
        # If it's my address, the condition is False, and it goes to the front
        ordered_widgets = sorted(
            self.box_dict.items(),
            key=lambda item: item[0] != self.name)

        # Re-place all widgets in the new grid formation
        for i, (addr, widget) in enumerate(ordered_widgets):
            r = i // cols
            c = i % cols
            widget.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")

    def __update_video_stream(self):
        while self.socket_active.is_set():
            while not self.new_images.empty() and self.alive:
                sender_username, latest_image = self.new_images.get_nowait()
                # If it's a new participant, add them to the grid
                if sender_username not in self.box_dict.keys() and sender_username in self.chatters_dict.values():
                    self.__add_box(sender_username)
                elif sender_username in self.box_dict.keys() and sender_username not in self.chatters_dict.values():
                    self.__remove_box(sender_username)

                if self.box_dict.get(sender_username):
                    if not latest_image == "":
                        self.box_dict[sender_username].config(text="", image=latest_image)
                    else:
                        if self.name != sender_username:
                            print(sender_username, 'asked for black camera')
                        self.box_dict[sender_username].config(text="Camera Off", image=black_ctk_image)
            break
        self.after(ms=10, func=self.__update_video_stream)

    def __input_handler(self):
        while self.running:
            if not self.camera_active.is_set():
                if self.cap and self.cap.isOpened():
                    self.cap.release()
                self.camera_active.wait()
                if not self.running:   # woken for shutdown
                    break
                self.__init_cap()

            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            frame = cv2.resize(frame, (640, 480))
            frame = cv2.flip(frame, 1)

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_frame)
            ctk_img = ctk.CTkImage(dark_image=pil_img, size=(int(pil_img.width / 2), int(pil_img.height / 2)))
            if self.camera_active.is_set():
                self.new_images.put((self.name, ctk_img))

                encoded, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                packet = buffer.tobytes()+SEP+self.user_id.encode()
                try:
                    self.sock.sendto(packet, self.server_addr)
                except OSError:
                    break

    def __output_handler(self):
        while self.running:
            try:
                if not self.socket_active.is_set():
                    print('waiting for video socket to be active')
                    self.socket_active.wait()

                if not self.running:
                    break

                # Read a full UDP datagram (65535 = max UDP payload). Reading only
                # CHUNK_SIZE truncates any frame larger than that, which lops off the
                # trailing "SEP + user_id" and makes the packet unparseable — so that
                # sender's video box never appears. rsplit(SEP, 1) also keeps us safe
                # if the JPEG bytes happen to contain the separator sequence.
                packet, sender_id = self.sock.recvfrom(65535)[0].rsplit(SEP, 1)
                sender_id = sender_id.decode()

                if packet == client_actions['kill']:
                    if sender_id in self.chatters_dict:
                        killer_name = self.chatters_dict.pop(sender_id)
                        self.new_images.put((killer_name, ""))

                    continue

                elif packet == client_actions['stop']:
                    if sender_id in self.chatters_dict:
                        self.new_images.put((self.chatters_dict[sender_id], ""))

                    continue

                if sender_id not in self.chatters_dict:
                    self.chatters_dict[sender_id] = self.find_username_by_id(sender_id)

                # Decode image
                data = np.frombuffer(packet, dtype=np.uint8())
                frame = cv2.imdecode(data, cv2.IMREAD_COLOR)

                if frame is not None:
                    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    captured_image = Image.fromarray(img)
                    photo_image = ctk.CTkImage(
                        dark_image=captured_image,
                        size=(int(captured_image.width / 2), int(captured_image.height / 2))
                    )
                    self.new_images.put((self.chatters_dict[sender_id], photo_image))

            except Exception as e:
                if not self.running:   # socket was closed by close()
                    break
                print(e)
                if e.args and e.args[0] == 10054:
                    break
                time.sleep(0.1)

    def close(self):
        # Stop the worker loops, release the camera and close the socket.
        self.running = False
        self.alive = False
        self.camera_active.set()    # unblock __input_handler if parked
        self.socket_active.set()    # unblock __output_handler if parked
        try:
            if self.cap and self.cap.isOpened():
                self.cap.release()
        except Exception:
            pass
        try:
            # Tell the server (and thus the other clients) we're leaving so our
            # box gets removed, then close the socket.
            self.sock.sendto(client_actions['kill']+SEP+self.user_id.encode(), self.server_addr)
        except Exception:
            pass
        try:
            self.sock.close()       # unblocks a pending recvfrom
        except Exception:
            pass

    def __init_cap(self):
        camera_index = 0
        self.cap = cv2.VideoCapture(camera_index)
        ret, frame = self.cap.read()
        while camera_index < 5:
            if not ret:
                camera_index += 1
                self.cap = cv2.VideoCapture(camera_index)
                ret, _ = self.cap.read()
            else:
                break