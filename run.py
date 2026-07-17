import sys
import os
import subprocess
import time
import webbrowser

def install_dependencies():
    print("[Launcher] Verifying python environment dependencies...")
    try:
        import fastapi
        import uvicorn
        import transformers
        import torch
        import PIL
        import numpy
        import matplotlib
        print("[Launcher] All dependencies are already met.")
    except ImportError as e:
        missing = e.name if hasattr(e, 'name') else str(e)
        print(f"[Launcher] Missing package: {missing}. Installing dependencies from requirements.txt...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("[Launcher] Dependencies installed successfully.")
        except subprocess.CalledProcessError as err:
            print(f"[Launcher] Error installing dependencies: {err}")
            sys.exit(1)

def launch_server():
    print("[Launcher] Starting FastAPI server...")
    
    # Wait a moment, then open the browser
    # We do it asynchronously or with a slight delay
    port = 8000
    url = f"http://127.0.0.1:{port}/"
    
    # Import uvicorn directly to run in-process
    import uvicorn
    
    # We can open the web browser right before starting or run it in a separate thread.
    # Since uvicorn.run is blocking, we can use a quick trick: open the browser first,
    # or start a timer thread to open it in 2 seconds. Let's use a timer thread!
    import threading
    def open_browser():
        time.sleep(2)
        print(f"[Launcher] Opening web browser at {url}")
        webbrowser.open(url)
        
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Start the server
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="info", reload=True)

if __name__ == "__main__":
    # Ensure current directory is the project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    sys.path.append(project_dir)
    
    install_dependencies()
    launch_server()
