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
preview_channel = pygame.mixer.Channel(1)
channel2 = pygame.mixer.Channel(2)
preview_after_id = None
color_map = {}
selected_sequence_indices = []
selected_sequence2_indices = []
_drag_data = {"item": None, "x": 0}
_drag_button = {"index": None, "track": None}

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
visual_canvas = tk.Canvas(visual_frame, height=50, bg="black")
visual_canvas.pack(fill=tk.X)

# Canvas for visual line of selected sounds (Track 2)
visual_canvas2 = tk.Canvas(visual_frame, height=50, bg="black")
visual_canvas2.pack(fill=tk.X)

# Main soundboard frame
board_frame = tk.Frame(root)
board_frame.pack()

# Bottom control frame
control_frame = tk.Frame(root)
control_frame.pack()

# Function to update visual line of selected colors
def update_visual_line():
    visual_canvas.delete("all")
    x_pos = 0
    for idx, index in enumerate(selected_sequence_indices):
        file = sound_files[index]
        duration = durations[file]
        width = int(duration * 100)
        color = color_map[file]
        rect = visual_canvas.create_rectangle(x_pos, 0, x_pos + width, 50, fill=color, tags=("block", f"block{idx}"))
        visual_canvas.tag_bind(rect, '<ButtonPress-1>', on_drag_start)
        visual_canvas.tag_bind(rect, '<B1-Motion>', on_drag_motion)
        visual_canvas.tag_bind(rect, '<ButtonRelease-1>', on_drag_release)
        x_pos += width
    visual_canvas.config(scrollregion=(0, 0, x_pos, 50))

    visual_canvas2.delete("all")
    x_pos = 0
    for idx, index in enumerate(selected_sequence2_indices):
        file = sound_files[index]
        duration = durations[file]
        width = int(duration * 100)
        color = color_map[file]
        rect = visual_canvas2.create_rectangle(x_pos, 0, x_pos + width, 50, fill=color, tags=("block2", f"block2_{idx}"))
        visual_canvas2.tag_bind(rect, '<ButtonPress-1>', on_drag_start2)
        visual_canvas2.tag_bind(rect, '<B1-Motion>', on_drag_motion2)
        visual_canvas2.tag_bind(rect, '<ButtonRelease-1>', on_drag_release2)
        x_pos += width
    visual_canvas2.config(scrollregion=(0, 0, x_pos, 50))

# Function to animate sweep line for each track
def animate_sweep(canvas, start_x, width, duration):
    steps = int(duration / 30 * 1000)
    if steps <= 0:
        return
    step_size = width / steps
    current_step = 0

    def sweep():
        nonlocal current_step
        if not playback_active:
            canvas.delete("sweep")
            return
        sweep_x = start_x + current_step * step_size
        canvas.delete("sweep")
        canvas.create_line(sweep_x, 0, sweep_x, 50, fill="white", width=3, tags="sweep")
        current_step += 1
        if current_step <= steps:
            root.after(30, sweep)

    sweep()

# Function to play the selected sound sequence
def play_sequence():
    global playback_active
    if not selected_sequence_indices and not selected_sequence2_indices:
        return
    playback_active = True
    play_track(visual_canvas, selected_sequence_indices, 0, 0, is_music=True)
    play_track(visual_canvas2, selected_sequence2_indices, 0, 1, is_music=False)

def play_track(canvas, sequence, index, channel_index, is_music):
    if index >= len(sequence) or not playback_active:
        canvas.delete("sweep")
        return

    file_index = sequence[index]
    file = sound_files[file_index]
    path = os.path.join(SOUND_FOLDER, file)
    sound = pygame.mixer.Sound(path)
    duration = durations[file]
    width = int(duration * 100)

    if is_music:
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
    else:
        channel2.play(sound)

    x_pos = sum(int(durations[sound_files[sequence[i]]] * 100) for i in range(index))
    animate_sweep(canvas, x_pos, width, duration)

    def check():
        busy = pygame.mixer.music.get_busy() if is_music else channel2.get_busy()
        if busy:
            root.after(100, check)
        else:
            play_track(canvas, sequence, index + 1, channel_index, is_music)

    check()

# Function to stop playback
def stop_sequence():
    global playback_active
    playback_active = False
    pygame.mixer.music.stop()
    preview_channel.stop()
    channel2.stop()
    visual_canvas.delete("sweep")
    visual_canvas2.delete("sweep")

# Function to clear the selection queue
def clear_sequence():
    global selected_sequence, selected_sequence2, selected_sequence_indices, selected_sequence2_indices
    selected_sequence = []
    selected_sequence2 = []
    selected_sequence_indices = []
    selected_sequence2_indices = []
    update_visual_line()

def on_sound_button_click(index, color):
    _drag_button["index"] = index
    _drag_button["track"] = None

def preview_sound_trigger(sound_path):
    try:
        sound = pygame.mixer.Sound(sound_path)
        preview_channel.play(sound)
    except Exception as e:
        print("Preview error:", e)

def preview_sound(event, sound_path):
    global preview_after_id
    preview_after_id = root.after(2000, lambda: preview_sound_trigger(sound_path))
    button = event.widget
    button.bind("<ButtonPress-1>", lambda e, p=sound_path, b=button: start_drag_from_button(e, p, b))

def stop_preview(event):
    global preview_after_id
    if preview_after_id:
        root.after_cancel(preview_after_id)
        preview_after_id = None
    preview_channel.stop()

def start_drag_from_button(event, sound_path, button):
    index = sound_buttons.index(button)
    _drag_button["index"] = index

visual_canvas.bind("<Button-1>", lambda e: drop_sound_on_track(e, 1))
visual_canvas2.bind("<Button-1>", lambda e: drop_sound_on_track(e, 2))

def drop_sound_on_track(event, track):
    index = _drag_button.get("index")
    if index is None:
        return
    file = sound_files[index]
    color = color_map[file]
    if track == 1:
        selected_sequence.append(color)
        selected_sequence_indices.append(index)
    else:
        selected_sequence2.append(color)
        selected_sequence2_indices.append(index)
    update_visual_line()
    _drag_button["index"] = None

# Drag handling for timeline
# (same as before)
def on_drag_start(event):
    canvas = event.widget
    _drag_data["item"] = canvas.find_closest(event.x, event.y)[0]
    _drag_data["x"] = event.x

def on_drag_motion(event):
    canvas = event.widget
    dx = event.x - _drag_data["x"]
    canvas.move(_drag_data["item"], dx, 0)
    _drag_data["x"] = event.x

def on_drag_release(event):
    _drag_data["item"] = None
    _drag_data["x"] = 0

def on_drag_start2(event):
    canvas = event.widget
    _drag_data["item"] = canvas.find_closest(event.x, event.y)[0]
    _drag_data["x"] = event.x

def on_drag_motion2(event):
    canvas = event.widget
    dx = event.x - _drag_data["x"]
    canvas.move(_drag_data["item"], dx, 0)
    _drag_data["x"] = event.x

def on_drag_release2(event):
    _drag_data["item"] = None
    _drag_data["x"] = 0
    
# Create sound buttons
for y in range(GRID_HEIGHT):
    for x in range(GRID_WIDTH):
        idx = y * GRID_WIDTH + x
        if idx >= len(sound_files):
            break
        file = sound_files[idx]
        color = color_map.get(file, "#%06x" % random.randint(0x444444, 0xFFFFFF))
        file_label = os.path.splitext(file)[0]
        sound_path = os.path.join(SOUND_FOLDER, file)
        button = tk.Button(
            board_frame,
            text=file_label,
            bg=color,
            width=BUTTON_SIZE // 10,
            height=BUTTON_SIZE // 20,
            wraplength=BUTTON_SIZE // 2,
            command=lambda idx=idx, color=color: on_sound_button_click(idx, color)
        )
        button.grid(row=y, column=x, padx=5, pady=5)
        button.bind("<Enter>", lambda e, p=sound_path: preview_sound(e, p))
        button.bind("<Leave>", stop_preview)
        sound_buttons.append(button)

# Controls
play_button = tk.Button(control_frame, text="Play", width=20, command=play_sequence)
play_button.pack(side=tk.LEFT, padx=10, pady=10)

stop_button = tk.Button(control_frame, text="Stop", width=20, command=stop_sequence)
stop_button.pack(side=tk.LEFT, padx=10, pady=10)

clear_button = tk.Button(control_frame, text="Clear", width=20, command=clear_sequence)
clear_button.pack(side=tk.LEFT, padx=10, pady=10)

# Start the GUI loop
root