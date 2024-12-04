import os
import sys
import json
import random
from tkinter import *
import tkinter.font as font
from tkinter import filedialog
from tkinter import PhotoImage, Button
from tkinter import Toplevel, Label, Entry
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog
import threading
import time
from mutagen.mp3 import MP3
import shutil
import win32gui
import win32con
import ctypes
import keyboard
import pyautogui
from pygetwindow import PyGetWindowException
import pygetwindow as gw
from mutagen import File

# Suppress pygame output in the console
with open(os.devnull, 'w') as f:
    old_stdout = sys.stdout
    sys.stdout = f
    from pygame import mixer
    sys.stdout = old_stdout

# Initialize mixer 
mixer.init()

# Global variables
global current_index, random_order, play_offset
paused_position = 0  # Holds the paused position in milliseconds
current_index = 0  # Initialize current_index to 0
random_index = 0
progress_drag_percentage = 0
play_offset = 0
progress_percentage = 0
current_song_path = ''
is_playing = False  # Indicates if music is currently playing
random_mode = False  # Toggle for random play mode
first_load = True  # To manage first-time initialization
is_paused = False  # Check if the song is paused
first_song_click = True
is_dragging = False
on_progress_released = True
is_first_song_playing = False
shortcuts_window = None

# Paths for music and settings
base_dir = os.getcwd()
music_path = ''
playlist_file = "playlist.json"
settings_file = "volume_settings.json"
mode_settings_file = "mode_settings.json"
music_settings_file = "music_player_settings.json"

def swap_buttons():
    global is_paused, play_button, resume_button, pause_button, is_playing
    if mixer.music.get_busy() or not is_paused:
        play_button.grid_remove()
        resume_button.grid_remove()
        pause_button.grid()
        is_playing = True
        is_paused = False

def load_music_folder():
    if os.path.exists(music_settings_file):
        with open(music_settings_file, "r") as f:
            settings = json.load(f)
        return settings.get("music_path")
    else:
        return None

music_path = load_music_folder()

def save_music_folder(path):
    settings = {"music_path": path}
    with open(music_settings_file, "w") as f:
        json.dump(settings, f)

def update_window_title():
    """Update the window title to include the current music folder."""
    folder_name = os.path.basename(music_path)  # Get just the folder name
    root.title(f"Music Player - {folder_name}")

def load_play_mode():
    """Load the saved random/normal play mode from the settings file."""
    if os.path.exists(mode_settings_file):
        with open(mode_settings_file, 'r') as f:
            mode_settings = json.load(f)
            return mode_settings.get('random_mode', False)
    return False

def save_play_mode():
    """Save the current play mode (random/normal) to the settings file."""
    with open(mode_settings_file, 'w') as f:
        json.dump({'random_mode': random_mode}, f)

def load_volume():
    """Load the saved volume level from the settings file."""
    if os.path.exists(settings_file):
        with open(settings_file, 'r') as f:
            settings = json.load(f)
            return settings.get('volume', 50)  # Default to 50 if not found
    return 50

def save_volume(volume):
    """Save the volume level to the settings file and adjust the mixer volume."""
    normalized_volume = int(volume) / 100
    mixer.music.set_volume(normalized_volume)
    with open(settings_file, 'w') as f:
        json.dump({'volume': volume}, f)

def print_current_song(event=None):
    """Print the currently playing song in the console."""
    current_song = songs_list.get(ACTIVE).replace('.mp3', '')
    print(f"Currently playing: {current_song or 'No song is currently playing.'}; Current index: {current_index}")

def update_current_index():
    """Update the current index based on the currently selected song."""
    selected_index = songs_list.curselection()
    if selected_index:
        global current_index
        current_index = selected_index[0]

def Play():
    global previous_button_state, next_button_state, is_playing, is_paused, first_song_click
    if is_playing:  # If already playing, return without doing anything
        return

    if random_mode:
        selected_index = songs_list.curselection()
        if selected_index:
            current_index = selected_index[0]
            play_random_song()
        else:
            play_random_song()
    else:
        play_ordered()

    # Show the pause button and hide the play button after starting the song
    pause_button.grid()  # Show pause button
    play_button.grid_remove()  # Hide play button
    start_progress_update()  # Set the playing state to True

    # Create and start the thread to check if the song has ended

    is_paused = False
    first_song_click = False  # Change state to indicate a song has been played
    root.bind('<v>', lambda event: toggle_pause_resume())

def Pause():
    global paused_position, is_paused, is_playing  # Reference the global paused position

    # Save the current volume
    original_volume = mixer.music.get_volume()

    # Gradually decrease the volume
    current_volume = original_volume
    while current_volume > 0:
        current_volume -= 0.08  # Decrease the volume incrementally
        mixer.music.set_volume(max(current_volume, 0))  # Ensure it doesn't go below 0
        time.sleep(0.05)  # Short delay for a smooth fade effect

    # Pause the music after fading out
    paused_position = mixer.music.get_pos()  # Get the current position in milliseconds
    mixer.music.pause()
    
    # Restore the original volume
    mixer.music.set_volume(original_volume)

    # Update UI elements
    resume_button.grid()
    pause_button.grid_remove()
    is_paused = True
    is_playing = False

def Resume():
    global is_paused, is_playing
    mixer.music.unpause()  # Just unpause the music; it resumes from the paused position
    pause_button.grid()
    resume_button.grid_remove()
    start_progress_update()
    is_paused = False
    is_playing = True

def toggle_pause_resume():
    global is_playing, is_paused  # Reference the global variables

    if is_playing or not is_paused:  # If currently playing, pause the music
        Pause()
    else:  # If currently paused, resume the music
        Resume()

def Next():
    """Play the next song in the random or normal order."""
    global random_index, is_playing, random_order, first_song_click, current_index

    start_progress_update()  # Update the play state
    if not is_playing:
        pause_button.grid()
        resume_button.grid_remove()
        is_playing = True

    if random_mode:
        # Play next song in the random order
        if random_order:  # Ensure random_order is generated
            random_index = (random_index + 1) % len(random_order)
            play_random_song()
    else:
        if first_song_click:
            next_one = current_index + 1
            first_song_click = False
        else:
            try:
                next_one = songs_list.curselection()[0] + 1
            except Exception as e:
                next_one = 1
        if next_one >= songs_list.size():  # If at the end, go to the first song
            next_one = 0
        play_song_at_index(next_one)
        current_index = next_one
        update_current_index()
        generate_random_order()
    root.bind('<v>', lambda event: toggle_pause_resume())


def Previous():
    """Play the previous song in the random or normal order."""
    global random_index, is_playing, random_order, first_song_click, current_index

    start_progress_update()  # Update the play state
    if not is_playing:
        pause_button.grid()
        resume_button.grid_remove()
        is_playing = True

    if random_mode:
        # Play previous song in the random order
        if random_order:  # Ensure random_order is generated
            random_index = (random_index - 1) % len(random_order)
            play_random_song()
    else:
        if first_song_click:
            previous_one = current_index -1
            first_song_click = False
        else:
            try:
                previous_one = songs_list.curselection()[0] - 1
            except Exception as e:
                previous_one = len(list(songs_list.get(0, END))) -1
        if previous_one < 0:  # If at the beginning, go to the last song
            previous_one = songs_list.size() - 1
        current_index = previous_one
        play_song_at_index(previous_one)
        update_current_index()
        generate_random_order()
    root.bind('<v>', lambda event: toggle_pause_resume())

def play_song_at_index(index, start_pos=0):
    """Play a song at a specific index, with an optional start position."""
    global current_index, progress_var, is_playing, current_song_path, is_paused, is_first_song_playing
    song_name_without_ext = songs_list.get(index)
    song_path = os.path.join(music_path, song_name_without_ext + '.mp3')  # Add .mp3 when loading

    if os.path.exists(song_path):
        mixer.music.load(song_path)
        # mixer.music.play(start=round(start_pos))

        play_at_offset(start_pos)

        songs_list.selection_clear(0, END)
        songs_list.activate(index)
        songs_list.selection_set(index)

        current_song_path = song_path  # Use the full path with .mp3
        
        if not random_order:
            current_index = index  # Update current_index when a song is played
        
        # Reset and start progress bar
        progress_var.set(0)
    songs_list.see(index)
    is_playing = True
    is_paused = False
    is_first_song_playing = True

def play_from_begining():
    original_volume = mixer.music.get_volume()
    current_volume = original_volume
    mixer.music.set_volume(max(current_volume, 0))
    selected_index = songs_list.curselection()
    current_index = selected_index[0]
    play_song_at_index(current_index)
    Pause()
    mixer.music.set_volume(original_volume)

def play_random():
    global random_index
    selected_index = songs_list.curselection()
    
    if selected_index:
        random_index = selected_index[0]
        play_song_at_index(random_index)  # Play the selected song directly
        play_random_song()

def play_random_song():
    """Play a song from the current random order based on the current index."""
    global random_index
    if random_order:
        song = random_order[random_index]  # Get the song at the current index
        play_song_at_index(songs_list.get(0, END).index(song))  # Play it

def get_current_song_state():
    """Get the current song and its playback position."""
    current_song = songs_list.get(ACTIVE)
    current_position = mixer.music.get_pos() / 1000  # Save position in seconds
    return current_song, current_position

def play_from_state(song, position):
    index = songs_list.get(0, END).index(song)
    play_song_at_index(index, start_pos=position)

def play_ordered():
    """Play the selected song in order."""
    selected_index = songs_list.curselection()
    current_index = selected_index[0] if selected_index else 0
    play_song_at_index(current_index)

def generate_random_order(selected_index=''):
    """Generate a random order for the playlist and store it in random_order."""
    global random_order, random_index
    song_list = list(songs_list.get(0, END))  # Get all the songs in the list
    if not selected_index:  # If no song is selected, default to the first song
        selected_index = (0,)
    else:
        selected_index = songs_list.curselection()
    
    selected_song = song_list[selected_index[0]]  # Get the song from the selected index

    random_order = random.sample(song_list, len(song_list))
    
    # Ensure the selected song is moved to the first position
    random_order.remove(selected_song)  # Take it out from the random order
    random_order = [selected_song] + random_order
    random_index = 0  # Reset the index to the first song in the random order

random_mode = False
first_load = True

def toggle_random():
    """Toggle between random and normal play mode without restarting the song."""
    global random_mode

    selected_index = songs_list.curselection()
    if selected_index:
        global current_index
        current_index = selected_index[0]
    
    current_song, current_pos = get_current_song_state()  # Save current state if applicable
    if first_load != True:
        random_mode = not random_mode
    if random_mode:
        if first_load != True:
            random_button.config(image=normal_play_image)  # Update button text to indicate normal play mode
    else:
        random_button.config(image=random_play_image)  # Update button text to indicate random play mode
    save_play_mode()

    generate_random_order(selected_index=selected_index)

def save_and_close():
    save_volume(volume_slider.get())
    save_play_mode()
    mixer.quit()
    root.destroy()
    raise SystemExit()

def save_volume(volume):
    volume = int(volume) / 100  # Normalize volume to a 0.0 - 1.0 range
    mixer.music.set_volume(volume)  # Set the volume in the mixer
    with open(settings_file, 'w') as f:
        json.dump({'volume': volume * 100}, f)  # Save volume in the original range

def play_next_song():
    global is_first_song_playing
    while True:
        if is_first_song_playing:
            while True:
                if not mixer.music.get_busy() and not is_paused:
                    time.sleep(2)
                    Next()
                    start_progress_update()
                else:
                    time.sleep(1)
        time.sleep(1)

def on_song_click(event):
    global first_song_click, is_playing, is_paused

    """Callback for when a song is clicked in the listbox."""
    selected_index = songs_list.curselection()  # Get index of the selected song
    if selected_index:
        song = songs_list.get(selected_index[0])  # Get the selected song name
        play_ordered()
        songs_list.selection_clear(0, END)  # Clear previous selections
        songs_list.selection_set(selected_index)  # Highlight the newly selected song
        start_progress_update()  # Set the playing state to True
        is_paused = False

        if first_song_click:
            first_song_click = False  # Change state to indicate a song has been played
        
        pause_button.grid()  # Show pause button
        play_button.grid_remove()
        resume_button.grid_remove()  # Hide play button
    generate_random_order(selected_index=selected_index)
    root.bind('<v>', lambda event: toggle_pause_resume())

def load_and_resize_image(file_path, size=(30, 30)):
    try:
        original_image = Image.open(file_path)  # Open the image file
        scaled_image = original_image.resize(size, Image.LANCZOS)  # Resize the image
        return ImageTk.PhotoImage(scaled_image)  # Convert to PhotoImage
    except Exception as e:
        print(f"Error loading image from {file_path}: {e}")
        return None  # Return None if an error occurs

def create_button(frame, image, command, row, column, state=NORMAL, border=0, padx=10):
    button = Button(frame, image=image, background=background_colors["main"],
                    command=command, state=state, bd=border)
    button.grid(row=row, column=column, padx=padx)
    return button

def update_progress_bar():
    global on_progress_released, progress_drag_percentage, progress_var, play_offset, progress_percentage
    """Update the progress bar based on the current song's progress."""
    update_current_index()  # Ensure the current song index is updated
    idx = current_index
    audio = MP3(os.path.join(music_path, songs_list.get(current_index) + '.mp3'))
    song_length = audio.info.length

    while idx == current_index:
        if not is_paused and not is_dragging:  # Only update if not paused and not dragging
            try:
                current_position = mixer.music.get_pos() / 1000 + play_offset  # Current position in seconds
                progress_percentage = (current_position / song_length) * 100  # Calculate percentage
                if mixer.music.get_pos() <= 0:
                    progress_percentage = 0
                progress_var.set(progress_percentage)  # Update progress bar
            except Exception as e:
                print("Error updating progress bar:", e)
                break
        time.sleep(1)

def on_progress_release(event):
    global is_dragging, progress_drag_percentage, on_progress_released, progress_var, is_playing, is_paused
    """Play the song from the position where the user releases the mouse."""
    progress_width = progress_bar.winfo_width()  # Get the width of the progress bar
    mouse_x = event.x  # Get the x-coordinate of the mouse when the left click is released

    progress_drag_percentage = (mouse_x / progress_width) * 100
    progress_var.set(progress_drag_percentage)
    seek_song(progress_drag_percentage)
    is_dragging = False
    on_progress_released = True

    play_button.grid_remove()
    resume_button.grid_remove()
    pause_button.grid()
    is_playing = True
    is_paused = False

def on_progress_drag(event):
    global is_dragging, progress_drag_percentage, progress_var
    """Update the progress bar as the user drags."""
    is_dragging = True  # Set the flag to disable automatic updates
    progress_width = progress_bar.winfo_width()  # Get the width of the progress bar
    mouse_x = event.x  # Get the x-coordinate of the mouse during dragging

    progress_drag_percentage = (mouse_x / progress_width) * 100
    progress_var.set(progress_drag_percentage)

def seek_song(new_value):
    song_length = MP3(os.path.join(music_path, songs_list.get(current_index) + '.mp3')).info.length
    new_position = (new_value / 100) * song_length  # Calculate the new position in seconds
    play_at_offset(new_position)

def seek_forward(seconds=15):
    global is_paused, is_playing
    song_length = MP3(os.path.join(music_path, songs_list.get(current_index) + '.mp3')).info.length
    new_offset = (mixer.music.get_pos() / 1000 + play_offset) + seconds
    if new_offset > song_length:
        new_offset = song_length  # Cap at song length
    play_at_offset(new_offset)  # Play from the new offset
    swap_buttons()

def seek_backward(seconds=15):
    global is_paused, is_playing
    new_offset = (mixer.music.get_pos() / 1000 + play_offset) - seconds
    if new_offset < 0:
        new_offset = 0  # Cap at the beginning
    play_at_offset(new_offset)  # Play from the new offset
    swap_buttons()

# Start the progress update in a separate thread
def start_progress_update():
    is_playing = True
    progress_thread = threading.Thread(target=update_progress_bar)
    progress_thread.daemon = True  # Daemon threads exit when the main program exits
    progress_thread.start()

def play_at_offset(offset):
    global play_offset

    if offset < 0:
        play_offset = 0
    elif offset > MP3(os.path.join(music_path, songs_list.get(current_index) + '.mp3')).info.length:
        mixer.music.stop()
        return
    else:
        play_offset = offset
    mixer.music.play(start=offset)

def update_songs_list():
    global current_index
    """Update the song list from the current music folder."""
    songs_list.delete(0, END)  # Clear the current list
    for song_file in os.listdir(music_path):
        if song_file.endswith(".mp3"):  # Add only mp3 files
            song_name_without_ext = os.path.splitext(song_file)[0]  # Remove the extension
            songs_list.insert(END, song_name_without_ext)  # Insert file name without the full path
    update_window_title()  # Update the window title
    current_index = 0
    update_current_index()

def change_music_folder():
    """Open a folder selection dialog to change the music folder."""
    global music_path, selected_index
    selected_folder = filedialog.askdirectory(initialdir=music_path, title="Select Music Folder")
    
    if selected_folder:  # If a folder is selected
        music_path = selected_folder  # Update the music path
        save_music_folder(music_path)  # Save the new path
        update_songs_list()  # Refresh the song list with new folder contents
        if mixer.music.get_busy() or is_playing:
            mixer.music.stop()
            swap_buttons()
        elif not mixer.music.get_busy() or is_paused:
            swap_buttons()

        selected_index = 0
        play_song_at_index(selected_index)
        start_progress_update()
        update_current_index()
        generate_random_order()

def get_folder():
    print(f'Current Folder Path: {load_music_folder()}')

def delete_all(event=None):
    search_entry.delete(0, tk.END)
    print('deleted all')

def search_songs(search_input=''):
    """Prompt for song search and find matching songs."""
    global current_index
    if search_input:
        search_input = search_input.lower()  # Convert input to lowercase for case-insensitive search
        matches = []
        
        # Search through all songs in the list
        for i, song in enumerate(songs_list.get(0, tk.END)):
            if search_input.replace('.','').replace(' ','') in song.lower().replace('.','').replace(' ',''):  # Case-insensitive matching
                matches.append(song)
                if len(matches) == 1:
                    # Scroll the first match into view
                    songs_list.see(i)
                    # Highlight the first match in tfhe listbox
                    songs_list.selection_clear(0, tk.END)
                    songs_list.selection_set(i)
                    play_song_at_index(i)

                    current_index = i

                    # Replace buttons only if a song is playing
                    swap_buttons()
                    is_playing = True
                    is_paused = False

        # Print all matches to the console
        if matches:
            print("Matches found:")
            for match in matches:
                print(match)
        else:
            print(f"No matches found for '{search_input}'.")
        update_current_index()
        generate_random_order(selected_index=current_index)
        start_progress_update()
    root.bind('<v>', lambda event: toggle_pause_resume())

def custom_search_dialog(event=None):
    """Custom search window for inputting song name."""
    search_window = Toplevel(root)
    search_window.geometry("350x180")  # Set custom window size (larger)
    search_window.resizable(False, False)  # Make the window not resizable
    search_window.title("Seek Song")

    # Input field
    search_label = Label(search_window, text="Enter song name:", font=("Arial", 14))
    search_label.pack(pady=20)
    
    search_entry = Entry(search_window, font=("Arial", 12))
    search_entry.pack(pady=10, padx=20)

    # Set focus to the input field
    search_entry.focus_set()

    # Bind common Windows shortcuts to the text entry box
    search_entry.bind('<Control-v>', lambda event: search_entry.insert(tk.END, root.clipboard_get()))
    search_entry.bind('<Control-a>', lambda event: search_entry.select_range(0, tk.END) or search_entry.icursor(tk.END))
    search_entry.bind('<Control-c>', lambda event: root.clipboard_clear() or root.clipboard_append(search_entry.selection_get()))
    search_entry.bind('<Control-x>', lambda event: root.clipboard_clear() or root.clipboard_append(search_entry.selection_get()) or search_entry.delete('sel.first', 'sel.last'))
    search_entry.bind('<Control-BackSpace>', lambda event: search_entry.delete(0, tk.END))

    # Bind the return key to the search function
    search_entry.bind('<Return>', lambda event: search_songs(search_entry.get()))

    def search_action():
        search_input = search_entry.get()
        if search_input:
            search_songs(search_input)
        
        # Close the window after search
        search_window.destroy()  

    # Function to close the search window
    def close_search_window(event=None):
        search_window.destroy()

    search_button = Button(search_window, text="Search", command=search_action, font=("Arial", 12))
    search_button.pack(pady=10)
    
    search_entry.bind("<Return>", lambda event: search_action())  # Enter key triggers search
    search_window.bind("<Escape>", close_search_window)  # Bind 'Esc' key to close the window

    start_progress_update()

def first_time_launch():
    music_path = load_music_folder()
    if music_path is None:
        root.withdraw()  # Hide the main window initially
        while True:
            selected_folder = filedialog.askdirectory(initialdir=os.path.expanduser("~"), title="Select Music Folder")
            if selected_folder:
                if any([file.endswith(".mp3") for file in os.listdir(selected_folder)]):
                    music_path = selected_folder
                    save_music_folder(music_path)
                    root.destroy()
                    os.execl(sys.executable, sys.executable, *sys.argv)
                    break
                else:
                    no_mp3_folder_window = Toplevel()
                    no_mp3_folder_window.title("No MP3 Folder Selected")
                    no_mp3_folder_window.resizable(False, False)
                    no_mp3_folder_window.transient(root)  # Make other windows non-clickable
                    Label(no_mp3_folder_window, text="Please select a folder with .mp3 files").pack(pady=20)
                    Button(no_mp3_folder_window, text="Select Folder", command=no_mp3_folder_window.destroy).pack(pady=5)
                    Button(no_mp3_folder_window, text="Exit App", command=lambda: sys.exit()).pack(pady=(5, 20))
                    no_mp3_folder_window.protocol("WM_DELETE_WINDOW", lambda: sys.exit())
                    no_mp3_folder_window.wait_window(no_mp3_folder_window)
            else:
                no_folder_window = Toplevel()
                no_folder_window.title("No Folder Selected")
                no_folder_window.resizable(False, False)
                no_folder_window.transient(root)  # Make other windows non-clickable
                Label(no_folder_window, text="Please select a folder").pack(pady=20)
                Button(no_folder_window, text="Select Folder", command=no_folder_window.destroy).pack(pady=5)
                Button(no_folder_window, text="Exit App", command=lambda: sys.exit()).pack(pady=(5, 20))
                no_folder_window.protocol("WM_DELETE_WINDOW", lambda: sys.exit())
                no_folder_window.wait_window(no_folder_window)
        root.deiconify()
        update_songs_list()
        current_index = 0
        update_current_index()
        generate_random_order(selected_index=current_index)

def scroll_up(event=None):
    """Scroll the listbox view up by a few items."""
    songs_list.yview_scroll(-1, "units")  # Scrolls up by one line

def scroll_down(event=None):
    """Scroll the listbox view down by a few items."""
    songs_list.yview_scroll(1, "units")  # Scrolls down by one line

def show_shortcuts():
    """Toggle the shortcuts window open and closed."""
    global shortcuts_window
    
    # If the window is already open, close it
    if shortcuts_window and tk.Toplevel.winfo_exists(shortcuts_window):
        shortcuts_window.destroy()
        shortcuts_window = None
    else:
        # Otherwise, create the window
        shortcuts_window = tk.Toplevel(root)
        shortcuts_window.title("Keybind Shortcuts")
        shortcuts_window.geometry("300x525")

        # Shortcut labels
        shortcuts = [
            ("A", "Previous Song"),
            ("D", "Next Song"),
            ("R", "Toggle Random"),
            ("C", "Change Music Folder"),
            ("V", "Play / Pause"),
            ("T", "Play Song From Begining"),
            ("Ctrl + Left", "Previous Song"),
            ("Ctrl + Right", "Next Song"),
            ("Up / Ctrl + X", "Increase Volume"),
            ("Down / Ctrl + Z", "Decrease Volume"),
            ("Right", "Seek Forward (+15 sec)"),
            ("Left", "Seek Backward (-15 sec)"),
            ("Shift + Right", "Seek Forward (+5 sec)"),
            ("Shift + Left", "Seek Backward (-5 sec)"),
            ("Ctrl + W / Ctrl + S", "Scroll Up / Down in List"),
            ("Ctrl + Up / Ctrl + Down", "Scroll Up / Down in List"),
            ("F", "Custom Search Dialog"),
            ("Ctrl + Shift + A", "Brings the app into focus"),
            ("Ctrl + Shift + Q", "Minimizes the app"),
            ("Q", "Show Keybind Shortcuts"),
        ]

        # Add shortcut descriptions to the window
        for key, action in shortcuts:
            label = tk.Label(shortcuts_window, text=f"{key}: {action}", font=("Arial", 10))
            label.pack(anchor="w", padx=10, pady=2)

        # Focus on this new window and prevent interaction with the main window
        shortcuts_window.grab_set()

class VolumeSlider:
    def __init__(self, master, row):
        """Initialize the volume slider."""
        self.master = master
        self.frame = tk.Frame(master)
        self.frame.grid(row=row, column=2, sticky="ew")

        # Colors for the slider
        slider_color = '#64969b'  # Example RGB color
        fill_color = '#051c1e'
        thumb_color = '#003232'

        self.canvas = tk.Canvas(self.frame, width=150, height=30)
        self.canvas.pack()

        # Draw the track and fill rectangle
        self.track = self.canvas.create_rectangle(10, 10, 140, 20, fill=slider_color, outline='')
        self.fill_rect = self.canvas.create_rectangle(10, 10, 10, 20, fill=fill_color, outline='')

        # Define thumb dimensions and position
        self.thumb_size = 20
        self.thumb = self.canvas.create_oval(0, 0, self.thumb_size, self.thumb_size, fill=thumb_color, outline='')

        # Bind mouse events for volume control
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)

        self.current_volume = load_volume()
        self.update_thumb_position()
        self.center_canvas()

        # Initialize mixer for volume control
        mixer.init()
        mixer.music.set_volume(self.current_volume / 100)  # Set initial volume in pygame mixer

    def center_canvas(self):
        """Center the canvas in the frame."""
        self.master.update_idletasks()
        width = self.master.winfo_width()
        padx = max(0, (width - 150) // 2)
        self.canvas.pack(padx=padx)

    def update_thumb_position(self):
        """Update the thumb position and fill rectangle based on the current volume."""
        x_position = 10 + (self.current_volume / 100) * 130
        thumb_y_position = (30 - self.thumb_size) // 2

        if x_position < 13:
            x_position = 13
        elif x_position > 137:
            x_position = 137
        
        # Update the fill rectangle based on current volume
        fill_width = 10 + (self.current_volume / 100) * 130
        self.canvas.coords(self.fill_rect, 10, 10, fill_width, 20)

        # Update thumb position
        self.canvas.coords(self.thumb, x_position - self.thumb_size // 2, thumb_y_position,
                           x_position + self.thumb_size // 2, thumb_y_position + self.thumb_size)

    def on_click(self, event):
        """Handle click on the slider to set volume."""
        self.set_volume(event.x)

    def on_drag(self, event):
        """Handle dragging the thumb."""
        self.set_volume(event.x)

    def set_volume(self, x):
        """Set volume based on the x position of the slider."""
        x = max(10, min(x, 140))  # Ensure x is within bounds
        self.current_volume = int((x - 10) / 130 * 100)  # Convert to volume level (0-100)
        self.update_thumb_position()
        save_volume(self.current_volume)

    def get(self):
        """Get the current volume level."""
        return self.current_volume
    
    def increase_volume(self):
        """Increase volume by 10%."""
        self.current_volume = min(100, self.current_volume + 10)  # Cap at 100%
        self.update_thumb_position()
        mixer.music.set_volume(self.current_volume / 100)
        save_volume(self.current_volume)

    def decrease_volume(self):
        """Decrease volume by 10%."""
        self.current_volume = max(0, self.current_volume - 10)  # Minimum 0%
        self.update_thumb_position()
        mixer.music.set_volume(self.current_volume / 100)
        save_volume(self.current_volume)

def get_random_state():
    if load_play_mode():
        print(f'Random State: Active')
    else:
        print(f'Random State: Disabled')

def get_volume():
    print(f'Current Volume: {volume_slider.get()}')

def bring_app_to_background():
    root.attributes('-topmost', False)
    root.iconify()

def bring_app_to_foreground():
    for i in range(2):
        root.iconify()
        root.deiconify()
    root.attributes('-topmost', True)
    root.attributes('-topmost', False)
    root.after(100, lambda: root.focus_set())

def format_time(seconds):
    """Format seconds into mm:ss or hh:mm:ss with appropriate labels."""
    if seconds < 60:  # Less than 1 minute
        return f"{int(seconds):02} sec"  # Ensure leading zero for seconds
    elif seconds < 3600:  # Less than 1 hour
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02}:{seconds:02} min"  # mm:ss format with "min"
    else:  # 1 hour or more
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        if hours == 1:  # Singular "hour"
            return f"{hours:02}:{minutes:02}:{seconds:02} hour"
        else:  # Plural "hours"
            return f"{hours:02}:{minutes:02}:{seconds:02} hours"

def get_artist(song_path):
    try:
        audio = File(song_path)  # Load the audio file
        if "TPE1" in audio:  # ID3 tag for artist in MP3 files
            return audio["TPE1"].text[0]
        elif "artist" in audio:  # FLAC or other formats
            return audio["artist"][0]
        else:
            return "Unknown Artist"
    except Exception as e:
        print(f"Error reading metadata: {e}")
        return "Unknown Artist"

def get_progress_percentage():
    song_length = MP3(os.path.join(music_path, songs_list.get(current_index) + '.mp3')).info.length
    current_position = mixer.music.get_pos() / 1000 + play_offset  # Convert to seconds
    progress_percentage = (current_position / song_length) * 100  # Assuming you have total_duration in seconds

    # Print the formatted output
    formatted_time = format_time(current_position)
    print(f'Current song progress: {round(progress_percentage, 2):.2f} % or {formatted_time}')

def print_current_artist():
    if current_song_path:
        artist = get_artist(current_song_path)
        print(f"Current Artist: {artist}")
    else:
        print("No song is currently loaded.")

def print_all_artists():
    song_list = list(songs_list.get(0, END))
    for song_path in song_list:
        artist = get_artist(song_path)
        print(f"Artist: {artist}")

load_volume()
load_play_mode()

play_next_song_thread = threading.Thread(target=play_next_song)
play_next_song_thread.start()

# Creating the root window 
root = Tk()
root.withdraw()  # Hide the main window
first_time_launch()
root.deiconify()  # Show the main window again
root.title('Music Player')
root.geometry('528x390')
root.resizable(False, False)  # Make the window not resizable

# Load the icon image
bundledir = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(bundledir, "resources", "buttons", "logo.png")
logo_image = Image.open(logo_path)
icon_image = ImageTk.PhotoImage(logo_image)

# Set the icon for the window
root.iconphoto(True, icon_image)

# Define the column weights to allow grid flexibility
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_columnconfigure(2, weight=1)

# Bind the save function to window close event
root.protocol("WM_DELETE_WINDOW", save_and_close)

# Define background colors
background_colors = {
    "list": "#005050",  # RGB(0, 80, 80)
    "foreground": "#161237",  # RGB(22, 18, 53)
    "select_bg": "#6496aa",  # RGB(100, 140, 170)
    "main": "#008080",  # RGB(0, 128, 128)
    "text": "#000011",  # RGB(0, 0, 17) 
}

# Define your font without underline
default_font = font.Font(family="Arial", size=15, underline=0)

# Create the listbox to contain songs
songs_list = Listbox(root, selectmode=SINGLE, bg=background_colors["list"], 
                     fg=background_colors["foreground"], font=default_font, 
                     height=12, width=47, bd=0, exportselection=False,
                     selectbackground=background_colors["select_bg"], 
                     selectforeground=background_colors["text"],
                     activestyle=tk.NONE, highlightthickness=0)
songs_list.grid(columnspan=9)
songs_list.grid(row=0, column=0, columnspan=9)
songs_list.bind('<<ListboxSelect>>', on_song_click)

root.tk_setPalette(background=background_colors["main"])

update_songs_list()

if first_load:
    generate_random_order()

# Font is defined which is to be used for the button font 
defined_font = font.Font(family='Helvetica')

# Load images
bundledir = os.path.dirname(os.path.abspath(__file__))
next_file = os.path.join(bundledir, "resources", "buttons", "next.png")
prev_file = os.path.join(bundledir, "resources", "buttons", "previous.png")
play_file = os.path.join(bundledir, "resources", "buttons", "play.png")
pause_file = os.path.join(bundledir, "resources", "buttons", "pause.png")
random_play_file = os.path.join(bundledir, "resources", "buttons", "shuffle-inactive.png")
normal_play_file = os.path.join(bundledir, "resources", "buttons", "shuffle-active.png")
songs_file = os.path.join(bundledir, "resources", "buttons", "playlist.png")
print_song_file = os.path.join(bundledir, "resources", "buttons", "search.png")

# Load and resize images using the function
next_image = load_and_resize_image(next_file)
prev_image = load_and_resize_image(prev_file)
play_image = load_and_resize_image(play_file)
pause_image = load_and_resize_image(pause_file)
random_play_image = load_and_resize_image(random_play_file)
normal_play_image = load_and_resize_image(normal_play_file)
songs_image = load_and_resize_image(songs_file)
print_song_image = load_and_resize_image(print_song_file)

# Create a new frame for the buttons and volume bar
button_frame = Frame(root)
button_frame.grid(row=1, column=0, columnspan=10, padx=10, pady=10)

next_button = create_button(button_frame, next_image, Next, row=1, column=4)
previous_button = create_button(button_frame, prev_image, Previous, row=1, column=2)
random_button = create_button(button_frame, random_play_image, toggle_random, row=1, column=6)
songs_button = create_button(button_frame, songs_image, change_music_folder, row=1, column=0)
print_song_button = create_button(button_frame, print_song_image, custom_search_dialog, row=1, column=1, padx=(0, 60))

# Next button
next_button = Button(
    button_frame,
    image=next_image,
    background=background_colors["main"],
    activebackground=background_colors["main"],  # No highlight on press
    activeforeground=background_colors["main"],  # No text color change on press
    command=Next
)
next_button['bd'] = 0
next_button.grid(row=1, column=4)

# Previous button
previous_button = Button(
    button_frame,
    image=prev_image,
    background=background_colors["main"],
    activebackground=background_colors["main"],  # No highlight on press
    activeforeground=background_colors["main"],  # No text color change on press
    command=Previous
)
previous_button['bd'] = 0
previous_button.grid(row=1, column=2)

# Random/Shuffle button
random_button = Button(
    button_frame,
    image=random_play_image,
    background=background_colors["main"],
    activebackground=background_colors["main"],  # No highlight on press
    activeforeground=background_colors["main"],  # No text color change on press
    command=toggle_random
)
random_button['bd'] = 0
random_button.grid(row=1, column=6)

# Songs folder button
songs_button = Button(
    button_frame,
    image=songs_image,
    background=background_colors["main"],
    activebackground=background_colors["main"],  # No highlight on press
    activeforeground=background_colors["main"],  # No text color change on press
    command=change_music_folder
)
songs_button['bd'] = 0
songs_button.grid(row=1, column=0)

# Search/Print song button
print_song_button = Button(
    button_frame,
    image=print_song_image,
    background=background_colors["main"],
    activebackground=background_colors["main"],  # No highlight on press
    activeforeground=background_colors["main"],  # No text color change on press
    command=custom_search_dialog
)
print_song_button['bd'] = 0
print_song_button.grid(row=1, column=1, padx=(0, 60))

# Play button
play_button = Button(
    button_frame,
    image=play_image,
    background=background_colors["main"],
    activebackground=background_colors["main"],  # No highlight on press
    activeforeground=background_colors["main"],  # No text color change on press
    command=Play
)
play_button['bd'] = 0
play_button.grid(row=1, column=3, padx=10)

# Pause button
pause_button = Button(
    button_frame,
    image=pause_image,
    background=background_colors["main"],
    activebackground=background_colors["main"],  # No highlight on press
    activeforeground=background_colors["main"],  # No text color change on press
    command=toggle_pause_resume
)
pause_button['bd'] = 0
pause_button.grid(row=1, column=3, padx=10)
pause_button.grid_remove()  # Hidden initially

# Resume button
resume_button = Button(
    button_frame,
    image=play_image,
    background=background_colors["main"],
    activebackground=background_colors["main"],  # No highlight on press
    activeforeground=background_colors["main"],  # No text color change on press
    command=toggle_pause_resume
)
resume_button['bd'] = 0
resume_button.grid(row=1, column=3, padx=10)
resume_button.grid_remove()  # Hidden initially

# Define a custom style for the progress bar
progress_barstyle = ttk.Style()
progress_barstyle.theme_use('default')  # Ensure we are using the default theme
progress_barstyle.configure("TProgressbar",
                troughcolor=background_colors['select_bg'],  # Background color (the empty part)
                background=background_colors['list'],  # Fill color (the progress part)
                thickness=20)        # Optional: Change the thickness of the bar

# Progress Bar Setup
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100, length=520, style="TProgressbar")
progress_bar.grid(row=2, column=1, columnspan=3, pady=10, sticky='ew')

# Bind left-click drag to the progress bar for continuous updates while dragging
progress_bar.bind("<B1-Motion>", on_progress_drag)

# Bind left-click release to update the song position and start playing from that point
progress_bar.bind("<ButtonRelease-1>", on_progress_release)

# Volume slider initialization on the same row but on the right side
volume_slider = VolumeSlider(button_frame, row=1)
volume_slider.frame.grid(row=1, column=9)

random_mode = load_play_mode()  # Load the initial play mode setting
if random_mode:
    random_button.config(image=normal_play_image)
first_load = False

# Configure grid weights to center the buttons
for i in range(7):  # Adjust for 7 columns
    root.grid_columnconfigure(i, weight=1)
root.grid_rowconfigure(1, minsize=45)

# Run the main event loop
try:
    # Bind all of the shortcuts
    root.bind('<m>', print_current_song)
    root.bind('<a>', lambda event: Previous())
    root.bind('<d>', lambda event: Next())
    root.bind('<r>', lambda event: toggle_random())
    root.bind('<e>', lambda event: change_music_folder())
    root.bind('<n>', lambda event: get_volume())
    root.bind('<b>', lambda event: get_progress_percentage())
    root.bind('<j>', lambda event: print_current_artist())
    root.bind('<l>', lambda event: get_random_state())
    root.bind('<k>', lambda event: get_folder())
    root.bind('<t>', lambda event: play_from_begining())
    root.bind('<p>', lambda event: print_all_artists())
    if first_song_click and not mixer.music.get_busy() and not is_playing:
        root.bind('<v>', lambda event: Play())
        first_song_click = False
    else:
        root.bind('<v>', lambda event: toggle_pause_resume())
    root.bind('<Control-Left>', lambda event: Previous())
    root.bind('<Control-Right>', lambda event: Next())
    root.bind('<Up>', lambda event: volume_slider.increase_volume())
    root.bind('<Down>', lambda event: volume_slider.decrease_volume())
    root.bind('<Control-x>', lambda event: volume_slider.increase_volume())
    root.bind('<Control-z>', lambda event: volume_slider.decrease_volume())
    root.bind('<Right>', lambda event: seek_forward())
    root.bind('<Left>', lambda event: seek_backward())
    root.bind('<Shift-Right>', lambda event: seek_forward(5))
    root.bind('<Shift-Left>', lambda event: seek_backward(5))
    root.bind('<Control-w>', scroll_up)
    root.bind('<Control-s>', scroll_down)
    root.bind('<Control-Up>', scroll_up)
    root.bind('<Control-Down>', scroll_down)
    root.bind('<f>', lambda event: custom_search_dialog())
    root.bind('<q>', lambda event: show_shortcuts())
    root.bind('<Control-c>', lambda event: save_and_close())

    keyboard.add_hotkey('ctrl+shift+a', bring_app_to_foreground)
    keyboard.add_hotkey('ctrl+shift+q', bring_app_to_background)

    # Run the main loop
    root.mainloop()

except KeyboardInterrupt:
    mixer.music.stop()
    sys.exit()

mixer.music.stop()
sys.exit()
