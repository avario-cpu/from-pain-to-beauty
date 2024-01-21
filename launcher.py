import threading
import subprocess


def run_script(script_name):
    print(f"Running {script_name}...")
    result = subprocess.run(['python', script_name], capture_output=True, text=True)
    print(f"{script_name} Exit Code: {result.returncode}")
    print(f"{script_name} Output: {result.stdout}")


if __name__ == "__main__":
    # List of scripts to run
    scripts = ['loc_test.py', 'test2.py']

    # Create a thread for each script
    threads = [threading.Thread(target=run_script, args=(script,)) for script in scripts]

    # Start each thread
    for thread in threads:
        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

    print("All scripts have completed.")
