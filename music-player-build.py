import os
import subprocess
import sys

# Function to get the correct resource path
def resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS  # PyInstaller creates a temporary folder and stores path in _MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Clear out previous builds
if os.path.exists('build'):
    import shutil
    shutil.rmtree('build')

if os.path.exists('dist'):
    shutil.rmtree('dist')

# Define the PyInstaller command and options
command = [
    'pyinstaller',
    '--onefile',
    '--windowed',
    '--add-data', r'C:/openai_assistant/games/resources/buttons/next.png;resources/buttons',
    '--add-data', r'C:/openai_assistant/games/resources/buttons/previous.png;resources/buttons',
    '--add-data', r'C:/openai_assistant/games/resources/buttons/play.png;resources/buttons',
    '--add-data', r'C:/openai_assistant/games/resources/buttons/pause.png;resources/buttons',
    '--add-data', r'C:/openai_assistant/games/resources/buttons/shuffle-inactive.png;resources/buttons',
    '--add-data', r'C:/openai_assistant/games/resources/buttons/shuffle-active.png;resources/buttons',
    '--add-data', r'C:/openai_assistant/games/resources/buttons/search.png;resources/buttons',
    '--add-data', r'C:/openai_assistant/games/resources/buttons/playlist.png;resources/buttons',
    '--add-data', r'C:/openai_assistant/games/resources/buttons/logo.png;resources/buttons',
    '--add-data', r'C:/openai_assistant/games/resources/misc/logo.png;resources/misc',
    '--add-data', r'C:/openai_assistant/games/mode_settings.json;.',
    '--add-data', r'C:/openai_assistant/games/playlist.json;.',
    '--add-data', r'C:/openai_assistant/games/volume_settings.json;.',
    '--add-data', r'C:/openai_assistant/games/music_player_settings.json;.',
    'music-player.py'
]

# Run the command
try:
    subprocess.run(command, check=True)
except subprocess.CalledProcessError as e:
    print(f"An error occurred: {e}")
