"""
Residual Ore Recovery DSS - Launcher (PyInstaller Safe)
Prevents infinite subprocess spawning when packaged as .exe
"""

import subprocess
import sys
import os
import webbrowser
import time
import threading
import socket


def is_port_in_use(port=8501):
    """Check if the port is already in use (another instance running)"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def open_browser():
    """Open browser after delay"""
    time.sleep(4)
    webbrowser.open('http://localhost:8501')


def main():
    # === CRITICAL: Prevent infinite loop ===
    # When PyInstaller exe runs, multiprocessing/subprocess can re-execute the exe
    # This environment variable prevents recursive spawning
    if os.environ.get('STREAMLIT_DSS_RUNNING') == '1':
        return
    os.environ['STREAMLIT_DSS_RUNNING'] = '1'

    # Check if already running
    if is_port_in_use(8501):
        print("System already running on port 8501")
        print("Opening browser...")
        webbrowser.open('http://localhost:8501')
        input("Press Enter to exit...")
        return

    # Get base directory
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    app_path = os.path.join(base_dir, "app.py")

    if not os.path.exists(app_path):
        print(f"ERROR: Cannot find {app_path}")
        print("Make sure app.py is in the same folder as this exe")
        input("Press Enter to exit...")
        return

    print("=" * 50)
    print("  Residual Ore Recovery DSS v3.1")
    print("=" * 50)
    print()
    print("Starting system...")
    print("URL: http://localhost:8501")
    print()
    print("Close this window to stop the system")
    print("=" * 50)

    # Open browser after delay
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # Find streamlit executable
    if getattr(sys, 'frozen', False):
        # When frozen, use the Python from the system PATH
        # PyInstaller exe cannot directly run streamlit module
        streamlit_cmd = ['streamlit', 'run', app_path,
                         '--server.headless=true',
                         '--browser.gatherUsageStats=false',
                         '--server.port=8501',
                         '--server.address=localhost']
    else:
        streamlit_cmd = [sys.executable, '-m', 'streamlit', 'run', app_path,
                         '--server.headless=true',
                         '--browser.gatherUsageStats=false',
                         '--server.port=8501',
                         '--server.address=localhost']

    try:
        # Use CREATE_NO_WINDOW flag to prevent additional console windows on Windows
        if sys.platform == 'win32':
            proc = subprocess.Popen(streamlit_cmd,
                                     env={**os.environ, 'STREAMLIT_DSS_RUNNING': '1'})
        else:
            proc = subprocess.Popen(streamlit_cmd,
                                     env={**os.environ, 'STREAMLIT_DSS_RUNNING': '1'})
        proc.wait()
    except FileNotFoundError:
        print()
        print("ERROR: 'streamlit' command not found!")
        print("Please run setup.bat first to install dependencies")
        print("Or run: pip install streamlit")
        input("Press Enter to exit...")
    except KeyboardInterrupt:
        print("\nSystem stopped.")


if __name__ == "__main__":
    # Extra protection: multiprocessing freeze support
    try:
        import multiprocessing
        multiprocessing.freeze_support()
    except Exception:
        pass

    main()
