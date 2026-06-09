import customtkinter as ctk

class VideoBox(ctk.CTkFrame):
    def __init__(self, master, participant_name):
        super().__init__(
            master,

            fg_color='#1f538d',width=320,height=240
        )

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.video_display = ctk.CTkLabel(
            self,
            text="",fg_color="transparent",height=240,width=320

        )
        self.video_display.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.info_overlay = ctk.CTkFrame(
            self,
            fg_color="#1a1a1a",
            corner_radius=10,
            height=28
        )
        self.info_overlay.grid(row=0, column=0, sticky="sw", padx=12, pady=12)

        self.name_label = ctk.CTkLabel(
            self.info_overlay,
            text=participant_name,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white",
            padx=10
        )
        self.name_label.pack(side="left")

    def switch_color(self):
        if self.cget('fg_color') == "#1f538d":
            self.configure(fg_color="#d14249")
        elif self.cget('fg_color') == "#d14249":
            self.configure(fg_color="#1f538d")

    def get_text(self):
        return self.video_display.cget('text')
    def config(self, image, text):
        self.video_display.configure(text=text, image=image)