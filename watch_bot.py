import os
import sys
import time
import subprocess

def get_max_mtime(directory: str) -> float:
    """Returns the maximum modification time of all .py files in directory."""
    max_mtime = 0.0
    for dirpath, _, filenames in os.walk(directory):
        if "__pycache__" in dirpath or ".git" in dirpath:
            continue
        for filename in filenames:
            if filename.endswith(".py"):
                filepath = os.path.join(dirpath, filename)
                try:
                    mtime = os.path.getmtime(filepath)
                    if mtime > max_mtime:
                        max_mtime = mtime
                except OSError:
                    pass
    return max_mtime

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    watch_dir = os.path.join(root_dir, "src")
    bot_path = os.path.join(watch_dir, "bot.py")
    
    print(f"👀 [WATCHER] Monitoring directory '{watch_dir}' for code changes...")
    
    last_mtime = get_max_mtime(watch_dir)
    process = None
    
    try:
        # Start the bot initially using uv run python
        process = subprocess.Popen([sys.executable, bot_path])
        
        while True:
            time.sleep(1)
            # Check if process exited on its own
            retcode = process.poll()
            if retcode is not None:
                print(f"⚠️ [WATCHER] Bot process exited with code {retcode}. Restarting...")
                process = subprocess.Popen([sys.executable, bot_path])
                last_mtime = get_max_mtime(watch_dir)
                continue
                
            # Check for changes in src/
            current_mtime = get_max_mtime(watch_dir)
            if current_mtime > last_mtime:
                print("⚡ [WATCHER] Code change detected in src/. Hot-restarting bot...")
                # Terminate the current running bot
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    
                # Start new process
                process = subprocess.Popen([sys.executable, bot_path])
                last_mtime = current_mtime
    except KeyboardInterrupt:
        print("Stopping watcher...")
        if process:
            process.terminate()
            try:
                process.wait(timeout=2)
            except Exception:
                pass

if __name__ == "__main__":
    main()
