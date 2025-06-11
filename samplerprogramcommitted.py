import tkinter as tk
from tkinter import filedialog
import random
import os
import json
import pygame

# Initialize Pygame mixer
pygame.mixer.init()

# Constants
GRID_WIDTH = 6
GRID_HEIGHT = 6
BUTTON_SIZE = 200
SOUND_FOLDER = "./sounds"  # Folder containing wav files
COLOR_MAP_FILE = "color_map.json"

# Global variables
sound_buttons = []
selected_sequence = []
selected_sequence2 = []
sound_files = []
durations = {}
playback_active = False
current_sound_index = 0
current_sound_index2 = 0
preview_channel = pygame.mixer.Channel(1)
channel2 = pygame.mixer.Channel(2)
preview_after_id = None
color_map = {}
selected_sequence_indices = []
selected_sequence2_indices = []
max_track_duration = 1  # Global default

selected_block = None  # Currently selected block info for deletion

# Load all .wav files from the folder
sound_files = [f for f in os.listdir(SOUND_FOLDER) if f.endswith('.wav')]

# Load or create color map
if os.path.exists(COLOR_MAP_FILE):
    with open(COLOR_MAP_FILE, 'r') as f:
        color_map = json.load(f)
else:
    color_map = {}

# Ensure all current files are in the color map and preload durations
updated = False
for f in sound_files:
    if f not in color_map:
        color_map[f] = "#%06x" % random.randint(0x444444, 0xFFFFFF)
        updated = True
    path = os.path.join(SOUND_FOLDER, f)
    sound = pygame.mixer.Sound(path)
    durations[f] = sound.get_length()

if updated:
    with open(COLOR_MAP_FILE, 'w') as f:
        json.dump(color_map, f)

# Main application window
root = tk.Tk()
root.title("Soundboard Dashboard")

# Canvas for visual line of selected sounds (Track 1)
visual_frame = tk.Frame(root)
visual_frame.pack()

scrollbar = tk.Scrollbar(visual_frame, orient=tk.HORIZONTAL)
scrollbar.pack(fill=tk.X, side=tk.BOTTOM)

visual_canvas = tk.Canvas(visual_frame, height=80, bg="black", xscrollcommand=scrollbar.set)
visual_canvas.pack(fill=tk.X)

visual_canvas2 = tk.Canvas(visual_frame, height=80, bg="black", xscrollcommand=scrollbar.set)
visual_canvas2.pack(fill=tk.X)

# Sync scroll both canvases
def sync_scroll(*args):
    visual_canvas.xview(*args)
    visual_canvas2.xview(*args)

scrollbar.config(command=sync_scroll)

visual_canvas.config(xscrollcommand=scrollbar.set)
visual_canvas2.config(xscrollcommand=scrollbar.set)

# Main soundboard frame
board_frame = tk.Frame(root)
board_frame.pack()

# Bottom control frame
control_frame = tk.Frame(root)
control_frame.pack()

# Function to update visual line of selected colors and track durations
def update_visual_line():
    global max_track_duration
    visual_canvas.delete("all")
    visual_canvas2.delete("all")

    duration1 = sum(durations[sound_files[i]] for i in selected_sequence_indices) if selected_sequence_indices else 0
    duration2 = sum(durations[sound_files[i]] for i in selected_sequence2_indices) if selected_sequence2_indices else 0
    max_track_duration = max(duration1, duration2, 1)
    canvas_width = int(max_track_duration * 100)

    visual_canvas.config(scrollregion=(0, 0, canvas_width, 80), width=min(canvas_width, 800))
    visual_canvas2.config(scrollregion=(0, 0, canvas_width, 80), width=min(canvas_width, 800))

    # Draw time ruler ticks and labels on top
    for second in range(int(max_track_duration) + 1):
        x = second * 100
        for canvas in (visual_canvas, visual_canvas2):
            canvas.create_line(x, 0, x, 15, fill="white", tags="tick")
            canvas.create_text(x + 2, 2, text=f"{second}s", anchor="nw", fill="white", font=("Arial", 8), tags="tick")

    y0 = 30
    y1 = 80

    # Draw blocks for track 1
    x_pos = 0
    for idx, index in enumerate(selected_sequence_indices):
        file = sound_files[index]
        duration = durations[file]
        width = int(duration / max_track_duration * canvas_width)
        color = color_map[file]
        rect = visual_canvas.create_rectangle(x_pos, y0, x_pos + width, y1, fill=color, tags=("block", f"idx_{idx}"))
        visual_canvas.tag_bind(rect, '<Button-1>', lambda e, c=visual_canvas, s=selected_sequence_indices, i=idx: select_block(e, c, s, i))
        x_pos += width

    if x_pos < canvas_width:
        visual_canvas.create_rectangle(x_pos, y0, canvas_width, y1, fill="black")

    # Draw blocks for track 2
    x_pos = 0
    for idx, index in enumerate(selected_sequence2_indices):
        file = sound_files[index]
        duration = durations[file]
        width = int(duration / max_track_duration * canvas_width)
        color = color_map[file]
        rect = visual_canvas2.create_rectangle(x_pos, y0, x_pos + width, y1, fill=color, tags=("block2", f"idx_{idx}"))
        visual_canvas2.tag_bind(rect, '<Button-1>', lambda e, c=visual_canvas2, s=selected_sequence2_indices, i=idx: select_block(e, c, s, i))
        x_pos += width

    if x_pos < canvas_width:
        visual_canvas2.create_rectangle(x_pos, y0, canvas_width, y1, fill="black")

    clear_selection()

# Track which block is selected for deletion
def select_block(event, canvas, sequence_indices, idx):
    global selected_block
    clear_selection()
    selected_block = (canvas, sequence_indices, idx)
    # Highlight selected block with an outline rectangle
    # Find the rectangle id by tag idx_*
    tag = f"idx_{idx}"
    rects = canvas.find_withtag(tag)
    if rects:
        rect = rects[0]
        canvas.itemconfig(rect, outline="yellow", width=3)

def clear_selection():
    global selected_block
    for c in (visual_canvas, visual_canvas2):
        for rect in c.find_withtag("block") + c.find_withtag("block2"):
            c.itemconfig(rect, outline="", width=1)
    selected_block = None

# Function to handle delete keypress for deleting selected block
def on_delete(event):
    global selected_block
    if selected_block is None:
        return
    canvas, sequence_indices, idx = selected_block
    if idx < len(sequence_indices):
        del sequence_indices[idx]
        update_visual_line()

# Playback functions for both tracks
def play_next_track1():
    global current_sound_index
    if current_sound_index >= len(selected_sequence_indices):
        stop_playback()
        return
    index = selected_sequence_indices[current_sound_index]
    file = sound_files[index]
    path = os.path.join(SOUND_FOLDER, file)
    sound = pygame.mixer.Sound(path)
    preview_channel.play(sound)
    duration = durations[file]
    current_sound_index += 1
    root.after(int(duration * 1000), play_next_track1)

def play_next_track2():
    global current_sound_index2
    if current_sound_index2 >= len(selected_sequence2_indices):
        stop_playback()
        return
    index = selected_sequence2_indices[current_sound_index2]
    file = sound_files[index]
    path = os.path.join(SOUND_FOLDER, file)
    sound = pygame.mixer.Sound(path)
    channel2.play(sound)
    duration = durations[file]
    current_sound_index2 += 1
    root.after(int(duration * 1000), play_next_track2)

def start_playback():
    global playback_active, current_sound_index, current_sound_index2
    if not selected_sequence_indices and not selected_sequence2_indices:
        return
    playback_active = True
    current_sound_index = 0
    current_sound_index2 = 0
    play_next_track1()
    play_next_track2()
    animate_sweep(visual_canvas)
    animate_sweep(visual_canvas2)

def stop_playback():
    global playback_active
    playback_active = False
    preview_channel.stop()
    channel2.stop()
    visual_canvas.delete("sweep")
    visual_canvas2.delete("sweep")

# Animate synchronized sweep line on a canvas
def animate_sweep(canvas):
    steps = int(max_track_duration * 1000 / 30)
    if steps <= 0:
        return
    step_size = (max_track_duration * 100) / steps
    current_step = 0

    def sweep():
        nonlocal current_step
        if not playback_active:
            canvas.delete("sweep")
            return
        x = current_step * step_size
        canvas.delete("sweep")
        canvas.create_line(x, 0, x, 80, fill="white", width=3, tags="sweep")
        current_step += 1
        if current_step <= steps:
            root.after(30, sweep)

    sweep()

# Controls to add sounds to sequences for demo purposes
def add_to_sequence1(index):
    selected_sequence_indices.append(index)
    update_visual_line()

def add_to_sequence2(index):
    selected_sequence2_indices.append(index)
    update_visual_line()

# Soundboard buttons for adding sounds to sequences
def create_sound_buttons():
    for widget in board_frame.winfo_children():
        widget.destroy()
    for i, file in enumerate(sound_files):
        color = color_map[file]
        btn = tk.Button(board_frame, text=file, bg=color, fg="black", width=15, height=2,
                        command=lambda i=i: add_to_sequence1(i))
        btn.grid(row=i // GRID_WIDTH, column=i % GRID_WIDTH, padx=2, pady=2)

# Control buttons
play_button = tk.Button(control_frame, text="Play", command=start_playback)
play_button.pack(side=tk.LEFT, padx=5)

stop_button = tk.Button(control_frame, text="Stop", command=stop_playback)
stop_button.pack(side=tk.LEFT, padx=5)

# Bind delete key for removing selected block
root.bind("<Delete>", on_delete)

create_sound_buttons()
update_visual_line()

root.mainloop()
