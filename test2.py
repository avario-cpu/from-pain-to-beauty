import time
import threading

# Shared variable
shared_variable = 0

# Event to signal when to break the loop
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


if __name__ == "__main__":
    # Start the loop in a separate thread
    loop_thread = threading.Thread(target=main)
    loop_thread.start()

    # Simulate changing the variable from outside the loop
    for _ in range(5):
        change_variable()
        time.sleep(1)

    # Stop the loop from outside
    stop_loop()

    # Wait for the loop thread to finish
    loop_thread.join()

    print("Loop ended.")
