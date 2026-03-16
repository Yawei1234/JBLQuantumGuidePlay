import customtkinter
import tkinter as tk
from tkinter import ttk
from typing import Callable, Union


class FloatSpinbox(customtkinter.CTkFrame):
    def __init__(self, *args,
                 width: int = 280,
                 height: int = 70,
                 step_size: Union[int, float] = 1,
                 max_value: Union[int, float] = None,
                 min_value: Union[int, float] = 0,
                 command: Callable = None,
                 value: Union[int, float] = 0,
                 **kwargs):
        super().__init__(*args, width=width, height=height, **kwargs)

        self.step_size = step_size
        self.command = command
        self.max_value = max_value
        self.min_value = min_value

        self.configure(fg_color=("#000029", "#000029"))  # set frame color

        self.grid_columnconfigure((0, 2), weight=0)  # buttons don't expand
        self.grid_columnconfigure(1, weight=1)  # entry expands
        buttonWidth = width/2

        self.subtract_button = customtkinter.CTkButton(self, font=("Roc Grotesk ExtraBold", 30), anchor="center", hover_color="#000029", text_color="#aec7fb", bg_color="#000029", fg_color="#000029", text="<", width=buttonWidth, height=height-6,
                                                       command=self.subtract_button_callback)

        self.subtract_button.grid(row=0, column=0, padx=(0, 10), pady=3)

        self.entry = customtkinter.CTkEntry(
            self, width=(width/3), height=height-6, border_width=0, font=("Roc Grotesk ExtraBold", 25), text_color="#aec7fb", fg_color="#000029")
        self.entry.grid(row=0, column=1, columnspan=1,
                        padx=(12, 10), pady=3, sticky="w")

        self.add_button = customtkinter.CTkButton(self, font=("Roc Grotesk ExtraBold", 30), anchor="center",  hover_color="#000029",  text_color="#aec7fb", bg_color="#000029", fg_color="#000029",  text=">", width=buttonWidth, height=height-6,
                                                  command=self.add_button_callback)
        self.add_button.grid(row=0, column=2, padx=(0, 10), pady=3)

        # default value
        if value is not None:
            self.entry.delete(0, "end")
            self.entry.insert(0, str(int(value))+"X")
        else:
            self.entry.insert(0, "1X")

    def add_button_callback(self):

        value = int(self.entry.get().split("X")[0]) + self.step_size
        if self.max_value is not None:
            if value > self.max_value:
                return
        if self.command is not None:
            self.command(value)
        try:
            self.entry.delete(0, "end")
            self.entry.insert(0, str(int(value))+"X")
        except ValueError:
            return

    def subtract_button_callback(self):
        value = int(self.entry.get().split("X")[0]) - self.step_size
        if self.min_value is not None:
            if value < self.min_value:
                return
        if self.command is not None:
            self.command(value)
        try:
            self.entry.delete(0, "end")
            self.entry.insert(0, str(int(value))+"X")
        except ValueError:
            return

    def get(self) -> Union[float, None]:
        try:
            return int(self.entry.get().split("X")[0])
        except ValueError:
            return None

    def set(self, value: float):
        self.entry.delete(0, "end")
        self.entry.insert(0, str(int(value))+"X")
