import time
import threading
import keyboard

stop_event = threading.Event()


def change_variable():
    global shared_variable
    shared_variable += 1


def main():
    print("Loop started.")

    while not stop_event.is_set():
        # Your loop logic goes here
        print(f"Current value of shared_variable: {shared_variable}")

        # Sleep for a short duration to avoid a busy loop
        time.sleep(1)


def stop_loop():
    print("Stopping the loop.")
    stop_event.set()
    loop_thread.join()


def start_thread():
    loop_thread.start()


loop_thread = threading.Thread(target=main)

keyboard.add_hotkey('Ctrl+Alt+H', stop_loop)
keyboard.add_hotkey('Ctrl+Alt+J', start_thread)

# try:
#     while True:
#         # Your main program logic goes here
#         time.sleep(1)
# except KeyboardInterrupt:
#     # Handle KeyboardInterrupt (Ctrl+C)
#     print("Program interrupted by user.")
# finally:
#     # Unregister the hotkey before exiting
#     keyboard.remove_hotkey('Ctrl+Alt+H')
