import subprocess
import sys

if __name__ == "__main__":
    script_path = r"C:\openai_assistant\games\music-player.py"
    subprocess.Popen([sys.executable, script_path], creationflags=subprocess.CREATE_NO_WINDOW)
