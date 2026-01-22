import subprocess
import time
import threading
import os
import sys

# --- Configuration ---
TIMEOUT_SECONDS = 1200  # 20 minutes
COMMAND = ["label-studio", "start", "--port", "9000"]
# ---------------------

last_activity = time.time()
running = True

def shutdown_system():
    """
    Executes the command to shut down the machine.
    Detects OS to use the correct command (Windows vs Linux/Mac).
    """
    print("--- Initiating System Shutdown ---")
    os.system("sudo shutdown -h now")

def output_reader(proc):
    """
    Reads output from the process line by line.
    Updates the global timestamp whenever output is detected.
    """
    global last_activity, running
    
    # Iterate over stdout. This blocks until a new line appears.
    for line in iter(proc.stdout.readline, b''):
        if line:
            # Print output to console so you can still see it
            sys.stdout.buffer.write(line)
            sys.stdout.flush()
            
            # Update the timestamp
            last_activity = time.time()
    
    # If the loop ends, the process has closed
    running = False

def monitor():
    try:
        # Copy environment and force unbuffered output for Python
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        # Start the process
        proc = subprocess.Popen(
            COMMAND, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            env=env
        )
        
        print(f"--- Started Label Studio (PID: {proc.pid}) ---")
        print(f"--- Monitoring for {TIMEOUT_SECONDS}s of silence ---")

        # Start the reader thread
        t = threading.Thread(target=output_reader, args=(proc,))
        t.daemon = True # Thread dies when main program dies
        t.start()

        should_shutdown = False

        while running:
            # Calculate idle time
            idle_time = time.time() - last_activity
            
            if idle_time > TIMEOUT_SECONDS:
                print(f"\n[Timeout] No output for {idle_time:.0f} seconds. Killing process...")
                proc.terminate() # Try graceful stop
                
                # Give it 5 seconds to close, then force kill
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                
                should_shutdown = True
                break
            
            # Check if process died on its own
            if proc.poll() is not None:
                print("\n[Status] Label Studio stopped unexpectedly.")
                should_shutdown = True
                break
                
            time.sleep(5) # Check status every 5 seconds

        # Trigger Shutdown if the loop exited because the process finished
        if should_shutdown:
            shutdown_system()

    except KeyboardInterrupt:
        print("\n[User] Stopping monitor (Shutdown aborted)...")
        # Clean up child process if user hits Ctrl+C
        if 'proc' in locals() and proc.poll() is None:
            proc.terminate()

if __name__ == "__main__":
    monitor()